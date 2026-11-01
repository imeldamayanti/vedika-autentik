import pytest
from pydantic import ValidationError

from vedika_ai.schemas import AnalysisResponse, ComparisonResponse


def valid_analysis() -> dict:
    return {
        "versi_mesin": "pramana-0.1.0",
        "ukuran": [1240, 1754],
        "halaman_jpg": None,
        "kualitas_scan": {"status": "baik", "catatan": "Terbaca."},
        "isi_lembar": {"no_sep": "contoh", "baris_terisi": 5},
        "temuan": [
            {
                "cek": "kecocokan_klaim",
                "kekuatan": "kuat",
                "kalimat": "Ditagih 8 sesi, berkas hanya mendukung 5.",
                "region": [90, 1036, 1065, 283],
                "skor": 0.98,
            }
        ],
        "metadata_file": {"Producer": "example"},
        "sidik_jari": {
            "algoritma": "phash64+simhash",
            "halaman": "a3f09c",
            "baris": ["baris-1"],
            "teks": "7d21",
        },
        "waktu_proses_ms": 4210,
    }


def test_analysis_response_accepts_contract_b_shape():
    result = AnalysisResponse.model_validate(valid_analysis())

    assert result.ukuran == (1240, 1754)
    assert result.temuan[0].cek == "kecocokan_klaim"


def test_analysis_response_forbids_label_and_suggestion():
    payload = valid_analysis() | {"label": "lolos", "saran": "wajar"}

    with pytest.raises(ValidationError):
        AnalysisResponse.model_validate(payload)


@pytest.mark.parametrize("check", ["berkas_kembar", "tempelan"])
def test_single_document_analysis_forbids_pair_only_findings(check):
    payload = valid_analysis()
    payload["temuan"][0]["cek"] = check

    with pytest.raises(ValidationError):
        AnalysisResponse.model_validate(payload)


def test_bad_scan_forbids_authenticity_findings():
    payload = valid_analysis()
    payload["kualitas_scan"] = {"status": "scan_ulang", "catatan": "Buram."}

    with pytest.raises(ValidationError):
        AnalysisResponse.model_validate(payload)


def test_ai_signal_cannot_be_strong():
    payload = valid_analysis()
    payload["temuan"][0] = {
        "cek": "tanda_ai",
        "kekuatan": "kuat",
        "kalimat": "Metadata menunjukkan aplikasi pembuat.",
    }

    with pytest.raises(ValidationError):
        AnalysisResponse.model_validate(payload)


def test_evidence_region_requires_positive_dimensions():
    payload = valid_analysis()
    payload["temuan"][0]["region"] = [90, 1036, 0, 283]

    with pytest.raises(ValidationError):
        AnalysisResponse.model_validate(payload)


def test_comparison_response_accepts_contract_b_shape():
    result = ComparisonResponse.model_validate(
        {
            "kemiripan": 0.97,
            "sama": True,
            "kalimat": "Isi berkas 97% sama dengan berkas pembanding.",
            "region_a": [[86, 541, 1069, 779]],
            "region_b": [[86, 541, 1069, 779]],
            "tempelan": [
                {
                    "bagian": "ttd-3",
                    "region_a": [901, 760, 251, 94],
                    "region_b": [901, 760, 251, 94],
                    "kemiripan": 0.99,
                }
            ],
        }
    )

    assert result.sama is True
    assert result.tempelan[0].bagian == "ttd-3"
