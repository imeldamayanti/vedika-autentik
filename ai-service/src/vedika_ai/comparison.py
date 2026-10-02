"""Deterministic within-document and pairwise reuse detection."""

from dataclasses import dataclass
from itertools import combinations

import cv2
import numpy as np

from .extraction import filled_rows
from .imaging import crop, render_document
from .schemas import ComparisonResponse, Finding, PastedRegion, Region
from .templates import DocumentTemplate, resolve_template

SIGNATURE_SIMILARITY_THRESHOLD = 0.92
COPIED_ROW_SIMILARITY_THRESHOLD = 0.97
DUPLICATE_PAGE_SIMILARITY_THRESHOLD = 0.97
THRESHOLD_VERSION = "reuse-v1"


@dataclass(frozen=True)
class CopyPasteAnalysis:
    finding: Finding | None
    duplicated_rows: frozenset[int]
    average_signature_similarity: float


def _normalized_gray(rgb: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    resized = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
    background = cv2.GaussianBlur(resized, (0, 0), 5)
    return cv2.divide(resized, background, scale=255)


def crop_similarity(first: np.ndarray, second: np.ndarray) -> float:
    """Compare aligned crops while allowing a few pixels of scan movement."""
    first_gray = _normalized_gray(first, (256, 64))
    second_gray = _normalized_gray(second, (256, 64))
    padded = cv2.copyMakeBorder(
        second_gray,
        5,
        5,
        5,
        5,
        cv2.BORDER_CONSTANT,
        value=255,
    )
    score = cv2.minMaxLoc(cv2.matchTemplate(padded, first_gray, cv2.TM_CCOEFF_NORMED))[1]
    return max(0.0, min(1.0, float(score)))


def _bounding_region(regions: list[Region]) -> Region:
    left = min(region[0] for region in regions)
    top = min(region[1] for region in regions)
    right = max(region[0] + region[2] for region in regions)
    bottom = max(region[1] + region[3] for region in regions)
    return (left, top, right - left, bottom - top)


def detect_copy_paste(rgb: np.ndarray, template: DocumentTemplate) -> CopyPasteAnalysis:
    signatures = template.signatures()
    signature_crops = [crop(rgb, region) for region in signatures]
    active_indexes = [row - 1 for row in filled_rows(rgb, template)]
    pair_scores = [
        (first, second, crop_similarity(signature_crops[first], signature_crops[second]))
        for first, second in combinations(active_indexes, 2)
    ]
    average = sum(score for _, _, score in pair_scores) / len(pair_scores) if pair_scores else 0.0
    matches = [
        (first, second, score)
        for first, second, score in pair_scores
        if score >= SIGNATURE_SIMILARITY_THRESHOLD
    ]
    if not matches:
        return CopyPasteAnalysis(None, frozenset(), round(average, 3))

    # A repeated signature is evidence of copy-paste, but it is not enough to
    # invalidate a session. A row is counted as duplicated only when its
    # service and therapist content also match at near-pixel level.
    service_regions: list[Region] = [
        (250, y + 6, 650, template.row_height - 12) for y in template.row_y
    ]
    service_crops = [crop(rgb, region) for region in service_regions]
    duplicated_rows: set[int] = set()
    copied_pairs: list[tuple[int, int, float]] = []
    for first, second, signature_score in matches:
        row_score = crop_similarity(service_crops[first], service_crops[second])
        if row_score >= COPIED_ROW_SIMILARITY_THRESHOLD:
            duplicated_rows.add(second + 1)
            copied_pairs.append((first, second, min(signature_score, row_score)))

    if copied_pairs:
        evidence_regions = [template.rows()[second] for _, second, _ in copied_pairs]
        sources = ", ".join(str(first + 1) for first, _, _ in copied_pairs)
        targets = ", ".join(str(second + 1) for _, second, _ in copied_pairs)
        sentence = (
            f"Baris {targets} sangat cocok dengan baris {sources}, termasuk isi layanan "
            "dan tanda tangannya."
        )
        score = max(score for _, _, score in copied_pairs)
    else:
        matched_indexes = sorted(
            {index for first, second, _ in matches for index in (first, second)}
        )
        evidence_regions = [signatures[index] for index in matched_indexes]
        sentence = (
            f"{len(matched_indexes)} tanda tangan memiliki pola piksel yang nyaris identik "
            "dan terindikasi ditempel berulang."
        )
        score = max(score for _, _, score in matches)

    finding = Finding(
        cek="copy_paste",
        kekuatan="kuat",
        kalimat=sentence,
        region=_bounding_region(evidence_regions),
        area=evidence_regions,
        skor=round(score, 3),
    )
    return CopyPasteAnalysis(finding, frozenset(duplicated_rows), round(average, 3))


def _masked_page(rgb: np.ndarray, template: DocumentTemplate) -> np.ndarray:
    masked = rgb.copy()
    for name in template.fingerprint_masks:
        x, y, width, height = template.regions[name]
        masked[y : y + height, x : x + width] = 255
    for x, y, width, height in template.dates():
        masked[y : y + height, x : x + width] = 255
    return cv2.resize(
        cv2.cvtColor(masked, cv2.COLOR_RGB2GRAY),
        (620, 877),
        interpolation=cv2.INTER_AREA,
    )


def _page_similarity(first: np.ndarray, second: np.ndarray, template: DocumentTemplate) -> float:
    first_gray = _masked_page(first, template)
    second_gray = _masked_page(second, template)
    return max(
        0.0,
        min(
            1.0,
            float(cv2.matchTemplate(first_gray, second_gray, cv2.TM_CCOEFF_NORMED)[0, 0]),
        ),
    )


def compare_documents(
    content_a: bytes,
    filename_a: str,
    content_b: bytes,
    filename_b: str,
) -> ComparisonResponse:
    # All three MVP templates currently use the same normalized geometry.
    template = resolve_template("melati-v1", None)
    first = render_document(content_a, filename_a, template.canonical_size)
    second = render_document(content_b, filename_b, template.canonical_size)
    similarity = _page_similarity(first.canonical_rgb, second.canonical_rgb, template)
    same = similarity >= DUPLICATE_PAGE_SIMILARITY_THRESHOLD

    pasted: list[PastedRegion] = []
    if same:
        for index, (region_a, region_b) in enumerate(
            zip(template.signatures(), template.signatures(), strict=True),
            start=1,
        ):
            score = crop_similarity(
                crop(first.canonical_rgb, region_a),
                crop(second.canonical_rgb, region_b),
            )
            if score >= SIGNATURE_SIMILARITY_THRESHOLD:
                pasted.append(
                    PastedRegion(
                        bagian=f"ttd-{index}",
                        region_a=region_a,
                        region_b=region_b,
                        kemiripan=round(score, 3),
                    )
                )

    table = template.regions["table"]
    if same:
        sentence = (
            f"Isi berkas {round(similarity * 100)}% sama dengan berkas pembanding "
            "setelah kolom identitas dan tanggal ditutup."
        )
    else:
        sentence = "Isi kedua berkas berbeda setelah kolom identitas dan tanggal ditutup."
    return ComparisonResponse(
        kemiripan=round(similarity, 3),
        sama=same,
        kalimat=sentence,
        region_a=[table] if same else [],
        region_b=[table] if same else [],
        tempelan=pasted,
    )
