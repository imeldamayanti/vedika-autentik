import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vedika_ai import saluran
from vedika_ai.errors import ServiceError
from vedika_ai.main import app as main_app
from vedika_ai.main import handle_service_error, mount_line_helper

LOCAL = ("127.0.0.1", 50000)
ONE_DEVICE = "List of devices attached\nR58N123ABC\tdevice\n\n"
REGISTRY_IDLE = "  mCallState=0\n  mRingingCallState=0\n  mCallState=0\n"


class FakeAdb:
    """Scripted adb: maps the command after `shell` to its output and records every call."""

    def __init__(self, devices=ONE_DEVICE, sim="READY,ABSENT", registry=REGISTRY_IDLE, fail=()):
        self.devices, self.sim, self.registry, self.fail = devices, sim, registry, set(fail)
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        command = args[args.index("shell") + 1 :] if "shell" in args else args
        if command[0] in self.fail:
            raise saluran.AdbError("exit 1")
        if command == ["devices"]:
            return self.devices
        if command == ["getprop", "ro.product.model"]:
            return "Pixel 7\n"
        if command == ["getprop", "gsm.sim.state"]:
            return f"{self.sim}\n"
        if command == ["dumpsys", "telephony.registry"]:
            return self.registry
        if command[0] == "am":
            return "Starting: Intent { act=android.intent.action.CALL dat=tel:xxxxxxxxxxxx }\n"
        return ""


def client_for(mode="1", run=None, client=LOCAL, **env):
    app = FastAPI()
    app.add_exception_handler(ServiceError, handle_service_error)
    app.include_router(saluran.create_router(mode, run))
    return TestClient(app, client=client)


# ---- pure parsers ----


@pytest.mark.parametrize(
    ("output", "devices"),
    [
        ("List of devices attached\n\n", []),
        (ONE_DEVICE, [("R58N123ABC", "device")]),
        (
            "* daemon not running; starting now at tcp:5037\n* daemon started successfully\n"
            "List of devices attached\nR58N123ABC\tunauthorized\nemulator-5554\toffline\n",
            [("R58N123ABC", "unauthorized"), ("emulator-5554", "offline")],
        ),
        ("List of devices attached\nA1 device usb:1-1 model:Pixel_7\n", [("A1", "device")]),
    ],
)
def test_parse_devices(output, devices):
    parsed = saluran.parse_devices(output)
    assert [d for d in parsed if d[0] not in ("*", "List")] == devices


@pytest.mark.parametrize(
    ("output", "state"),
    [
        ("", "idle"),
        ("mCallState=0\nmCallState=0", "idle"),
        ("mCallState=0\nmCallState=1", "ringing"),
        ("mCallState=2\nmCallState=0", "offhook"),
        ("mCallState=1\nmCallState=2", "offhook"),
        ("  mCallState=2\n  mRingingCallState=0\n  mForegroundCallState=3", "offhook"),
    ],
)
def test_parse_call_state_reads_every_sim(output, state):
    assert saluran.parse_call_state(output) == state


@pytest.mark.parametrize(
    ("state", "ready"),
    [
        ("READY", True),
        ("READY,ABSENT", True),
        ("ABSENT,READY", True),
        ("LOADED,READY", True),
        ("ABSENT", False),
        ("NOT_READY", False),
        ("PIN_REQUIRED,ABSENT", False),
        ("", False),
    ],
)
def test_sim_ready(state, ready):
    assert saluran.sim_ready(state) is ready


@pytest.mark.parametrize(
    ("raw", "number"),
    [
        ("0812-3456-7890", "081234567890"),
        ("+62 812 3456 7890", "+6281234567890"),
        ("08123456", "08123456"),
        ("0812345", None),
        ("0812-3456-7890-1234-5", None),
        ("0812;rm -rf", None),
        ("tel:081234567890", None),
        ("0812 3456 7890 && reboot", None),
        ("", None),
    ],
)
def test_normalize_number(raw, number):
    assert saluran.normalize_number(raw) == number


def test_adb_runner_reports_missing_binary_and_non_zero_exit():
    with pytest.raises(saluran.AdbError):
        saluran.adb_runner("/nonexistent/adb")(["devices"])
    with pytest.raises(saluran.AdbError, match="exit 1"):
        saluran.adb_runner("false")(["devices"])
    assert saluran.adb_runner("echo")(["shell", "ok"]) == "shell ok\n"


# ---- health ----


def test_health_ready_with_one_authorised_phone():
    adb = FakeAdb()
    response = client_for(run=adb).get("/v1/saluran/kesehatan")

    assert response.status_code == 200
    assert response.json() == {
        "siap": True,
        "alasan": None,
        "perangkat": "Pixel 7",
        "sim": "READY,ABSENT",
        "panggilan": "idle",
    }
    assert adb.calls[0] == ["devices"]


@pytest.mark.parametrize(
    ("adb", "reason", "call"),
    [
        (FakeAdb(devices="List of devices attached\n\n"), "HP tidak terhubung ke laptop", "idle"),
        (
            FakeAdb(devices="List of devices attached\nA1\tunauthorized\n"),
            "Izinkan debugging USB di HP",
            "idle",
        ),
        (
            FakeAdb(devices="List of devices attached\nA1\toffline\n"),
            "HP tidak terhubung ke laptop",
            "idle",
        ),
        (
            FakeAdb(devices="List of devices attached\nA1\tdevice\nB2\tdevice\n"),
            "Lebih dari satu HP terhubung; isi SALURAN_ADB_SERIAL",
            "idle",
        ),
        (
            FakeAdb(devices="List of devices attached\nA1\tdevice\nB2\tunauthorized\n"),
            "Lebih dari satu HP terhubung; isi SALURAN_ADB_SERIAL",
            "idle",
        ),
        (FakeAdb(sim="ABSENT"), "SIM tidak siap", "idle"),
        (FakeAdb(sim="NOT_READY,ABSENT"), "SIM tidak siap", "idle"),
        (FakeAdb(registry="mCallState=2\nmCallState=0\n"), "HP sedang dalam panggilan", "offhook"),
        (FakeAdb(registry="mCallState=1\n"), "HP sedang dalam panggilan", "ringing"),
        (FakeAdb(fail={"devices"}), "adb tidak bisa dijalankan", "idle"),
        (FakeAdb(fail={"dumpsys"}), "adb tidak bisa dijalankan", "idle"),
    ],
)
def test_health_not_ready_names_the_first_failed_check(adb, reason, call):
    body = client_for(run=adb).get("/v1/saluran/kesehatan").json()

    assert (body["siap"], body["alasan"], body["panggilan"]) == (False, reason, call)


def test_serial_selects_one_of_several_phones(monkeypatch):
    monkeypatch.setenv("SALURAN_ADB_SERIAL", "B2")
    adb = FakeAdb(devices="List of devices attached\nA1\tdevice\nB2\tdevice\n")
    client = client_for(run=adb)

    assert client.get("/v1/saluran/kesehatan").json()["siap"] is True
    assert adb.calls[1] == ["-s", "B2", "shell", "getprop", "ro.product.model"]
    monkeypatch.setenv("SALURAN_ADB_SERIAL", "Z9")
    assert (
        client_for(run=adb).get("/v1/saluran/kesehatan").json()["alasan"]
        == "HP tidak terhubung ke laptop"
    )


# ---- dial, hang up, status ----


def test_dial_normalises_the_number_and_starts_the_call_intent():
    adb = FakeAdb()
    response = client_for(run=adb).post("/v1/saluran/panggil", json={"nomor": "0812-3456 7890"})

    assert response.status_code == 200 and response.json() == {"ok": True}
    assert adb.calls == [
        ["shell", "am", "start", "-a", "android.intent.action.CALL", "-d", "tel:081234567890"]
    ]


@pytest.mark.parametrize("number", ["12345", "0812;reboot", "abc", "0812 3456 7890 $(id)", ""])
def test_dial_rejects_an_invalid_number_without_touching_adb(number):
    adb = FakeAdb()
    response = client_for(run=adb).post("/v1/saluran/panggil", json={"nomor": number})

    assert response.status_code == 422
    assert response.json()["galat"]["kode"] == "nomor_tidak_valid"
    assert adb.calls == []


def test_dial_reports_adb_failure_and_intent_errors():
    response = client_for(run=FakeAdb(fail={"am"})).post(
        "/v1/saluran/panggil", json={"nomor": "081234567890"}
    )
    assert response.status_code == 502 and response.json()["galat"]["kode"] == "adb_gagal"

    def rejects_intent(args):
        del args
        return "Error: Activity not started, unable to resolve Intent\n"

    response = client_for(run=rejects_intent).post(
        "/v1/saluran/panggil", json={"nomor": "081234567890"}
    )
    assert response.status_code == 502 and response.json()["galat"]["kode"] == "adb_gagal"


def test_hang_up_is_idempotent_and_status_reads_the_registry():
    adb = FakeAdb(registry="mCallState=0\nmCallState=2\n")
    client = client_for(run=adb)

    assert client.post("/v1/saluran/tutup").json() == {"ok": True}
    assert client.post("/v1/saluran/tutup").json() == {"ok": True}
    assert adb.calls == [["shell", "input", "keyevent", "KEYCODE_ENDCALL"]] * 2
    assert client.get("/v1/saluran/status").json() == {"panggilan": "offhook"}
    assert client_for(run=FakeAdb(fail={"dumpsys"})).get("/v1/saluran/status").status_code == 502


def test_dial_never_logs_the_number():
    from loguru import logger

    lines = []
    sink = logger.add(lines.append, level="DEBUG")
    try:
        client = client_for(run=FakeAdb())
        client.post("/v1/saluran/panggil", json={"nomor": "081234567890"})
        client_for(run=FakeAdb(fail={"am"})).post(
            "/v1/saluran/panggil", json={"nomor": "081234567890"}
        )
    finally:
        logger.remove(sink)

    assert any("panggil diminta" in line for line in lines)
    assert not any("81234567890" in line for line in lines)


# ---- configuration and access ----


def test_configuration_hands_the_station_browser_its_settings(monkeypatch):
    for name in ("API_URL", "AUDIO", "INPUT", "OUTPUT"):
        monkeypatch.delenv(f"SALURAN_{name}", raising=False)
    for name in ("AI_SERVICE_KEY",):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SALURAN_AGEN_KEY", "agen-rahasia")
    client = client_for(run=FakeAdb())

    assert client.get("/v1/saluran/konfigurasi").json() == {
        "api_url": "http://localhost:8000",
        "kunci_agen": "agen-rahasia",
        "kunci_layanan": None,
        "audio": "speaker",
        "input": None,
        "output": None,
    }
    monkeypatch.setenv("SALURAN_API_URL", "https://api.example")
    monkeypatch.setenv("SALURAN_AUDIO", "kabel")
    monkeypatch.setenv("SALURAN_INPUT", "USB Audio")
    monkeypatch.setenv("SALURAN_OUTPUT", "USB Audio")
    monkeypatch.setenv("AI_SERVICE_KEY", "layanan-rahasia")
    assert client.get("/v1/saluran/konfigurasi").json() == {
        "api_url": "https://api.example",
        "kunci_agen": "agen-rahasia",
        "kunci_layanan": "layanan-rahasia",
        "audio": "kabel",
        "input": "USB Audio",
        "output": "USB Audio",
    }


@pytest.mark.parametrize("host", ["192.168.1.20", "10.0.0.5", "testclient", "::ffff:192.168.1.20"])
def test_every_route_rejects_non_local_clients(host):
    client = client_for(run=FakeAdb(), client=(host, 50000))
    requests = [
        ("get", "/v1/saluran/kesehatan", {}),
        ("get", "/v1/saluran/status", {}),
        ("get", "/v1/saluran/konfigurasi", {}),
        ("post", "/v1/saluran/panggil", {"json": {"nomor": "081234567890"}}),
        ("post", "/v1/saluran/tutup", {}),
    ]
    for method, path, kwargs in requests:
        response = client.request(method, path, **kwargs)
        assert response.status_code == 403, path
        assert response.json()["galat"]["kode"] == "bukan_lokal"


def test_ipv6_loopback_is_local():
    client = client_for(run=FakeAdb(), client=("::1", 50000))

    assert client.get("/v1/saluran/kesehatan").status_code == 200


def test_helper_needs_no_service_key(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_KEY", "layanan-rahasia")

    assert client_for(run=FakeAdb()).get("/v1/saluran/kesehatan").status_code == 200


# ---- mounting ----


def test_routes_do_not_exist_without_saluran_adb(monkeypatch):
    client = TestClient(main_app, client=LOCAL)
    assert client.get("/v1/saluran/kesehatan").status_code == 404
    assert client.get("/v1/saluran/konfigurasi").status_code == 404

    for value in ("", "0", "ya"):
        monkeypatch.setenv("SALURAN_ADB", value)
        assert mount_line_helper(FastAPI()) is False


@pytest.mark.parametrize("value", ["1", "palsu"])
def test_routes_are_mounted_when_saluran_adb_is_set(monkeypatch, value):
    monkeypatch.setenv("SALURAN_ADB", value)
    app = FastAPI()

    assert mount_line_helper(app) is True
    paths = set(app.openapi()["paths"])
    assert {"/v1/saluran/kesehatan", "/v1/saluran/panggil", "/v1/saluran/tutup"} <= paths
    assert ("/v1/saluran/palsu/tutup-penerima" in paths) is (value == "palsu")


# ---- fake phone ----


def test_fake_phone_follows_dial_hang_up_and_remote_hang_up():
    client = client_for(mode="palsu")

    assert client.get("/v1/saluran/kesehatan").json() == {
        "siap": True,
        "alasan": None,
        "perangkat": "HP palsu",
        "sim": "READY",
        "panggilan": "idle",
    }
    assert client.post("/v1/saluran/panggil", json={"nomor": "081234567890"}).json() == {"ok": True}
    assert client.get("/v1/saluran/status").json() == {"panggilan": "offhook"}
    assert client.get("/v1/saluran/kesehatan").json()["alasan"] == "HP sedang dalam panggilan"
    assert client.post("/v1/saluran/palsu/tutup-penerima").json() == {"ok": True}
    assert client.get("/v1/saluran/status").json() == {"panggilan": "idle"}
    client.post("/v1/saluran/panggil", json={"nomor": "081234567890"})
    assert client.post("/v1/saluran/tutup").json() == {"ok": True}
    assert client.post("/v1/saluran/tutup").json() == {"ok": True}
    assert client.get("/v1/saluran/status").json() == {"panggilan": "idle"}
    assert client.post("/v1/saluran/panggil", json={"nomor": "123"}).status_code == 422


def test_real_mode_has_no_fake_route():
    assert client_for(run=FakeAdb()).post("/v1/saluran/palsu/tutup-penerima").status_code == 404
