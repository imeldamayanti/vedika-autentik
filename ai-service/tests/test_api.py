from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

from vedika_ai import config
from vedika_ai.main import app, get_pipeline
from vedika_ai.schemas import AnalysisResponse, ComparisonResponse

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


@pytest.fixture(autouse=True)
def fake_pipeline():
    app.dependency_overrides[get_pipeline] = FakePipeline
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

    assert {"/v1/kesehatan", "/v1/analisis", "/v1/bandingkan"} <= paths.keys()


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
    assert missing.json()["galat"]["kode"] == "kunci_layanan_tidak_valid"
    assert accepted.status_code == 200
