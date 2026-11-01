"""Deterministic masked visual fingerprints."""

import hashlib

import cv2
import numpy as np

from .imaging import crop
from .schemas import Fingerprint
from .templates import DocumentTemplate

FINGERPRINT_VERSION = "visual-phash64-v1"


def hamming_distance(first_hash: str, second_hash: str) -> int:
    """Return the bit distance between two 64-bit hexadecimal fingerprints."""
    if len(first_hash) != 16 or len(second_hash) != 16:
        raise ValueError("Sidik jari harus berupa 16 digit heksadesimal.")
    try:
        return (int(first_hash, 16) ^ int(second_hash, 16)).bit_count()
    except ValueError as error:
        raise ValueError("Sidik jari harus berupa 16 digit heksadesimal.") from error


def _phash64(rgb: np.ndarray) -> str:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    transformed = cv2.dct(np.float32(resized))[:8, :8]
    median = float(np.median(transformed[1:, :]))
    bits = (transformed > median).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def build_fingerprint(rgb: np.ndarray, template: DocumentTemplate) -> Fingerprint:
    masked = rgb.copy()
    for name in template.fingerprint_masks:
        x, y, width, height = template.regions[name]
        masked[y : y + height, x : x + width] = 255
    for x, y, width, height in template.dates():
        masked[y : y + height, x : x + width] = 255
    page_hash = _phash64(masked)
    row_hashes = [_phash64(crop(masked, region)) for region in template.rows()]
    text_surrogate = hashlib.sha256((page_hash + "".join(row_hashes)).encode()).hexdigest()[:16]
    return Fingerprint(
        algoritma="phash64-visual",
        halaman=page_hash,
        baris=row_hashes,
        teks=text_surrogate,
        versi_fingerprint=FINGERPRINT_VERSION,
    )
