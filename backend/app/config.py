"""Pengaturan dan konstanta API. Rahasia dibaca dari backend/.env (tidak di-commit)."""
import os
from pathlib import Path

from dotenv import load_dotenv

AKAR = Path(__file__).resolve().parents[2]
load_dotenv(AKAR / "backend" / ".env")

VERSI_ATURAN = "2026.09"
MAKS_UKURAN = 10 * 1024 * 1024
EKSTENSI = {".pdf", ".jpg", ".jpeg", ".png"}
VERIFIKATOR = "R. Santoso"

# Rumah sakit yang dikenal. Konteks demo, bukan verifikasi asal dokumen.
FASKES = {
    "0901R014": "RS Melati Sehat",
    "0901R027": "RS Cipta Medika",
    "0901R041": "RSU Bakti Mulia",
    "0901R008": "RS Harapan Bunda",
}


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "")


def mesin_url() -> str:
    return os.environ.get("MESIN_URL", "http://localhost:8001")


def kunci_mesin() -> str | None:
    return os.environ.get("KUNCI_MESIN") or None


def upload_dir() -> Path:
    return Path(os.environ.get("UPLOAD_DIR", AKAR / "backend" / "uploads"))
