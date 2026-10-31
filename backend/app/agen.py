"""Logika agen suara (Kontrak B1) dan pembacaan hasil (Kontrak B2). Aturan percobaan, jeda, dan label ada di sini,
bukan di agen: agen hanya menarik tugas dan melapor (docs/api-contract-v3.md)."""
import logging
from datetime import timedelta
from pathlib import Path

from . import aturan_v3 as at
from . import config, jam, repo_v3, tampilan_v3
from .galat import Galat
from .mesin import MesinGalat

log = logging.getLogger("vedika.agen")

LAPORAN = ("wa_terkirim", "menelepon", "tersambung", "merekam", "tidak_diangkat", "chat_cadangan_terkirim")
BERLANGSUNG = ("tersambung", "merekam")
RETENSI_SESUAI = timedelta(days=30)
EKSTENSI_AUDIO = {".webm", ".mp3", ".wav", ".ogg", ".m4a"}
TANGKAPAN = ("penerima", "hubungan", "hadir", "jumlah_min", "jumlah_maks", "keyakinan", "membantah_tanggal_libur", "tanda_bahaya")
TANDA_BAHAYA = {"tanda_tangan_tanpa_layanan", "diminta_membayar", "layanan_berbeda"}
PESAN_PEMBACA_GAGAL = "Jawaban belum bisa dibaca otomatis. Tidak dihitung."


def _tidak_ada() -> Galat:
    return Galat(404, "panggilan_tidak_ada", "Panggilan tidak ditemukan.")


def _nomor_percobaan(p: dict) -> int:
    """Percobaan yang sedang dijalankan: DB menaikkan nilainya saat agen melapor 'menelepon'."""
    return p["percobaan"] + 1 if p["status"] in ("antre", "wa_terkirim") else p["percobaan"]


# ---- POST /agen/ambil ----

def tanggal_libur_skrip(conn, p: dict) -> list[str]:
    return [f"{t.day} {config.BULAN_NAMA[f'{t.month:02d}']}" for t in repo_v3.tanggal_libur(conn, p["id_peserta"], p["id_rs"], p["bulan_layanan"])]


def susun_tugas(conn, p: dict, pengaturan: dict) -> dict:
    nomor = config.nomor_penguji()
    percobaan = p["percobaan"] + 1
    sapaan_pasien = at.sapaan(p["jenis_kelamin"])
    teks = at.pesan_pemberitahuan(
        nama_penerima=p["nama_penerima"], nama_pasien=p["pasien"], nama_rs=p["nama_rs"], bulan=p["bulan_layanan"],
        jeda_menit=pengaturan["jeda_wa_menit"], nomor_penelepon=config.nomor_penelepon(),
    )
    return {
        "id": p["id"], "percobaan": percobaan, "no_tujuan": nomor,
        "skrip": {
            "nama_penerima": p["nama_penerima"],
            "sapaan_penerima": sapaan_pasien if p["penerima"] == "peserta" else "Bapak/Ibu",
            "hubungan": at.hubungan_penerima(p), "nama_pasien": p["pasien"], "sapaan_pasien": sapaan_pasien,
            "nama_rs": p["nama_rs"], "bulan": at.nama_bulan(p["bulan_layanan"]),
            "tanggal_libur": tanggal_libur_skrip(conn, p),
        },
        "wa": {"lewati": percobaan >= 2, "teks": teks, "tautan": at.tautan_wa(nomor, teks)},
        "jeda_wa_menit": pengaturan["jeda_wa_menit"], "batas_detik": config.BATAS_PANGGILAN_DETIK,
    }


def ambil_tugas(conn) -> dict | None:
    """Tugas berikutnya untuk agen, atau None (HTTP 204). Aturan: satu panggilan aktif, jam kerja, mode otomatis
    (kecuali prioritas dari 'Telepon sekarang'), dan percobaan ke-2 menunggu coba_lagi_setelah."""
    sekarang = jam.sekarang()
    pengaturan = repo_v3.ambil_pengaturan(conn)
    batas_kunci = sekarang - timedelta(minutes=config.KUNCI_AMBIL_MENIT)
    if not tampilan_v3.dalam_jam(pengaturan, sekarang) or repo_v3.ada_panggilan_aktif(conn, batas_kunci):
        return None
    id_ = repo_v3.kunci_tugas(conn, sekarang, batas_kunci, pengaturan["mode_otomatis"] and not pengaturan["jeda"])
    if id_ is None:
        return None
    p = repo_v3.satu_baris(conn, id_)
    repo_v3.perbarui(conn, id_, {"no_tujuan": config.nomor_penguji(), "jeda_wa_menit": pengaturan["jeda_wa_menit"]})
    return susun_tugas(conn, p, pengaturan)


# ---- POST /panggilan/{id}/status ----

# dari status (dan percobaan yang sedang dijalankan) -> laporan yang sah
def laporan_sah(p: dict) -> tuple[str, ...]:
    if p["status"] == "antre":
        return ("wa_terkirim",) if p["percobaan"] == 0 else ("menelepon",)
    return {
        "wa_terkirim": ("menelepon",), "menelepon": ("tersambung", "tidak_diangkat"), "tersambung": ("merekam",),
        "tidak_terhubung": ("chat_cadangan_terkirim",),
    }.get(p["status"], ())


def balasan_status(p: dict, status, percobaan, coba_lagi=None, chat=None) -> dict:
    return {"status": status, "percobaan": percobaan, "coba_lagi_setelah": jam.iso(coba_lagi), "chat_cadangan": chat}


def lapor_status(conn, id_: str, laporan: str, waktu, catatan: str | None) -> dict:
    if laporan not in LAPORAN:
        raise Galat(422, "laporan_tidak_dikenal", "Laporan harus salah satu dari: " + ", ".join(LAPORAN) + ".")
    p = repo_v3.satu_baris(conn, id_)
    if p is None:
        raise _tidak_ada()
    if laporan not in laporan_sah(p):
        raise Galat(409, "urutan_salah", f"Laporan {laporan} tidak sah untuk panggilan berstatus {p['status']}.")
    sekarang = jam.sekarang()
    if waktu is not None and waktu.tzinfo is None:
        waktu = waktu.replace(tzinfo=config.ZONA)
    waktu = waktu or sekarang
    ke = _nomor_percobaan(p)

    if laporan == "wa_terkirim":
        repo_v3.perbarui(conn, id_, {"status": "wa_terkirim", "waktu_wa": waktu})
        repo_v3.tambah_log(conn, id_, "wa_terkirim", waktu, ke, catatan)
        return balasan_status(p, "wa_terkirim", p["percobaan"])

    if laporan == "menelepon":
        if p["status"] == "wa_terkirim":  # percobaan ke-1: tunggu jeda sejak pesan WA (R2.2)
            if sekarang < p["waktu_wa"] + timedelta(minutes=p["jeda_wa_menit"]):
                raise Galat(409, "jeda_belum_lewat", f"Panggilan baru boleh dimulai {p['jeda_wa_menit']} menit setelah pesan WA.")
        repo_v3.perbarui(conn, id_, {"status": "menelepon", "percobaan": ke})
        repo_v3.tambah_log(conn, id_, "menelepon", waktu, ke, catatan)
        return balasan_status(p, "menelepon", ke)

    if laporan == "tersambung":
        repo_v3.perbarui(conn, id_, {"status": "tersambung", "waktu_mulai": waktu})
        repo_v3.tambah_log(conn, id_, "tersambung", waktu, ke, catatan)
        return balasan_status(p, "tersambung", ke)

    if laporan == "merekam":
        repo_v3.perbarui(conn, id_, {"status": "merekam"})
        repo_v3.tambah_log(conn, id_, "merekam", waktu, ke, catatan)
        return balasan_status(p, "merekam", ke)

    if laporan == "tidak_diangkat":
        repo_v3.tambah_log(conn, id_, "menelepon", waktu, ke, "tidak_diangkat")
        if ke < 2:  # percobaan ke-1: kembali antre, coba lagi setelah jeda (R3.5)
            coba_lagi = sekarang + timedelta(minutes=repo_v3.ambil_pengaturan(conn)["jeda_percobaan_menit"])
            repo_v3.perbarui(conn, id_, {"status": "antre", "coba_lagi_setelah": coba_lagi, "diambil_pada": None})
            return balasan_status(p, "antre", ke, coba_lagi)
        jawaban = dict(at.JAWABAN_TIDAK_TERHUBUNG)
        label, alasan = at.label_jawaban(jawaban, p["sesi_ditagih"])
        repo_v3.perbarui(conn, id_, {
            "status": "tidak_terhubung", "label": label, "alasan": alasan, "jawaban": jawaban, "waktu_selesai": sekarang,
            "diambil_pada": None, "coba_lagi_setelah": None,
        })
        chat = at.pesan_cadangan(nama_pasien=p["pasien"], nama_rs=p["nama_rs"], bulan=p["bulan_layanan"])
        return balasan_status(p, "tidak_terhubung", ke, chat={"teks": chat, "tautan": at.tautan_wa(config.nomor_penguji(), chat)})

    # chat_cadangan_terkirim
    repo_v3.perbarui(conn, id_, {"chat_cadangan_terkirim": True})
    repo_v3.tambah_log(conn, id_, "tidak_terhubung", waktu, ke, catatan or "chat_cadangan_terkirim")
    return balasan_status(p, "tidak_terhubung", ke)


# ---- POST /panggilan/{id}/transkrip ----

def tambah_transkrip(conn, id_: str, baris: list[dict], tangkapan: dict | None) -> None:
    p = repo_v3.satu_baris(conn, id_)
    if p is None:
        raise _tidak_ada()
    if p["status"] not in BERLANGSUNG:
        raise Galat(409, "bukan_berlangsung", "Transkrip hanya diterima selama panggilan tersambung.")
    repo_v3.tambah_transkrip(conn, id_, baris)
    if tangkapan is not None:  # tiap kiriman menggantikan yang sebelumnya; hanya untuk panel, bukan dasar label
        repo_v3.perbarui(conn, id_, {"tangkapan_sementara": {k: tangkapan[k] for k in TANGKAPAN if k in tangkapan}})


# ---- POST /panggilan/{id}/hasil ----

def simpan_hasil(conn, simpan, id_: str, transkrip: list[dict], durasi: int, rekaman: tuple[str, bytes] | None) -> None:
    """Langkah 1 (sinkron): simpan rekaman dan transkrip final, status membaca_jawaban. Sisanya di proses_hasil."""
    p = repo_v3.satu_baris(conn, id_)
    if p is None:
        raise _tidak_ada()
    if p["status"] not in BERLANGSUNG:
        raise Galat(409, "bukan_berlangsung", "Hasil hanya diterima untuk panggilan yang sedang berlangsung.")
    sekarang = jam.sekarang()
    kolom = {"status": "membaca_jawaban", "transkrip": transkrip, "durasi_detik": durasi, "waktu_selesai": sekarang}
    if rekaman:
        nama, isi = rekaman
        ekstensi = Path(nama).suffix.lower()
        kolom["rekaman_path"] = simpan.simpan_di(f"rekaman/{id_}{ekstensi if ekstensi in EKSTENSI_AUDIO else '.webm'}", isi)
    repo_v3.perbarui(conn, id_, kolom)
    repo_v3.tambah_log(conn, id_, "membaca_jawaban", sekarang, p["percobaan"])


def lolos_skema(j) -> str | None:
    """Pesan galat bila keluaran pembaca tidak sesuai skema README data uji, selain itu None."""
    if not isinstance(j, dict):
        return "Keluaran pembaca bukan objek JSON."
    if j.get("status_panggilan") not in ("terjawab", "tidak_terhubung", "menolak"):
        return "status_panggilan tidak valid."
    if j.get("penerima") not in ("peserta", "keluarga", None):
        return "penerima tidak valid."
    if j.get("keyakinan") not in ("tinggi", "rendah", None):
        return "keyakinan tidak valid."
    if j.get("hadir") not in (True, False, None):
        return "hadir tidak valid."
    for k in ("jumlah_min", "jumlah_maks"):
        v = j.get(k)
        if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v < 0):
            return f"{k} harus bilangan bulat tak negatif atau null."
    bahaya = j.get("tanda_bahaya", [])
    if not isinstance(bahaya, list) or not set(bahaya) <= TANDA_BAHAYA:
        return "tanda_bahaya berisi nilai di luar daftar."
    return None


def baca_dengan_ulang(mesin, permintaan: dict) -> tuple[dict | None, str | None]:
    """Panggil pembaca; gagal (502, 504, timeout, tak terhubung, JSON tak lolos skema) diulang 1 kali.
    422 transkrip_kosong tidak diulang. Mengembalikan (jawaban, None) atau (None, pesan galat)."""
    galat = None
    for _ in range(2):
        try:
            j = mesin.baca(permintaan, config.WAKTU_PEMBACA_DETIK)
        except MesinGalat as e:
            galat = f"{e.kode}: {e.pesan}"
            if e.kode == "transkrip_kosong":
                break
            continue
        masalah = lolos_skema(j)
        if masalah is None:
            return j, None
        galat = f"skema_tidak_valid: {masalah}"
    return None, galat


def proses_hasil(buka_conn, simpan, mesin, id_: str) -> None:
    """Latar belakang: panggil pembaca, hitung label dengan aturan.py, simpan, selesai. Tidak pernah berhenti di
    membaca_jawaban: kegagalan apa pun berakhir di label Tidak yakin (gagal aman, R4.3)."""
    with buka_conn() as conn:
        try:
            with conn.transaction():  # savepoint: gagal di tengah tidak meninggalkan setengah hasil
                _proses(conn, simpan, mesin, id_)
        except Exception as e:  # noqa: BLE001 - jaring pengaman terakhir supaya demo tidak macet
            log.exception("proses_hasil %s gagal", id_)
            with conn.transaction():
                _selesaikan(conn, simpan, id_, None, f"galat_internal: {type(e).__name__}")
        conn.commit()


def _proses(conn, simpan, mesin, id_: str) -> None:
    p = repo_v3.satu_baris(conn, id_)
    libur = [t.isoformat() for t in repo_v3.tanggal_libur(conn, p["id_peserta"], p["id_rs"], p["bulan_layanan"])]
    jawaban, galat = baca_dengan_ulang(mesin, {
        "id": id_, "transkrip": p["transkrip"] or [],
        "konteks": {"sesi_ditagih": p["sesi_ditagih"], "tanggal_libur": libur, "nama_pasien": p["pasien"], "bulan": p["bulan_layanan"]},
    })
    _selesaikan(conn, simpan, id_, jawaban, galat)


def _selesaikan(conn, simpan, id_: str, jawaban: dict | None, galat: str | None) -> None:
    p = repo_v3.satu_baris(conn, id_)
    if jawaban is None:
        jawaban = {**at.lengkapi_jawaban({"status_panggilan": "terjawab", "ringkasan": PESAN_PEMBACA_GAGAL}), "kutipan_kunci": ""}
        label, _ = at.label_jawaban(jawaban, p["sesi_ditagih"])
        alasan = PESAN_PEMBACA_GAGAL
    else:
        jawaban = at.lengkapi_jawaban(jawaban)
        label, alasan = at.label_jawaban(jawaban, p["sesi_ditagih"])
    kolom = {
        "status": "selesai", "jawaban": jawaban, "label": label, "alasan": alasan, "galat_pembaca": galat,
        "tangkapan_sementara": None,
        # R5.5: Sesuai disimpan 30 hari; Tidak sesuai sampai klarifikasi selesai (null); lainnya tanpa rekaman dan transkrip.
        "hapus_pada": p["waktu_selesai"] + RETENSI_SESUAI if label == "Sesuai" and p["waktu_selesai"] else None,
    }
    if label not in ("Sesuai", "Tidak sesuai"):
        if p["rekaman_path"]:
            simpan.hapus(p["rekaman_path"])
        kolom.update({"rekaman_path": None, "transkrip": None})
    repo_v3.perbarui(conn, id_, kolom)
    repo_v3.tambah_log(conn, id_, "selesai", jam.sekarang(), p["percobaan"])
