from typing import ClassVar

import pytest
from fastapi.testclient import TestClient
from loguru import logger

from vedika_ai import config
from vedika_ai.answer_reader import AnswerReader
from vedika_ai.answers import JawabanTerstruktur
from vedika_ai.gemini import GeminiError
from vedika_ai.main import app, get_answer_reader, get_pipeline, get_token_issuer
from vedika_ai.schemas import AnalysisResponse, ComparisonResponse
from vedika_ai.voice import VoiceTokenResponse

client = TestClient(app)


class FakePipeline:
    ready = True
    models: ClassVar[list[str]] = ["fake-ocr"]

    def analyze(self, content, filename, claim, template):
        del content, filename, claim, template
        return AnalysisResponse.model_validate(
            {
                "versi_mesin": "pramana-0.5.0",
                "ukuran": [1240, 1754],
                "halaman_jpg": "jpeg-base64",
                "kualitas_scan": {"status": "baik", "catatan": "Terbaca."},
                "isi_lembar": {"baris_terisi": 8},
                "temuan": [],
                "metadata_file": {},
                "sidik_jari": {
                    "algoritma": "phash64-visual",
                    "halaman": "a3f09c",
                    "baris": [],
                    "teks": "7d21",
                },
                "waktu_proses_ms": 10,
                "template_id": "melati-v1",
                "versi_template": "1.0",
            }
        )

    def compare(self, content_a, filename_a, content_b, filename_b):
        del content_a, filename_a, content_b, filename_b
        return ComparisonResponse(
            kemiripan=0.98,
            sama=True,
            kalimat="Isi berkas 98% sama dengan berkas pembanding.",
            region_a=[(85, 540, 1070, 782)],
            region_b=[(85, 540, 1070, 782)],
            tempelan=[],
        )


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
def fake_pipeline():
    app.dependency_overrides[get_pipeline] = FakePipeline
    app.dependency_overrides[get_answer_reader] = FakeAnswerReader
    app.dependency_overrides[get_token_issuer] = FakeTokenIssuer
    yield
    app.dependency_overrides.clear()


def pdf_file(name: str = "sample.pdf", content: bytes = b"%PDF-1.4\n%%EOF"):
    return {"file": (name, content, "application/pdf")}


def test_health_reports_analysis_readiness():
    response = client.get("/v1/kesehatan")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "versi_mesin": "pramana-0.5.0",
        "model": ["fake-ocr"],
        "siap_analisis": True,
    }
    assert response.headers["X-Request-ID"]


def test_openapi_contains_all_contract_b_endpoints():
    paths = client.get("/openapi.json").json()["paths"]

    assert {
        "/v1/kesehatan",
        "/v1/analisis",
        "/v1/bandingkan",
        "/v1/indikator",
        "/v1/baca",
        "/v1/suara/token",
    } <= paths.keys()


def test_indicator_endpoint_returns_auditable_flags():
    response = client.post(
        "/v1/indikator",
        json={
            "bulan": "2026-08",
            "sesi": [
                {"tanggal": f"2026-08-{day:02d}", "hari_libur": day == 17}
                for day in range(1, 10)
            ],
            "bulan_aktif": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["i1"] is True
    assert response.json()["masuk_antrean"] is True
    assert response.json()["indikator_aktif"] == ["I1", "I2", "I4"]


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


def test_analysis_returns_contract_b_result():
    response = client.post(
        "/v1/analisis",
        files=pdf_file(),
        data={"klaim": '{"sesi_ditagih": 8}', "template": "melati-v1"},
    )

    assert response.status_code == 200
    assert response.json()["kualitas_scan"]["status"] == "baik"
    assert response.json()["template_id"] == "melati-v1"
    assert "label" not in response.json()


def test_analysis_rejects_invalid_claim_without_echoing_input():
    response = client.post(
        "/v1/analisis",
        files=pdf_file(),
        data={"klaim": "not-json"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "galat": {"kode": "klaim_tidak_valid", "pesan": "Konteks klaim tidak valid."}
    }


def test_request_logs_do_not_contain_filename_or_claim_values():
    messages = []
    sink_id = logger.add(lambda message: messages.append(str(message)), format="{message}")
    try:
        response = client.post(
            "/v1/analisis",
            files=pdf_file(name="participant-987654321.pdf"),
            data={"klaim": '{"sep":"SEP-PRIVATE-123","sesi_ditagih":8}'},
        )
    finally:
        logger.remove(sink_id)

    assert response.status_code == 200
    logged = "".join(messages)
    assert "participant-987654321.pdf" not in logged
    assert "SEP-PRIVATE-123" not in logged


def test_analysis_rejects_unsupported_extension():
    response = client.post(
        "/v1/analisis",
        files=pdf_file(name="sample.txt"),
        data={"klaim": "{}"},
    )

    assert response.status_code == 415
    assert response.json()["galat"]["kode"] == "format_tidak_didukung"


def test_analysis_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(config, "MAX_FILE_BYTES", 4)
    response = client.post(
        "/v1/analisis",
        files=pdf_file(content=b"12345"),
        data={"klaim": "{}"},
    )

    assert response.status_code == 413
    assert response.json()["galat"]["kode"] == "terlalu_besar"


def test_comparison_returns_contract_b_result():
    response = client.post(
        "/v1/bandingkan",
        files={
            "file_a": ("a.pdf", b"%PDF-a", "application/pdf"),
            "file_b": ("b.pdf", b"%PDF-b", "application/pdf"),
        },
    )

    assert response.status_code == 200
    assert response.json()["sama"] is True
    assert response.json()["kemiripan"] == 0.98


def test_service_key_is_required_only_when_configured(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_KEY", "secret")

    missing = client.get("/v1/kesehatan")
    accepted = client.get("/v1/kesehatan", headers={"X-Kunci-Layanan": "secret"})

    assert missing.status_code == 401
    assert missing.json()["galat"]["kode"] == "kunci_salah"
    assert accepted.status_code == 200
