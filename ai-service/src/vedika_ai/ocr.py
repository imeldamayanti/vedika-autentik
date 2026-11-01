"""Small OCR boundary. Tesseract is the verified Phase 1 baseline."""

import re
import shutil
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pytesseract
from PIL import Image

from .errors import ServiceError


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float


class OcrEngine(Protocol):
    name: str

    def read(self, rgb: np.ndarray, *, page_segmentation: int = 6) -> OcrResult: ...


class TesseractOcr:
    name = "tesseract-5"

    @staticmethod
    def available() -> bool:
        return shutil.which("tesseract") is not None

    def read(self, rgb: np.ndarray, *, page_segmentation: int = 6) -> OcrResult:
        if not self.available():
            raise ServiceError(503, "ocr_tidak_siap", "Mesin OCR belum tersedia.")
        try:
            data = pytesseract.image_to_data(
                Image.fromarray(rgb),
                lang="eng",
                config=f"--psm {page_segmentation}",
                output_type=pytesseract.Output.DICT,
                timeout=5,
            )
        except (RuntimeError, pytesseract.TesseractError) as error:
            raise ServiceError(503, "ocr_gagal", "Mesin OCR gagal memproses dokumen.") from error
        words: list[str] = []
        confidences: list[float] = []
        for text, confidence in zip(data["text"], data["conf"], strict=True):
            cleaned = re.sub(r"\s+", " ", text).strip()
            try:
                score = float(confidence)
            except (TypeError, ValueError):
                continue
            if cleaned and score >= 0:
                words.append(cleaned)
                confidences.append(score / 100)
        average = sum(confidences) / len(confidences) if confidences else 0.0
        return OcrResult(text=" ".join(words), confidence=round(average, 3))


class EmptyOcr:
    """Test helper and explicit degraded mode; never selected in production."""

    name = "empty"

    def read(self, rgb: np.ndarray, *, page_segmentation: int = 6) -> OcrResult:
        del rgb, page_segmentation
        return OcrResult(text="", confidence=0.0)
