from functools import lru_cache
from pathlib import Path

import pytest

from vedika_ai.extraction import extract_content
from vedika_ai.imaging import render_document
from vedika_ai.ocr import TesseractOcr
from vedika_ai.templates import resolve_template

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "dataset"


@lru_cache
def _extract(folder: str, name: str, kode_faskes: str):
    ocr = TesseractOcr()
    if not ocr.available():
        pytest.skip("Tesseract tidak tersedia")
    path = DATASET / folder / f"{name}.pdf"
    template = resolve_template("", kode_faskes)
    document = render_document(path.read_bytes(), path.name, template.canonical_size)
    content, _, _ = extract_content(document.canonical_rgb, template, ocr)
    return content


@pytest.mark.parametrize(
    ("folder", "name", "kode_faskes", "expected"),
    [
        (
            "01-berkas-asli",
            "VA-ASL-01",
            "0901R014",
            ["04/08", "07/08", "11/08", "14/08", "18/08", "21/08", "25/08", "28/08"],
        ),
        (
            "01-berkas-asli",
            "VA-ASL-04",
            "0901R014",
            ["03/08", "06/08", "10/08", "13/08", "17/08", "20/08", "24/08", "27/08"],
        ),
    ],
)
def test_constrained_date_extraction_is_exact(folder, name, kode_faskes, expected):
    assert _extract(folder, name, kode_faskes).tanggal_sesi == expected


def test_written_total_abstains_on_ambiguous_eight_and_accepts_clear_six():
    ambiguous = _extract("04-buatan-ai", "VA-AI-03", "0901R041")
    clear = _extract("01-berkas-asli", "VA-ASL-03", "0901R027")

    assert ambiguous.jumlah_kunjungan_tertulis is None
    assert clear.jumlah_kunjungan_tertulis == 6


def test_identity_fields_are_returned_only_when_high_confidence():
    assert _extract("01-berkas-asli", "VA-ASL-01", "0901R014").nama == "Hartono Wijaya"
    assert _extract("01-berkas-asli", "VA-ASL-02", "0901R041").no_kartu == "0001390447182"
    assert _extract("01-berkas-asli", "VA-ASL-03", "0901R027").no_sep == "0901R0270826V463370"
