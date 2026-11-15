"""Phone helper: drives the station's Android phone over adb for the agent page.

Mounted only on the station laptop (SALURAN_ADB=1, or "palsu" for an in-memory fake phone) and
answers only localhost, because /konfigurasi hands the station browser its keys. Phone numbers
are never logged.
"""

import re
import subprocess
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
NOT_CONNECTED = "HP tidak terhubung ke laptop"
UNAUTHORIZED = "Izinkan debugging USB di HP"
SEVERAL_DEVICES = "Lebih dari satu HP terhubung; isi SALURAN_ADB_SERIAL"
SIM_NOT_READY = "SIM tidak siap"
IN_CALL = "HP sedang dalam panggilan"
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


def sim_ready(state: str) -> bool:
    """gsm.sim.state is one value per slot, e.g. "READY,ABSENT"."""
    return "READY" in [part.strip() for part in state.split(",")]


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
        except AdbError:
            return _not_ready(ADB_FAILED)
        return {
            "siap": call == "idle",
            "alasan": None if call == "idle" else IN_CALL,
            "perangkat": model,
            "sim": sim,
            "panggilan": call,
        }

    def call_state(self) -> CallState:
        return parse_call_state(self.shell("dumpsys", "telephony.registry"))

    def dial(self, number: str) -> None:
        output = self.shell(
            "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{number}"
        )
        if "Error" in output or "Exception" in output:
            raise AdbError("am start rejected the call intent")

    def hang_up(self) -> None:
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

    def dial(self, number: str) -> None:
        del number
        self.state = "offhook"

    def hang_up(self) -> None:
        self.state = "idle"


# ---- HTTP ----


def require_localhost(request: Request) -> None:
    if request.client is None or request.client.host not in LOCAL_HOSTS:
        raise ServiceError(403, "bukan_lokal", "Saluran telepon hanya melayani laptop stasiun.")


def create_router(mode: str, run: Runner | None = None) -> APIRouter:
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
        return {"panggilan": adb(phone.call_state)}

    @router.post("/panggil")
    def dial(body: DialRequest) -> dict:
        number = normalize_number(body.nomor)
        if number is None:
            raise ServiceError(422, "nomor_tidak_valid", "Nomor tujuan tidak valid.")
        logger.info("saluran panggil diminta")
        adb(lambda: phone.dial(number))
        return {"ok": True}

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
