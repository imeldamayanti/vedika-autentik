"""Pengaturan dan konstanta API. Rahasia dibaca dari backend/.env (tidak di-commit)."""
import os
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

AKAR = Path(__file__).resolve().parents[2]
load_dotenv(AKAR / "backend" / ".env")
# Di Vercel root proyek adalah backend/, jadi folder data uji disalin ke backend/ saat build (backend/vercel.json).
DATA_UJI = next(
    (p for p in (AKAR / "data-uji-konfirmasi", Path(__file__).resolve().parents[1] / "data-uji-konfirmasi")
     if (p / "tools" / "aturan.py").exists()),
    AKAR / "data-uji-konfirmasi",
)

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
    mentah = os.environ.get("CORS_ORIGINS", "http://localhost:8899,http://127.0.0.1:8899,http://localhost:8001")
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
KUNCI_MACET_MENIT = 5  # panggilan berjalan tanpa laporan selama ini dilepas sebagai satu percobaan gagal
STASIUN_AKTIF_DETIK = 30  # stasiun dianggap aktif bila detaknya lebih baru dari ini
BATAS_PANGGILAN_DETIK = 150  # R3.3: panggilan paling lama 2,5 menit
WAKTU_PEMBACA_DETIK = 30
# Jeda (detik) sebelum mengulang pembaca setelah galat penyedia (Gemini 503/429, batas waktu, tak terhubung).
# Gangguan Gemini biasanya hilang dalam hitungan detik; ulang langsung hanya menabrak dinding yang sama.
JEDA_ULANG_PEMBACA = (3, 10, 20, 40)
BULAN_NAMA = {
    "01": "Januari", "02": "Februari", "03": "Maret", "04": "April", "05": "Mei", "06": "Juni",
    "07": "Juli", "08": "Agustus", "09": "September", "10": "Oktober", "11": "November", "12": "Desember",
}


def kunci_agen() -> str | None:
    return os.environ.get("AGEN_KEY") or None


def nomor_penguji() -> str:
    """Prototipe: panggilan dan WA menuju nomor ini bila nomor penerima di data hanya placeholder 0800 (R2.1)."""
    return os.environ.get("NOMOR_PENGUJI", "0800-0000-0000")


def nomor_penelepon() -> str:
    return os.environ.get("NOMOR_PENELEPON", "0800-0000-0165")


def rekaman_dir() -> Path:
    return upload_dir() / "rekaman"


# ---- WhatsApp lewat Meta Cloud API (app/wa.py) ----

def meta_wa_mode() -> str:
    """log (tanpa jaringan), teks, atau template. Tanpa token atau phone id selalu log."""
    mode = os.environ.get("META_WA_MODE", "log").strip().lower()
    if not meta_wa_token() or not meta_wa_phone_id() or mode not in ("teks", "template"):
        return "log"
    return mode


def meta_wa_token() -> str | None:
    return os.environ.get("META_WA_TOKEN") or None


def meta_wa_phone_id() -> str | None:
    return os.environ.get("META_WA_PHONE_ID") or None


def meta_wa_api_version() -> str | None:
    return os.environ.get("META_WA_API_VERSION") or None


def meta_wa_template(jenis: str) -> str | None:
    return os.environ.get(f"META_WA_TEMPLATE_{jenis.upper()}") or None


def meta_wa_template_bahasa() -> str:
    return os.environ.get("META_WA_TEMPLATE_BAHASA") or "id"
