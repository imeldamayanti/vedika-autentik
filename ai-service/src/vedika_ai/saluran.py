"""Phone helper: drives the station's Android phone over adb for the agent page.

Mounted only on the station laptop (SALURAN_ADB=1, or "palsu" for an in-memory fake phone) and
answers only localhost, because /konfigurasi hands the station browser its keys. Phone numbers
are never logged.
"""

import re
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Depends, Request
from loguru import logger
from pydantic import BaseModel

from . import config
from .errors import ServiceError

CallState = Literal["idle", "offhook", "ringing"]
Runner = Callable[[list[str]], str]

ADB_TIMEOUT_SECONDS = 8
LOCAL_HOSTS = {"127.0.0.1", "::1"}
NUMBER_PATTERN = re.compile(r"^\+?\d{8,15}$")
CALL_STATE_PATTERN = re.compile(r"mCallState=(\d)")
# PreciseCallState per SIM: 1 ACTIVE (answered), 3 DIALING, 4 ALERTING. mCallState is 2 while
# ringing, so only this tells a picked-up call from one still ringing.
FOREGROUND_STATE_PATTERN = re.compile(r"mForegroundCallState=(-?\d)")
KEYGUARD_PATTERN = re.compile(r"isKeyguardShowing=true")
# The system call handler. Naming it skips the app chooser that appears when another app (Zoom,
# for one) also handles CALL intents; without it the call never leaves the phone.
TELECOM_PACKAGE = "com.android.server.telecom"
SIM_READY_STATES = {"READY", "LOADED"}
# Speakerphone: Android has no adb command for it and many phones (Xiaomi, Android 13) start every
# call on the earpiece, so in speaker mode the helper taps the in-call "Speaker" button itself.
SPEAKER_LABELS = ("speaker", "pengeras suara", "speakerphone", "loudspeaker")
SPEAKER_ROUTE_PATTERN = re.compile(r"Current state: (\w+)")
UI_DUMP_PATH = "/sdcard/vedika-ui.xml"
NODE_PATTERN = re.compile(r"<node [^>]*>")
BOUNDS_PATTERN = re.compile(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"')
DESC_PATTERN = re.compile(r'(?:content-desc|text)="([^"]*)"')
SPEAKER_ATTEMPTS = 8
SPEAKER_TAPS = 2
NOT_CONNECTED = "HP tidak terhubung ke laptop"
UNAUTHORIZED = "Izinkan debugging USB di HP"
SEVERAL_DEVICES = "Lebih dari satu HP terhubung; isi SALURAN_ADB_SERIAL"
SIM_NOT_READY = "SIM tidak siap"
IN_CALL = "HP sedang dalam panggilan"
LOCKED = "Layar HP terkunci; buka kunci layar HP"
ADB_FAILED = "adb tidak bisa dijalankan"


class AdbError(Exception):
    pass


class DialRequest(BaseModel):
    nomor: str


# ---- pure parsers ----


def parse_devices(output: str) -> list[tuple[str, str]]:
    """`adb devices` output -> [(serial, state)]."""
    devices = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and not line.startswith("*"):
            devices.append((parts[0], parts[1]))
    return devices


def parse_call_state(output: str) -> CallState:
    """`dumpsys telephony.registry` prints one mCallState per SIM: 0 idle, 1 ringing, 2 offhook."""
    states = set(CALL_STATE_PATTERN.findall(output))
    if "2" in states:
        return "offhook"
    return "ringing" if "1" in states else "idle"


def parse_ringing(output: str) -> bool:
    """True while the recipient's phone is ringing (foreground call state ALERTING)."""
    return "4" in FOREGROUND_STATE_PATTERN.findall(output)


def parse_connected(output: str) -> bool:
    """True once the network reports a call as answered (foreground call state ACTIVE)."""
    return "1" in FOREGROUND_STATE_PATTERN.findall(output)


def sim_ready(state: str) -> bool:
    """gsm.sim.state is one value per slot, e.g. "READY,ABSENT". Some phones (Xiaomi, Android 13)
    report LOADED, the state after READY once the SIM records are read."""
    return any(part.strip() in SIM_READY_STATES for part in state.split(","))


def keyguard_showing(output: str) -> bool:
    """`dumpsys window` says isKeyguardShowing=true while the lock screen is up. A locked phone
    shows the call screen but never dials, so the station must not claim a task then."""
    return KEYGUARD_PATTERN.search(output) is not None


def speaker_route(telecom_dump: str) -> bool:
    """`dumpsys telecom` names the call audio route: ActiveEarpieceRoute, ActiveSpeakerRoute, ..."""
    match = SPEAKER_ROUTE_PATTERN.search(telecom_dump)
    return bool(match) and "Speaker" in match.group(1)


def speaker_button(ui_xml: str) -> tuple[int, int] | None:
    """Centre of the in-call Speaker button in a `uiautomator dump`, or None if not on screen."""
    for node in NODE_PATTERN.findall(ui_xml):
        labels = [label.strip().lower() for label in DESC_PATTERN.findall(node)]
        if not any(label in SPEAKER_LABELS for label in labels):
            continue
        bounds = BOUNDS_PATTERN.search(node)
        if bounds:
            x1, y1, x2, y2 = (int(value) for value in bounds.groups())
            return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def normalize_number(raw: str) -> str | None:
    number = re.sub(r"[\s-]", "", raw)
    return number if NUMBER_PATTERN.fullmatch(number) else None


# ---- adb ----


def adb_runner(binary: str) -> Runner:
    def run(args: list[str]) -> str:
        try:
            result = subprocess.run(
                [binary, *args],
                capture_output=True,
                text=True,
                timeout=ADB_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise AdbError(type(error).__name__) from error
        if result.returncode != 0:
            raise AdbError(f"exit {result.returncode}")
        return result.stdout

    return run


def _not_ready(reason: str, device: str | None = None, sim: str | None = None) -> dict:
    return {"siap": False, "alasan": reason, "perangkat": device, "sim": sim, "panggilan": "idle"}


class AdbPhone:
    def __init__(self, run: Runner, serial: str | None = None):
        self.run = run
        self.serial = serial

    def shell(self, *args: str) -> str:
        return self.run([*(["-s", self.serial] if self.serial else []), "shell", *args])

    def health(self) -> dict:
        try:
            devices = parse_devices(self.run(["devices"]))
            if self.serial:
                devices = [device for device in devices if device[0] == self.serial]
            ready = [device for device in devices if device[1] == "device"]
            if len(ready) > 1:
                return _not_ready(SEVERAL_DEVICES)
            if not ready:
                unauthorized = any(state == "unauthorized" for _, state in devices)
                return _not_ready(UNAUTHORIZED if unauthorized else NOT_CONNECTED)
            if len(devices) > 1 and not self.serial:
                return _not_ready(SEVERAL_DEVICES)
            model = self.shell("getprop", "ro.product.model").strip() or None
            sim = self.shell("getprop", "gsm.sim.state").strip() or None
            if not sim_ready(sim or ""):
                return _not_ready(SIM_NOT_READY, model, sim)
            call = self.call_state()
            locked = call == "idle" and keyguard_showing(self.shell("dumpsys", "window"))
        except AdbError:
            return _not_ready(ADB_FAILED)
        if locked:
            return {**_not_ready(LOCKED, model, sim), "panggilan": call}
        return {
            "siap": call == "idle",
            "alasan": None if call == "idle" else IN_CALL,
            "perangkat": model,
            "sim": sim,
            "panggilan": call,
        }

    def call_state(self) -> CallState:
        return parse_call_state(self.shell("dumpsys", "telephony.registry"))

    def line_status(self) -> dict:
        registry = self.shell("dumpsys", "telephony.registry")
        call = parse_call_state(registry)
        connected = call == "offhook" and parse_connected(registry)
        ringing = call == "offhook" and not connected and parse_ringing(registry)
        return {"panggilan": call, "tersambung": connected, "berdering": ringing}

    def dial(self, number: str) -> None:
        output = self.shell(
            "am",
            "start",
            "-a",
            "android.intent.action.CALL",
            "-d",
            f"tel:{number}",
            "-p",
            TELECOM_PACKAGE,
        )
        if "Error" in output or "Exception" in output:
            raise AdbError("am start rejected the call intent")

    def speaker_on(self, sleep: Callable[[float], None]) -> bool:
        """Switch the call to speakerphone. Checks the real audio route before and after every tap,
        and taps at most SPEAKER_TAPS times so a slow route update never toggles it back off."""
        taps = 0
        for _ in range(SPEAKER_ATTEMPTS):
            sleep(1.0)
            if self.call_state() == "idle":
                return False
            if speaker_route(self.shell("dumpsys", "telecom")):
                return True
            if taps >= SPEAKER_TAPS:
                continue
            self.shell("uiautomator", "dump", UI_DUMP_PATH)
            centre = speaker_button(self.shell("cat", UI_DUMP_PATH))
            if centre is None:
                continue
            self.shell("input", "tap", str(centre[0]), str(centre[1]))
            taps += 1
            sleep(0.5)
        return False

    def hang_up(self) -> None:
        # On some phones KEYCODE_ENDCALL with no call acts as the power key and locks the screen,
        # and a locked phone cannot dial the next patient. Send it only while a call is up.
        if self.call_state() != "idle":
            self.shell("input", "keyevent", "KEYCODE_ENDCALL")


class FakePhone:
    """In-memory phone for tests and the automated e2e call (SALURAN_ADB=palsu)."""

    def __init__(self):
        self.state: CallState = "idle"

    def health(self) -> dict:
        idle = self.state == "idle"
        return {
            "siap": idle,
            "alasan": None if idle else IN_CALL,
            "perangkat": "HP palsu",
            "sim": "READY",
            "panggilan": self.state,
        }

    def call_state(self) -> CallState:
        return self.state

    def line_status(self) -> dict:
        # The fake phone cannot tell ringing from answered (None = unknown); the robot recipient
        # speaks first, so the agent listens from the start.
        return {"panggilan": self.state, "tersambung": None, "berdering": None}

    def dial(self, number: str) -> None:
        del number
        self.state = "offhook"

    def hang_up(self) -> None:
        self.state = "idle"


# ---- HTTP ----


def require_localhost(request: Request) -> None:
    if request.client is None or request.client.host not in LOCAL_HOSTS:
        raise ServiceError(403, "bukan_lokal", "Saluran telepon hanya melayani laptop stasiun.")


def create_router(
    mode: str, run: Runner | None = None, sleep: Callable[[float], None] = time.sleep
) -> APIRouter:
    """mode "palsu" uses the fake phone; anything else drives adb through `run`."""
    fake = mode == "palsu"
    phone = (
        FakePhone() if fake else AdbPhone(run or adb_runner(config.adb_bin()), config.adb_serial())
    )
    router = APIRouter(prefix="/v1/saluran", dependencies=[Depends(require_localhost)])

    def adb(action: Callable[[], object]):
        try:
            return action()
        except AdbError as error:
            logger.warning("saluran adb_gagal reason={reason}", reason=str(error))
            raise ServiceError(502, "adb_gagal", "Perintah ke HP saluran gagal.") from error

    @router.get("/kesehatan")
    def health() -> dict:
        return phone.health()

    @router.get("/status")
    def status() -> dict:
        return adb(phone.line_status)

    @router.post("/panggil")
    def dial(body: DialRequest) -> dict:
        number = normalize_number(body.nomor)
        if number is None:
            raise ServiceError(422, "nomor_tidak_valid", "Nomor tujuan tidak valid.")
        logger.info("saluran panggil diminta")
        adb(lambda: phone.dial(number))
        if not fake and config.line_audio() == "speaker":
            threading.Thread(target=turn_speaker_on, daemon=True).start()
        return {"ok": True}

    def turn_speaker_on() -> None:
        try:
            on = phone.speaker_on(sleep)
        except AdbError as error:
            logger.warning("saluran speaker_gagal reason={reason}", reason=str(error))
            return
        logger.info("saluran speaker aktif={on}", on=on)

    @router.post("/tutup")
    def hang_up() -> dict:
        adb(phone.hang_up)
        return {"ok": True}

    @router.get("/konfigurasi")
    def configuration() -> dict:
        return {
            "api_url": config.line_api_url(),
            "kunci_agen": config.line_agent_key(),
            "kunci_layanan": config.service_key(),
            "audio": config.line_audio(),
            "input": config.line_input(),
            "output": config.line_output(),
        }

    if fake:

        @router.post("/palsu/tutup-penerima")
        def recipient_hangs_up() -> dict:
            phone.hang_up()
            return {"ok": True}

    return router
