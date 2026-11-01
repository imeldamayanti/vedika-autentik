"""Conservative provenance rules based on explicit file metadata."""

import re

from .schemas import Finding

PROVENANCE_RULE_VERSION = "provenance-v1"
TEMPLATE_TEXT_ANCHORS = {
    "melati-v1": "kenanga raya",
    "cipta-medika-v1": "percetakan negara",
    "bakti-mulia-v1": "cempaka barat",
}


def inspect_provenance(
    metadata: dict[str, str | int | float | bool | None],
) -> list[Finding]:
    values = " ".join(str(value).lower() for value in metadata.values() if value is not None)
    findings: list[Finding] = []

    if "photoshop" in values or "gimp" in values:
        findings.append(
            Finding(
                cek="suntingan",
                kekuatan="sedang",
                kalimat=(
                    "Metadata menunjukkan berkas pernah diproses dengan editor gambar; "
                    "lokasi perubahan belum dapat dipastikan dari metadata saja."
                ),
                skor=0.7,
            )
        )

    if "canva" in values:
        findings.append(
            Finding(
                cek="tanda_ai",
                kekuatan="sedang",
                kalimat=(
                    "Metadata menunjukkan berkas dibuat dengan aplikasi desain Canva; "
                    "temuan ini merupakan bukti pendukung, bukan vonis fraud."
                ),
                skor=0.8,
            )
        )

    return findings


def inspect_template_text(text: str, confidence: float, template_id: str) -> list[Finding]:
    """Flag a missing static hospital anchor only when OCR itself is reliable."""
    anchor = TEMPLATE_TEXT_ANCHORS.get(template_id)
    if not anchor or confidence < 0.5:
        return []
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    if anchor in normalized:
        return []
    return [
        Finding(
            cek="tanda_ai",
            kekuatan="lemah",
            kalimat=(
                "Teks statis pada kop tidak cocok dengan template rumah sakit; "
                "sumber dokumen perlu diperiksa."
            ),
            skor=0.55,
        )
    ]
