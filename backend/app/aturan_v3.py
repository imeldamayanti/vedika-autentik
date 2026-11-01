"""Aturan v3: label, status RS, peta enum, dan teks WhatsApp (Lampiran B).

Label dan status RS dihitung oleh data-uji-konfirmasi/tools/aturan.py. Berkas itu dimuat apa adanya
di sini, tidak ditulis ulang, supaya aturan hanya punya satu sumber.
"""
import importlib.util
from functools import lru_cache
from urllib.parse import quote

from .config import AKAR, BULAN_NAMA

STATUS_BERJALAN = ("wa_terkirim", "menelepon", "tersambung", "merekam", "membaca_jawaban")
STATUS_SELESAI = ("selesai", "tidak_terhubung")
STATUS_PANGGILAN = ("antre",) + STATUS_BERJALAN + STATUS_SELESAI
BAWAAN_PENGATURAN = {
    "mode_otomatis": False, "jeda": False, "jam_mulai": "09:00", "jam_selesai": "17:00",
    "jeda_wa_menit": 1, "jeda_percobaan_menit": 2,
}

LABEL_API = {
    "Sesuai": "sesuai", "Tidak sesuai": "tidak_sesuai", "Tidak yakin": "tidak_yakin",
    "Tidak terhubung": "tidak_terhubung", "Menolak": "menolak",
}
LABEL_DB = {v: k for k, v in LABEL_API.items()}
TINDAKAN_API = {"tutup_kasus": "tutup", "minta_klarifikasi_rs": "klarifikasi", "teruskan_pk_jkn": "teruskan", "pantau": "pantau"}
TINDAKAN_DB = {v: k for k, v in TINDAKAN_API.items()}
TINDAKAN_PILIHAN = ("tutup", "klarifikasi", "teruskan")
SARAN_LABEL = {
    "sesuai": "tutup", "tidak_sesuai": "klarifikasi", "tidak_yakin": "pantau",
    "tidak_terhubung": "pantau", "menolak": "pantau",
}
KUNCI_JAWABAN = (
    "status_panggilan", "penerima", "hubungan", "hadir", "jumlah_min", "jumlah_maks", "keyakinan",
    "tanda_bahaya", "membantah_tanggal_libur", "kutipan_kunci", "ringkasan",
)
JAWABAN_TIDAK_TERHUBUNG = {
    "status_panggilan": "tidak_terhubung", "penerima": None, "hubungan": None, "hadir": None,
    "jumlah_min": None, "jumlah_maks": None, "keyakinan": None, "tanda_bahaya": [],
    "membantah_tanggal_libur": None, "kutipan_kunci": "", "ringkasan": "Panggilan tidak diangkat 2 kali.",
}
ATURAN_RS = "Perlu klarifikasi RS jika tidak sesuai >= 3 DAN rasio tidak sesuai/terjawab >= 10%"


@lru_cache
def aturan():
    spec = importlib.util.spec_from_file_location("aturan", AKAR / "data-uji-konfirmasi" / "tools" / "aturan.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def label_jawaban(jawaban: dict, sesi_ditagih: int) -> tuple[str, str]:
    return aturan().label_jawaban(jawaban, sesi_ditagih)


def ringkasan_rs(hasil: list[dict]) -> dict:
    """hasil: [{id_rs, label}] dengan label teks aturan.py ('Tidak sesuai', ...)."""
    return aturan().ringkasan_rs(hasil)


def lengkapi_jawaban(jawaban: dict | None) -> dict | None:
    """Key skema pembaca yang tidak ada di baris lama (mis. riwayat tanpa membantah_tanggal_libur) diisi null."""
    if jawaban is None:
        return None
    return {**{k: ([] if k == "tanda_bahaya" else None) for k in KUNCI_JAWABAN}, **jawaban}


def selisih(sesi_ditagih: int, jawaban: dict | None) -> int | None:
    jmax = (jawaban or {}).get("jumlah_maks")
    return None if jmax is None else max(0, sesi_ditagih - jmax)


def saran(label_api: str | None) -> str | None:
    return SARAN_LABEL.get(label_api) if label_api else None


def nama_bulan(bulan: str) -> str:
    return BULAN_NAMA[bulan[5:7]]


def hubungan_penerima(p: dict) -> str | None:
    return "peserta" if p["penerima"] == "peserta" else p["hubungan"]


def sapaan(jenis_kelamin: str | None) -> str:
    return {"L": "Bapak", "P": "Ibu"}.get(jenis_kelamin or "", "Bapak/Ibu")


def pesan_pemberitahuan(*, nama_penerima, nama_pasien, nama_rs, bulan, jeda_menit, nomor_penelepon) -> str:
    """Lampiran B persis (R2.3). Tanpa tautan di dalam teks."""
    return (
        f"Halo {nama_penerima}. Ini BPJS Kesehatan. Dalam {jeda_menit} menit kami akan menelepon dari nomor "
        f"{nomor_penelepon} untuk konfirmasi singkat layanan fisioterapi {nama_pasien} di {nama_rs} bulan "
        f"{nama_bulan(bulan)}. Ini bukan tagihan. Kami tidak akan meminta data pribadi, kode OTP, atau pembayaran. "
        "Untuk memastikan pesan ini, hubungi Care Center 165."
    )


def pesan_cadangan(*, nama_pasien, nama_rs, bulan) -> str:
    return (
        f"Kami belum berhasil menelepon. Kira-kira berapa kali {nama_pasien} menjalani fisioterapi di {nama_rs} "
        f"bulan {nama_bulan(bulan)}? Balas dengan angka: 1) 1–2 kali  2) 3–4 kali  3) 5–8 kali  4) lebih dari 8 kali  "
        "5) tidak ingat  6) tidak pernah terapi di sana."
    )


def tautan_wa(nomor: str, teks: str) -> str:
    """wa.me butuh nomor internasional tanpa tanda: 08xx → 628xx."""
    digit = "".join(c for c in nomor if c.isdigit())
    if digit.startswith("0"):
        digit = "62" + digit[1:]
    return f"https://wa.me/{digit}?text={quote(teks, safe='')}"
