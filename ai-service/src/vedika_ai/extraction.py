"""Template-guided structured extraction."""

import re
from itertools import pairwise, product

import cv2
import numpy as np

from .imaging import crop
from .ocr import OcrEngine
from .schemas import DocumentContent
from .templates import DocumentTemplate

MONTHS = "Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember"
MONTH_NUMBERS = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}


def _ink_occupancy(rgb: np.ndarray) -> float:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    return float(np.mean(gray < 180))


def filled_rows(rgb: np.ndarray, template: DocumentTemplate) -> list[int]:
    filled: list[int] = []
    for index, signature_region in enumerate(template.signatures(), start=1):
        signature = crop(rgb, signature_region)
        # A supported physiotherapy session requires the patient's signature.
        # The threshold stays above the printed grid-line occupancy in an empty row.
        if _ink_occupancy(signature) >= 0.02:
            filled.append(index)
    return filled


def _extract_sep(text: str, template: DocumentTemplate, period: str | None) -> str | None:
    compact = re.sub(r"[^A-Z0-9]", "", text.upper()).replace("O", "0")
    match = re.search(r"\d{4}R\d{3}\d{4}V\d{6}", compact)
    if not match:
        return None
    candidate = match.group(0)
    if not candidate.startswith(template.kode_faskes):
        return None
    expected_month = _period_month(period)
    if expected_month is not None and candidate[8:10] != f"{expected_month:02d}":
        return None
    return candidate


def _extract_period(text: str) -> str | None:
    match = re.search(rf"\b({MONTHS})\s+(20\d{{2}})\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    return f"{match.group(1).capitalize()} {match.group(2)}"


def _period_month(period: str | None) -> int | None:
    if not period:
        return None
    return MONTH_NUMBERS.get(period.split(maxsplit=1)[0].lower())


def _date_candidates(day: int) -> tuple[int, ...]:
    # Tesseract frequently reads handwritten 8 as 3. Keep both possibilities;
    # the full sequence must have exactly one strictly increasing solution.
    candidates = [day]
    if day in {3, 13, 23}:
        candidates.append(day + 5)
    return tuple(candidates)


def _extract_session_dates(
    rgb: np.ndarray,
    template: DocumentTemplate,
    row_numbers: list[int],
    period: str | None,
    ocr: OcrEngine,
) -> list[str]:
    expected_month = _period_month(period)
    parsed: list[tuple[int, int]] = []
    for row_number in row_numbers:
        date_crop = crop(rgb, template.dates()[row_number - 1])
        enlarged = cv2.resize(date_crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        result = ocr.read(enlarged, page_segmentation=7)
        match = re.search(r"(?<!\d)(\d{1,2})\s*/\s*(\d{2})(?!\d)", result.text)
        if not match or result.confidence < 0.5:
            return []
        day, month = int(match.group(1)), int(match.group(2))
        if expected_month is not None and month != expected_month:
            if not (month == 3 and expected_month == 8):
                return []
            month = expected_month
        if not 1 <= day <= 31 or not 1 <= month <= 12:
            return []
        parsed.append((day, month))

    if not parsed or len({month for _, month in parsed}) != 1:
        return []
    valid_sequences = [
        sequence
        for sequence in product(*(_date_candidates(day) for day, _ in parsed))
        if all(first < second for first, second in pairwise(sequence))
    ]
    if len(valid_sequences) != 1:
        return []
    month = parsed[0][1]
    return [f"{day:02d}/{month:02d}" for day in valid_sequences[0]]


def _extract_written_total(
    rgb: np.ndarray,
    template: DocumentTemplate,
    filled_count: int,
    ocr: OcrEngine,
) -> int | None:
    digit_crop = crop(rgb, template.total_digit())
    enlarged = cv2.resize(digit_crop, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    results = [ocr.read(enlarged, page_segmentation=mode) for mode in (10, 13)]
    parsed: list[tuple[int, float]] = []
    for result in results:
        match = re.fullmatch(r"\D*([1-8])\D*", result.text.strip())
        if match:
            parsed.append((int(match.group(1)), result.confidence))
    for value, confidence in parsed:
        if value == filled_count and confidence >= 0.5:
            return value
    return None


def _extract_name(rgb: np.ndarray, template: DocumentTemplate, ocr: OcrEngine) -> str | None:
    region = template.regions.get("name")
    if region is None:
        return None
    enlarged = cv2.resize(crop(rgb, region), None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    result = ocr.read(enlarged, page_segmentation=6)
    if result.confidence < 0.8:
        return None
    match = re.match(r"[^A-Za-z]*([A-Za-z]+(?:\s+[A-Za-z]+)+)\s*\([LP]\)", result.text)
    return match.group(1).strip() if match else None


def _extract_card_number(rgb: np.ndarray, template: DocumentTemplate, ocr: OcrEngine) -> str | None:
    region = template.regions.get("card")
    if region is None:
        return None
    enlarged = cv2.resize(crop(rgb, region), None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    result = ocr.read(enlarged, page_segmentation=6)
    compact = re.sub(r"\D", "", result.text)
    if result.confidence < 0.7 or len(compact) != 13:
        return None
    return compact


def extract_content(
    rgb: np.ndarray,
    template: DocumentTemplate,
    ocr: OcrEngine,
) -> tuple[DocumentContent, str, float]:
    row_numbers = filled_rows(rgb, template)
    ocr_result = ocr.read(rgb)
    period = _extract_period(ocr_result.text)
    content = DocumentContent(
        nama=_extract_name(rgb, template, ocr),
        no_kartu=_extract_card_number(rgb, template, ocr),
        no_sep=_extract_sep(ocr_result.text, template, period),
        periode=period,
        baris_terisi=len(row_numbers),
        tanggal_sesi=_extract_session_dates(rgb, template, row_numbers, period, ocr),
        jumlah_kunjungan_tertulis=_extract_written_total(rgb, template, len(row_numbers), ocr),
        kemiripan_ttd_rerata=None,
    )
    return content, ocr_result.text, ocr_result.confidence


def unsupported_rows_region(
    template: DocumentTemplate, filled_count: int
) -> tuple[int, int, int, int]:
    first_missing = min(filled_count, len(template.row_y) - 1)
    y = template.row_y[first_missing]
    bottom = template.row_y[-1] + template.row_height
    return (85, y, 1070, bottom - y)
