"""Deterministic scan-quality measurements and gate."""

from dataclasses import dataclass

import cv2
import numpy as np

from .imaging import RenderedDocument
from .schemas import Region, ScanQuality

EXPECTED_ASPECT_RATIO = 1240 / 1754
MIN_SHARPNESS_RAW = 50.0
MIN_BRIGHTNESS = 0.55
MAX_ASPECT_DELTA = 0.10


@dataclass(frozen=True)
class QualityAssessment:
    quality: ScanQuality
    region: Region | None


def _estimate_skew(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 1800, 350)
    if lines is None:
        return 0.0
    angles: list[float] = []
    for rho_theta in lines[:50]:
        theta = float(rho_theta[0][1])
        angle = np.degrees(theta) - 90
        if -10 <= angle <= 10:
            angles.append(angle)
    return round(float(np.median(angles)), 2) if angles else 0.0


def assess_quality(document: RenderedDocument) -> QualityAssessment:
    original_gray = cv2.cvtColor(document.original_rgb, cv2.COLOR_RGB2GRAY)
    canonical_gray = cv2.cvtColor(document.canonical_rgb, cv2.COLOR_RGB2GRAY)
    raw_sharpness = float(cv2.Laplacian(original_gray, cv2.CV_64F).var())
    sharpness = round(min(1.0, raw_sharpness / 500.0), 3)
    brightness = round(float(original_gray.mean() / 255), 3)
    contrast = round(float(original_gray.std() / 64), 3)
    width, height = document.original_size
    aspect_delta = abs((width / height) - EXPECTED_ASPECT_RATIO)
    skew = _estimate_skew(canonical_gray)

    reasons: list[str] = []
    region: Region | None = None
    if raw_sharpness < MIN_SHARPNESS_RAW:
        reasons.append("tulisan buram")
    if brightness < MIN_BRIGHTNESS:
        reasons.append("gambar terlalu gelap")
    if aspect_delta > MAX_ASPECT_DELTA:
        reasons.append("bagian halaman terpotong")
        if width / height < EXPECTED_ASPECT_RATIO:
            region = (990, 0, 250, 1754)
        else:
            region = (0, 1350, 1240, 404)

    if reasons:
        sentence = ", ".join(reasons).capitalize() + ". Minta rumah sakit memindai ulang."
        status = "scan_ulang"
    else:
        sentence = f"Berkas terbaca, kemiringan {abs(skew):.1f} derajat."
        status = "baik"

    quality = ScanQuality(
        status=status,
        catatan=sentence,
        ketajaman=sharpness,
        miring_derajat=skew,
        kecerahan=brightness,
        kontras=contrast,
        rasio_aspek=round(width / height, 3),
        perspektif_dikoreksi=document.perspective_corrected,
    )
    return QualityAssessment(quality=quality, region=region)
