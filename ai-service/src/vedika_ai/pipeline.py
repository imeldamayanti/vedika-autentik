"""Single-document analysis and pairwise comparison pipeline."""

import time

from . import config
from .comparison import compare_documents, detect_copy_paste
from .extraction import extract_content, unsupported_rows_region
from .fingerprints import build_fingerprint
from .imaging import encode_jpeg_base64, render_document
from .ocr import OcrEngine, TesseractOcr
from .provenance import inspect_provenance, inspect_template_text
from .quality import assess_quality
from .schemas import AnalysisResponse, ClaimContext, ComparisonResponse, DocumentContent, Finding
from .templates import resolve_template


class AnalysisPipeline:
    def __init__(self, ocr: OcrEngine | None = None):
        self.ocr = ocr or TesseractOcr()

    @property
    def ready(self) -> bool:
        return not isinstance(self.ocr, TesseractOcr) or self.ocr.available()

    @property
    def models(self) -> list[str]:
        return [self.ocr.name] if self.ready else []

    def analyze(
        self,
        content: bytes,
        filename: str,
        claim: ClaimContext,
        template_id: str = "",
    ) -> AnalysisResponse:
        started = time.perf_counter()
        template = resolve_template(template_id, claim.kode_faskes)
        document = render_document(content, filename, template.canonical_size)
        assessment = assess_quality(document)
        fingerprint = build_fingerprint(document.canonical_rgb, template)
        findings: list[Finding] = []

        if assessment.quality.status == "scan_ulang":
            document_content = DocumentContent()
        else:
            document_content, ocr_text, ocr_confidence = extract_content(
                document.canonical_rgb,
                template,
                self.ocr,
            )
            reuse = detect_copy_paste(document.canonical_rgb, template)
            supported = (document_content.baris_terisi or 0) - len(reuse.duplicated_rows)
            document_content = document_content.model_copy(
                update={
                    "baris_asli": supported,
                    "kemiripan_ttd_rerata": reuse.average_signature_similarity,
                }
            )
            if reuse.finding is not None:
                findings.append(reuse.finding)
            provenance = inspect_provenance(document.metadata)
            if reuse.finding is not None:
                provenance = [finding for finding in provenance if finding.cek != "suntingan"]
            findings.extend(provenance)
            findings.extend(inspect_template_text(ocr_text, ocr_confidence, template.id))
            mismatch_phrases: list[str] = []
            mismatch_regions: list[tuple[int, int, int, int]] = []
            if claim.sesi_ditagih is not None and supported < claim.sesi_ditagih:
                if reuse.duplicated_rows:
                    mismatch_phrases.append(
                        f"ditagih {claim.sesi_ditagih} sesi dan setelah baris salinan "
                        f"dikeluarkan, berkas hanya mendukung {supported}"
                    )
                    copied_regions = [
                        template.rows()[index - 1] for index in sorted(reuse.duplicated_rows)
                    ]
                    mismatch_regions.append(
                        reuse.finding.region if reuse.finding else copied_regions[0]
                    )
                else:
                    mismatch_phrases.append(
                        f"ditagih {claim.sesi_ditagih} sesi, berkas hanya mendukung {supported}"
                    )
                    mismatch_regions.append(unsupported_rows_region(template, supported))

            if (
                claim.periode
                and document_content.periode
                and claim.periode.casefold() != document_content.periode.casefold()
            ):
                mismatch_phrases.append("periode layanan pada berkas berbeda dari klaim")
                mismatch_regions.append(template.regions["periode"])

            if claim.sep and document_content.no_sep and claim.sep != document_content.no_sep:
                mismatch_phrases.append("SEP yang terbaca pada berkas berbeda dari klaim")
                mismatch_regions.append(template.regions["sep"])

            if mismatch_phrases:
                sentence = "; ".join(mismatch_phrases)
                sentence = sentence[0].upper() + sentence[1:] + "."
                findings.append(
                    Finding(
                        cek="kecocokan_klaim",
                        kekuatan="kuat",
                        kalimat=sentence,
                        region=mismatch_regions[0],
                        area=mismatch_regions if len(mismatch_regions) > 1 else None,
                        skor=round(max(0.9, ocr_confidence), 3),
                    )
                )

        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return AnalysisResponse(
            versi_mesin=config.ENGINE_VERSION,
            ukuran=template.canonical_size,
            halaman_jpg=encode_jpeg_base64(document.canonical_rgb),
            kualitas_scan=assessment.quality,
            isi_lembar=document_content,
            temuan=findings,
            metadata_file=document.metadata,
            sidik_jari=fingerprint,
            waktu_proses_ms=elapsed_ms,
            template_id=template.id,
            versi_template=template.version,
        )

    def compare(
        self,
        content_a: bytes,
        filename_a: str,
        content_b: bytes,
        filename_b: str,
    ) -> ComparisonResponse:
        return compare_documents(content_a, filename_a, content_b, filename_b)
