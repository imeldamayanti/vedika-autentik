"""Pengaturan dan konstanta API. Rahasia dibaca dari backend/.env (tidak di-commit)."""
import os
from datetime import timedelta, timezone
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


def cors_origins() -> list[str]:
    """Origin FE yang boleh memanggil API langsung (dev). Produksi memakai rewrite Vercel, tanpa CORS."""
    mentah = os.environ.get("CORS_ORIGINS", "http://localhost:8899,http://127.0.0.1:8899")
    return [o.strip() for o in mentah.split(",") if o.strip()]


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "")


def mesin_url() -> str:
    return os.environ.get("MESIN_URL", "http://localhost:8001")


def kunci_mesin() -> str | None:
    return os.environ.get("KUNCI_MESIN") or None


def upload_dir() -> Path:
    return Path(os.environ.get("UPLOAD_DIR", AKAR / "backend" / "uploads"))


# ---- v3: konfirmasi suara (docs/api-contract-v3.md) ----

ZONA = timezone(timedelta(hours=7))  # WIB; waktu di kontrak selalu berzona +07:00
VERSI_ATURAN_V3 = "2026.10"
BULAN_BAWAAN = "2026-08"
MAKS_REKAMAN = 10 * 1024 * 1024
KUNCI_AMBIL_MENIT = 5  # kunci ambil agen lepas bila tidak ada laporan selama ini
BATAS_PANGGILAN_DETIK = 150  # R3.3: panggilan paling lama 2,5 menit
WAKTU_PEMBACA_DETIK = 30
BULAN_NAMA = {
    "01": "Januari", "02": "Februari", "03": "Maret", "04": "April", "05": "Mei", "06": "Juni",
    "07": "Juli", "08": "Agustus", "09": "September", "10": "Oktober", "11": "November", "12": "Desember",
}


def kunci_agen() -> str | None:
    return os.environ.get("AGEN_KEY") or None


def nomor_penguji() -> str:
    """Prototipe: semua panggilan dan WA menuju satu nomor penguji (R2.1), bukan nomor peserta."""
    return os.environ.get("NOMOR_PENGUJI", "0800-0000-0000")


def nomor_penelepon() -> str:
    return os.environ.get("NOMOR_PENELEPON", "0800-0000-0165")


def rekaman_dir() -> Path:
    return upload_dir() / "rekaman"
