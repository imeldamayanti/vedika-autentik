"""Decode input documents and produce one canonical page image."""

import base64
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader

from .errors import ServiceError
from .schemas import PageSize


@dataclass(frozen=True)
class RenderedDocument:
    original_rgb: np.ndarray
    canonical_rgb: np.ndarray
    original_size: PageSize
    page_count: int
    metadata: dict[str, str | int | float | bool | None]
    perspective_corrected: bool


def _order_quad(points: np.ndarray) -> np.ndarray:
    ordered = np.zeros((4, 2), dtype=np.float32)
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).reshape(-1)
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(differences)]
    ordered[3] = points[np.argmax(differences)]
    return ordered


def _page_quad(rgb: np.ndarray) -> np.ndarray | None:
    """Find a photographed paper boundary; ignore scans already filling the frame."""
    height, width = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = float(width * height)
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        area_ratio = cv2.contourArea(contour) / page_area
        if not 0.45 <= area_ratio <= 0.95:
            continue
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(polygon) != 4 or not cv2.isContourConvex(polygon):
            continue
        points = _order_quad(polygon.reshape(4, 2).astype(np.float32))
        # A real photo has visible background around at least part of the paper.
        distances = np.column_stack(
            [points[:, 0], width - points[:, 0], points[:, 1], height - points[:, 1]]
        )
        if float(np.max(np.min(distances, axis=1))) < min(width, height) * 0.02:
            continue
        return points
    return None


def _normalize_page(rgb: np.ndarray, target_size: PageSize) -> tuple[np.ndarray, bool]:
    target_width, target_height = target_size
    quad = _page_quad(rgb)
    if quad is not None:
        destination = np.array(
            [
                [0, 0],
                [target_width - 1, 0],
                [target_width - 1, target_height - 1],
                [0, target_height - 1],
            ],
            dtype=np.float32,
        )
        transform = cv2.getPerspectiveTransform(quad, destination)
        return (
            cv2.warpPerspective(
                rgb,
                transform,
                (target_width, target_height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            ),
            True,
        )

    height, width = rgb.shape[:2]
    interpolation = (
        cv2.INTER_AREA if width > target_width or height > target_height else cv2.INTER_CUBIC
    )
    return cv2.resize(rgb, (target_width, target_height), interpolation=interpolation), False


def _pdf_metadata(content: bytes) -> tuple[int, dict[str, str | None]]:
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise ServiceError(422, "tidak_terbaca", "PDF terenkripsi tidak dapat diperiksa.")
        metadata = {
            str(key).lstrip("/"): str(value) if value is not None else None
            for key, value in (reader.metadata or {}).items()
        }
        return len(reader.pages), metadata
    except ServiceError:
        raise
    except Exception as error:
        raise ServiceError(422, "tidak_terbaca", "PDF rusak atau tidak dapat dibaca.") from error


def _render_pdf(content: bytes) -> tuple[np.ndarray, int, dict[str, str | None]]:
    page_count, metadata = _pdf_metadata(content)
    if page_count < 1:
        raise ServiceError(422, "tidak_terbaca", "PDF tidak memiliki halaman.")
    if page_count > 1:
        raise ServiceError(422, "terlalu_banyak_halaman", "Maksimal satu halaman per berkas.")
    try:
        document = pdfium.PdfDocument(content)
        page = document[0]
        image = page.render(scale=150 / 72).to_pil().convert("RGB")
        rgb = np.asarray(image)
        page.close()
        document.close()
        return rgb, page_count, metadata
    except Exception as error:
        raise ServiceError(422, "tidak_terbaca", "PDF tidak dapat dirender.") from error


def _render_image(content: bytes) -> tuple[np.ndarray, dict[str, str | int | None]]:
    try:
        with Image.open(BytesIO(content)) as source:
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
            metadata: dict[str, str | int | None] = {
                "Format": source.format,
                "Width": image.width,
                "Height": image.height,
            }
            for key, value in source.getexif().items():
                metadata[f"EXIF:{key}"] = str(value)
            return np.asarray(image), metadata
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ServiceError(422, "tidak_terbaca", "Gambar rusak atau tidak dapat dibaca.") from error


def render_document(content: bytes, filename: str, canonical_size: PageSize) -> RenderedDocument:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        if not content.startswith(b"%PDF"):
            raise ServiceError(422, "tidak_terbaca", "Isi berkas bukan PDF yang valid.")
        original, page_count, metadata = _render_pdf(content)
    else:
        original, metadata = _render_image(content)
        page_count = 1

    height, width = original.shape[:2]
    canonical, perspective_corrected = _normalize_page(original, canonical_size)
    return RenderedDocument(
        original_rgb=original,
        canonical_rgb=canonical,
        original_size=(width, height),
        page_count=page_count,
        metadata=metadata,
        perspective_corrected=perspective_corrected,
    )


def encode_jpeg_base64(rgb: np.ndarray) -> str:
    success, encoded = cv2.imencode(
        ".jpg",
        cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
        [cv2.IMWRITE_JPEG_QUALITY, 88],
    )
    if not success:
        raise ServiceError(500, "galat_internal", "Halaman hasil normalisasi tidak dapat disimpan.")
    return base64.b64encode(encoded.tobytes()).decode("ascii")


def crop(rgb: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray:
    x, y, width, height = region
    return rgb[y : y + height, x : x + width]
