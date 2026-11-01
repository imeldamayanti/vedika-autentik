import pytest
from fastapi.testclient import TestClient

from vedika_ai import config
from vedika_ai.answer_reader import AnswerReader
from vedika_ai.answers import JawabanTerstruktur
from vedika_ai.gemini import GeminiError
from vedika_ai.main import app, get_answer_reader, get_token_issuer
from vedika_ai.voice import VoiceTokenResponse

client = TestClient(app)


class FakeAnswerReader:
    def read(self, request):
        del request
        return JawabanTerstruktur(
            status_panggilan="terjawab",
            penerima="peserta",
            hubungan=None,
            hadir=True,
            jumlah_min=3,
            jumlah_maks=3,
            keyakinan="tinggi",
            tanda_bahaya=[],
            membantah_tanggal_libur=True,
            kutipan_kunci="Tiga kali.",
            ringkasan="Peserta menyatakan hadir tiga kali.",
        )


class FailingGenerator:
    def __init__(self, code):
        self.code = code

    def generate_json(self, prompt, schema):
        del prompt, schema
        raise GeminiError(self.code)


class FakeTokenIssuer:
    def issue(self, context):
        del context
        return VoiceTokenResponse(
            token="auth_tokens/test",
            model="gemini-live-test",
            websocket_url="wss://example.test/BidiGenerateContentConstrained",
            instruksi="Instruksi aman",
            kedaluwarsa="2026-10-28T11:35:00Z",
        )


@pytest.fixture(autouse=True)
def fake_providers():
    app.dependency_overrides[get_answer_reader] = FakeAnswerReader
    app.dependency_overrides[get_token_issuer] = FakeTokenIssuer
    yield
    app.dependency_overrides.clear()


def test_health_reports_reader_readiness(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "server-key")
    response = client.get("/v1/kesehatan")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "versi_mesin": config.ENGINE_VERSION,
        "versi_pembaca": config.READER_VERSION,
        "pembaca_siap": True,
    }
    assert response.headers["X-Request-ID"]


def test_openapi_contains_only_current_contract_endpoints():
    paths = client.get("/openapi.json").json()["paths"]

    assert set(paths) == {"/v1/kesehatan", "/v1/baca", "/v1/suara/token"}


BACA_REQUEST = {
    "id": "CALL-P-S1-2026-08",
    "transkrip": [{"detik": 45, "pembicara": "penerima", "teks": "Tiga kali."}],
    "konteks": {
        "sesi_ditagih": 11,
        "tanggal_libur": ["2026-08-16", "2026-08-17"],
        "nama_pasien": "Andi Pratama",
        "bulan": "2026-08",
    },
}


def test_read_endpoint_returns_contract_b2_answer_without_label():
    response = client.post("/v1/baca", json={**BACA_REQUEST, "field_baru": "diabaikan"})

    assert response.status_code == 200
    body = response.json()
    assert body["jumlah_maks"] == 3
    assert body["versi_pembaca"] == config.READER_VERSION
    assert not {"label", "langkah_disarankan", "saran", "skor", "hasil"} & body.keys()


def test_read_endpoint_rejects_empty_transcript_with_422():
    app.dependency_overrides[get_answer_reader] = lambda: AnswerReader(FailingGenerator("x"))

    response = client.post("/v1/baca", json={**BACA_REQUEST, "transkrip": []})

    assert response.status_code == 422
    assert response.json()["galat"]["kode"] == "transkrip_kosong"


@pytest.mark.parametrize(
    ("provider_code", "status", "code"),
    [("penyedia_tidak_tersedia", 502, "llm_gagal"), ("batas_waktu", 504, "batas_waktu")],
)
def test_read_endpoint_maps_provider_failures_to_contract_errors(provider_code, status, code):
    app.dependency_overrides[get_answer_reader] = lambda: AnswerReader(
        FailingGenerator(provider_code)
    )

    response = client.post("/v1/baca", json=BACA_REQUEST)

    assert response.status_code == status
    assert response.json()["galat"]["kode"] == code


def test_voice_token_endpoint_returns_only_ephemeral_credential():
    response = client.post(
        "/v1/suara/token",
        json={
            "nama_penerima": "Andi Pratama",
            "sapaan_penerima": "Bapak",
            "hubungan": "peserta",
            "nama_pasien": "Andi Pratama",
            "sapaan_pasien": "Bapak",
            "nama_rs": "RS Melati Sehat",
            "bulan": "Agustus",
            "tanggal_libur": ["16 Agustus", "17 Agustus"],
        },
    )

    assert response.status_code == 200
    assert response.json()["token"] == "auth_tokens/test"
    assert "permanent" not in response.text


def test_provider_endpoints_fail_clearly_when_gemini_is_not_configured(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    app.dependency_overrides.pop(get_answer_reader)

    response = client.post("/v1/baca", json=BACA_REQUEST)

    assert response.status_code == 503
    assert response.json()["galat"]["kode"] == "gemini_tidak_dikonfigurasi"


def test_voice_console_is_served_by_ai_service():
    response = client.get("/voice/")

    assert response.status_code == 200
    assert "Vedika Agen Suara" in response.text


def test_service_key_is_required_only_when_configured(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_KEY", "secret")

    missing = client.get("/v1/kesehatan")
    accepted = client.get("/v1/kesehatan", headers={"X-Kunci-Layanan": "secret"})

    assert missing.status_code == 401
    assert missing.json()["galat"]["kode"] == "kunci_salah"
    assert accepted.status_code == 200
