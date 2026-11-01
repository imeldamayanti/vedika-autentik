"""Kontrak A v3: FE ↔ API (docs/api-contract-v3.md). Tanpa login di prototipe (produksi: login Supabase)."""
import re

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import aturan_v3 as at
from . import config, jam, repo_v3, tampilan_v3
from .deps import get_conn, get_penyimpanan
from .galat import Galat

router = APIRouter(prefix="/api/v1")
POLA_BULAN = r"^\d{4}-(0[1-9]|1[0-2])$"


@router.get("/antrean")
def antrean(
    bulan: str = Query(config.BULAN_BAWAAN, pattern=POLA_BULAN),
    id_rs: str | None = None,
    status: str | None = None,
    conn=Depends(get_conn),
):
    return tampilan_v3.antrean(conn, bulan, id_rs, status)


@router.get("/panggilan/{id_}")
def detail_panggilan(id_: str, conn=Depends(get_conn)):
    d = tampilan_v3.detail(conn, id_)
    if d is None:
        raise Galat(404, "panggilan_tidak_ada", "Panggilan tidak ditemukan.")
    return d


@router.get("/ringkasan-rs")
def ringkasan_rs(bulan: str = Query(config.BULAN_BAWAAN, pattern=POLA_BULAN), conn=Depends(get_conn)):
    return tampilan_v3.ringkasan_rs(conn, bulan)


@router.get("/keputusan")
def riwayat_keputusan(conn=Depends(get_conn)):
    return tampilan_v3.daftar_keputusan(conn)


@router.get("/pengaturan")
def pengaturan(conn=Depends(get_conn)):
    return tampilan_v3.pengaturan_publik(repo_v3.ambil_pengaturan(conn))


# ---- tulis (D-03) ----

TIPE_AUDIO = {".webm": "audio/webm", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4"}
POLA_JAM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _tidak_valid(pesan: str) -> Galat:
    return Galat(422, "pengaturan_tidak_valid", pesan)


def _periksa_pengaturan(body: dict, sekarang: dict) -> dict:
    """Terapkan perubahan sebagian dan kembalikan hanya kunci yang berubah. Field tak dikenal diabaikan."""
    baru = {k: body[k] for k in at.BAWAAN_PENGATURAN if k in body}
    for k in ("mode_otomatis", "jeda"):
        if k in baru and not isinstance(baru[k], bool):
            raise _tidak_valid(f"{k} harus true atau false.")
    for k in ("jam_mulai", "jam_selesai"):
        if k in baru and not (isinstance(baru[k], str) and POLA_JAM.match(baru[k])):
            raise _tidak_valid(f"{k} harus berformat HH:MM.")
    for k in ("jeda_wa_menit", "jeda_percobaan_menit"):
        if k in baru and (isinstance(baru[k], bool) or not isinstance(baru[k], int) or not 0 <= baru[k] <= 1440):
            raise _tidak_valid(f"{k} harus bilangan bulat 0 sampai 1440.")
    if "mode_otomatis" in baru and "jeda" not in baru:
        baru["jeda"] = False  # mode diubah ke nilai apa pun: Jeda ikut mati
    akhir = {**sekarang, **baru}
    if akhir["jeda"] and not akhir["mode_otomatis"]:
        raise _tidak_valid("Jeda hanya sah bila mode otomatis aktif.")
    if akhir["jam_mulai"] >= akhir["jam_selesai"]:
        raise _tidak_valid("jam_mulai harus lebih awal dari jam_selesai.")
    return baru


@router.put("/pengaturan")
def ubah_pengaturan(body: dict = Body(...), conn=Depends(get_conn)):
    sekarang = repo_v3.ambil_pengaturan(conn)
    baru = _periksa_pengaturan(body, sekarang)
    repo_v3.simpan_pengaturan(conn, baru)
    conn.commit()
    return tampilan_v3.pengaturan_publik({**sekarang, **baru})


@router.post("/panggilan/{id_}/mulai")
def telepon_sekarang(id_: str, conn=Depends(get_conn)):
    r = repo_v3.satu_baris(conn, id_)
    if r is None:
        raise Galat(404, "panggilan_tidak_ada", "Panggilan tidak ditemukan.")
    if r["status"] != "antre":
        raise Galat(409, "bukan_antre", "Hanya panggilan berstatus antre yang bisa ditelepon sekarang.")
    repo_v3.tandai_prioritas(conn, id_)
    conn.commit()
    return tampilan_v3.baris_antre({**r, "prioritas": True})


class KeputusanBaru(BaseModel):
    ikut_saran: bool
    tindakan: str | None = None
    alasan: str | None = None


@router.post("/panggilan/{id_}/keputusan", status_code=201)
def putuskan(id_: str, body: KeputusanBaru, conn=Depends(get_conn)):
    r = repo_v3.satu_baris(conn, id_)
    if r is None:
        raise Galat(404, "panggilan_tidak_ada", "Panggilan tidak ditemukan.")
    label = tampilan_v3.label_api(r)
    if label is None:
        raise Galat(409, "belum_selesai", "Panggilan belum selesai, belum bisa diputuskan.")
    saran = at.saran(label)
    alasan = (body.alasan or "").strip() or None
    if body.ikut_saran:
        tindakan = saran
    else:
        tindakan = body.tindakan
        if tindakan not in at.TINDAKAN_PILIHAN:
            raise Galat(422, "tindakan_tidak_dikenal", "Tindakan harus salah satu dari: " + ", ".join(at.TINDAKAN_PILIHAN) + ".")
        if tindakan == saran:
            raise Galat(422, "tindakan_sama_saran", "Tindakan sama dengan saran; pilih Ikuti saran.")
        if alasan is None:
            raise Galat(422, "alasan_wajib", "Alasan wajib diisi bila tidak mengikuti saran sistem.")
    k = repo_v3.simpan_keputusan(conn, id_, config.VERIFIKATOR, at.TINDAKAN_DB[tindakan], body.ikut_saran, alasan, jam.sekarang())
    conn.commit()
    return tampilan_v3.objek_keputusan(k)


@router.get("/panggilan/{id_}/rekaman")
def rekaman(id_: str, conn=Depends(get_conn), simpan=Depends(get_penyimpanan)):
    r = repo_v3.satu_baris(conn, id_)
    if r is None:
        raise Galat(404, "panggilan_tidak_ada", "Panggilan tidak ditemukan.")
    jalur = simpan.jalur(r["rekaman_path"]) if tampilan_v3.rekaman_tersedia(r, jam.sekarang()) else None
    if jalur is None:
        raise Galat(404, "rekaman_tidak_ada", "Rekaman tidak tersedia.")
    # FileResponse melayani header Range, jadi pemutar audio di browser bisa melompat.
    return FileResponse(jalur, media_type=TIPE_AUDIO.get(jalur.suffix.lower(), "application/octet-stream"))


@router.post("/demo/reset")
def reset_demo(conn=Depends(get_conn), simpan=Depends(get_penyimpanan)):
    """Kembalikan panggilan, log, keputusan, dan rekaman ke keadaan awal demo. Data master tidak disentuh."""
    from scripts import seed_v3

    jalur = repo_v3.jalur_rekaman(conn)
    seed_v3.reset_panggilan(conn, seed_v3.muat_data())
    conn.commit()
    for rel in jalur:  # berkas dihapus setelah DB berhasil di-commit
        simpan.hapus(rel)
    return {"ok": True}
