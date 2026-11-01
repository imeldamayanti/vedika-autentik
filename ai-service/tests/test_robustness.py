from pathlib import Path

import cv2
import numpy as np
import pytest

from vedika_ai.fingerprints import build_fingerprint, hamming_distance
from vedika_ai.imaging import render_document
from vedika_ai.templates import resolve_template

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "dataset" / "01-berkas-asli" / "VA-ASL-01.jpg"


def _fingerprint(content: bytes, filename: str):
    template = resolve_template("melati-v1", None)
    document = render_document(content, filename, template.canonical_size)
    return build_fingerprint(document.canonical_rgb, template)


def _encode(image: np.ndarray, quality: int = 70) -> bytes:
    success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    assert success
    return encoded.tobytes()


@pytest.mark.parametrize("transformation", ["jpeg", "resize", "brightness"])
def test_fingerprint_remains_close_after_safe_transport_transforms(transformation):
    source_bytes = SOURCE.read_bytes()
    image = cv2.imdecode(np.frombuffer(source_bytes, np.uint8), cv2.IMREAD_COLOR)
    if transformation == "jpeg":
        transformed = _encode(image, quality=35)
    elif transformation == "resize":
        half = cv2.resize(
            image,
            (image.shape[1] // 2, image.shape[0] // 2),
            interpolation=cv2.INTER_AREA,
        )
        transformed = _encode(half)
    else:
        transformed = _encode(cv2.convertScaleAbs(image, alpha=1, beta=12), quality=75)

    original = _fingerprint(source_bytes, SOURCE.name)
    variant = _fingerprint(transformed, f"{transformation}.jpg")
    page_distance = hamming_distance(original.halaman, variant.halaman)
    row_distance = sum(
        hamming_distance(first, second)
        for first, second in zip(original.baris, variant.baris, strict=True)
    )

    assert page_distance <= 6
    assert row_distance <= 24


def test_hamming_distance_rejects_malformed_hashes():
    with pytest.raises(ValueError, match="16 digit"):
        hamming_distance("abc", "0" * 16)
