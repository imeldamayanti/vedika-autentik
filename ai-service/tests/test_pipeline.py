from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter

from vedika_ai.errors import ServiceError
from vedika_ai.extraction import filled_rows
from vedika_ai.imaging import render_document
from vedika_ai.ocr import EmptyOcr, TesseractOcr
from vedika_ai.pipeline import AnalysisPipeline
from vedika_ai.quality import assess_quality
from vedika_ai.schemas import ClaimContext
from vedika_ai.templates import resolve_template

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "dataset"


def dataset_file(folder: str, name: str, extension: str = "jpg") -> Path:
    return DATASET / folder / f"{name}.{extension}"


def render_jpg(folder: str, name: str, kode_faskes: str = "0901R014"):
    path = dataset_file(folder, name)
    template = resolve_template("", kode_faskes)
    return render_document(path.read_bytes(), path.name, template.canonical_size), template


def test_quality_gate_accepts_original_and_phone_photo():
    original, _ = render_jpg("01-berkas-asli", "VA-ASL-01")
    phone, _ = render_jpg("01-berkas-asli", "VA-ASL-04")

    assert assess_quality(original).quality.status == "baik"
    assert assess_quality(phone).quality.status == "baik"
    assert original.perspective_corrected is False
    assert phone.perspective_corrected is True


def test_quality_gate_rejects_all_bad_scan_fixtures():
    for name in ["VA-BRM-01", "VA-BRM-02", "VA-BRM-03"]:
        document, _ = render_jpg("05-scan-buram", name)
        assert assess_quality(document).quality.status == "scan_ulang", name


def test_multi_page_pdf_is_rejected_instead_of_silently_ignoring_pages():
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    stream = BytesIO()
    writer.write(stream)
    template = resolve_template("melati-v1", None)

    with pytest.raises(ServiceError) as raised:
        render_document(stream.getvalue(), "two-pages.pdf", template.canonical_size)

    assert raised.value.code == "terlalu_banyak_halaman"


def test_template_guided_row_count_matches_six_session_document():
    document, template = render_jpg("01-berkas-asli", "VA-ASL-03", "0901R027")

    assert filled_rows(document.canonical_rgb, template) == [1, 2, 3, 4, 5, 6]


def test_template_guided_row_count_matches_five_session_document():
    document, template = render_jpg("03-angka-disunting", "VA-DST-01")

    assert filled_rows(document.canonical_rgb, template) == [1, 2, 3, 4, 5]


def test_pipeline_emits_claim_mismatch_from_real_pdf_pixels():
    path = dataset_file("03-angka-disunting", "VA-DST-01", "pdf")
    pipeline = AnalysisPipeline(ocr=EmptyOcr())

    result = pipeline.analyze(
        path.read_bytes(),
        path.name,
        ClaimContext(sesi_ditagih=8, kode_faskes="0901R014"),
    )

    assert result.kualitas_scan.status == "baik"
    assert result.isi_lembar.baris_terisi == 5
    assert {finding.cek for finding in result.temuan} == {
        "suntingan",
        "kecocokan_klaim",
    }
    mismatch = next(finding for finding in result.temuan if finding.cek == "kecocokan_klaim")
    assert mismatch.kekuatan == "kuat"
    assert result.halaman_jpg
    assert result.sidik_jari.versi_fingerprint == "visual-phash64-v1"


def test_pipeline_compares_reliably_read_period_and_sep_with_claim():
    if not TesseractOcr.available():
        pytest.skip("Tesseract tidak tersedia")
    path = dataset_file("01-berkas-asli", "VA-ASL-03", "pdf")

    result = AnalysisPipeline().analyze(
        path.read_bytes(),
        path.name,
        ClaimContext(
            sesi_ditagih=6,
            kode_faskes="0901R027",
            periode="September 2026",
            sep="0901R0270926V000000",
        ),
    )

    mismatch = next(finding for finding in result.temuan if finding.cek == "kecocokan_klaim")
    assert "Periode layanan" in mismatch.kalimat
    assert "SEP" in mismatch.kalimat
    assert mismatch.area == [(780, 400, 380, 90), (780, 305, 380, 90)]


def test_pipeline_stops_authenticity_checks_for_bad_scan():
    path = dataset_file("05-scan-buram", "VA-BRM-01", "pdf")
    pipeline = AnalysisPipeline(ocr=EmptyOcr())

    result = pipeline.analyze(
        path.read_bytes(),
        path.name,
        ClaimContext(sesi_ditagih=8, kode_faskes="0901R014"),
    )

    assert result.kualitas_scan.status == "scan_ulang"
    assert result.temuan == []
    assert result.isi_lembar.baris_terisi is None


def test_masked_page_fingerprint_is_deterministic():
    path = dataset_file("01-berkas-asli", "VA-ASL-01", "pdf")
    pipeline = AnalysisPipeline(ocr=EmptyOcr())
    claim = ClaimContext(sesi_ditagih=8, kode_faskes="0901R014")

    first = pipeline.analyze(path.read_bytes(), path.name, claim)
    second = pipeline.analyze(path.read_bytes(), path.name, claim)

    assert first.sidik_jari == second.sidik_jari


def test_copy_paste_rows_reduce_supported_session_count():
    path = dataset_file("03-angka-disunting", "VA-DST-02", "pdf")
    pipeline = AnalysisPipeline(ocr=EmptyOcr())

    result = pipeline.analyze(
        path.read_bytes(),
        path.name,
        ClaimContext(sesi_ditagih=8, kode_faskes="0901R027"),
    )

    assert result.isi_lembar.baris_terisi == 8
    assert result.isi_lembar.baris_asli == 6
    assert {finding.cek for finding in result.temuan} == {
        "copy_paste",
        "kecocokan_klaim",
    }


def test_repeated_signature_does_not_remove_distinct_service_rows():
    path = dataset_file("04-buatan-ai", "VA-AI-02", "pdf")
    pipeline = AnalysisPipeline(ocr=EmptyOcr())

    result = pipeline.analyze(
        path.read_bytes(),
        path.name,
        ClaimContext(sesi_ditagih=8, kode_faskes="0901R027"),
    )

    assert result.isi_lembar.baris_asli == 8
    assert {finding.cek for finding in result.temuan} == {"copy_paste", "tanda_ai"}


def test_pair_comparison_confirms_known_duplicate_and_rejects_unrelated_file():
    source = dataset_file("02-berkas-kembar", "VA-KMB-00", "pdf")
    duplicate = dataset_file("02-berkas-kembar", "VA-KMB-01", "pdf")
    unrelated = dataset_file("01-berkas-asli", "VA-ASL-02", "pdf")
    pipeline = AnalysisPipeline(ocr=EmptyOcr())

    matching = pipeline.compare(
        source.read_bytes(), source.name, duplicate.read_bytes(), duplicate.name
    )
    different = pipeline.compare(
        source.read_bytes(), source.name, unrelated.read_bytes(), unrelated.name
    )

    assert matching.sama is True
    assert matching.kemiripan >= 0.97
    assert len(matching.tempelan) == 8
    assert different.sama is False
    assert different.tempelan == []


def test_masked_fingerprint_feeds_backend_exact_candidate_search():
    source = dataset_file("02-berkas-kembar", "VA-KMB-00", "pdf")
    duplicate = dataset_file("02-berkas-kembar", "VA-KMB-02", "pdf")
    unrelated = dataset_file("01-berkas-asli", "VA-ASL-01", "pdf")
    pipeline = AnalysisPipeline(ocr=EmptyOcr())
    claim = ClaimContext(kode_faskes="0901R014")

    source_hash = pipeline.analyze(source.read_bytes(), source.name, claim).sidik_jari.halaman
    duplicate_hash = pipeline.analyze(
        duplicate.read_bytes(), duplicate.name, claim
    ).sidik_jari.halaman
    unrelated_hash = pipeline.analyze(
        unrelated.read_bytes(), unrelated.name, claim
    ).sidik_jari.halaman

    assert source_hash == duplicate_hash
    assert source_hash != unrelated_hash
