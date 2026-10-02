"""Worker antrean: ambil job, panggil mesin AI (Kontrak B), simpan hasil, hitung label.

Jalankan sebagai proses terpisah dengan `python -m app.worker`, atau panggil proses_satu langsung.
"""
import time

from . import klaim as data_klaim
from . import repo
from .config import VERSI_ATURAN
from .label import ALASAN_SARAN, hitung_label
from .mesin import KlienMesin, MesinGalat
from .tampilan import ringkasan


def _ambil_job(conn):
    job = conn.execute(
        "select id, berkas_id from job where status = 'menunggu' order by dibuat, id for update skip locked limit 1"
    ).fetchone()
    if job:
        conn.execute(
            "update job set status = 'jalan', percobaan = percobaan + 1, diambil = now() where id = %s", (job["id"],)
        )
    conn.commit()
    return job


def _tutup_job(conn, job_id, status, galat=None):
    conn.execute("update job set status = %s, galat = %s, selesai = now() where id = %s", (status, galat, job_id))


def proses_satu(conn, mesin: KlienMesin, penyimpanan) -> bool:
    """Memproses satu job. True bila ada job yang diproses."""
    job = _ambil_job(conn)
    if job is None:
        return False
    berkas = repo.ambil_berkas(conn, job["berkas_id"])
    isi = penyimpanan.baca(berkas["path_storage"])
    klaim_awal = data_klaim.cari(berkas["sep"])  # SEP dari unggahan, bila ada
    try:
        hasil = mesin.analisis(berkas["nama_file"], isi, klaim_awal)
    except MesinGalat as e:
        # Gagal aman: berkas yang tidak bisa diproses menjadi Perlu dicek, tidak pernah Lolos.
        repo.simpan_gagal(
            conn, berkas["id"], galat=e.kode,
            kalimat="Berkas tidak bisa diproses oleh mesin pemeriksa. Ditandai Perlu dicek.",
            alasan="Berkas tidak bisa diproses, sehingga tidak bisa dinyatakan Lolos.", versi_aturan=VERSI_ATURAN,
        )
        _tutup_job(conn, job["id"], "gagal", e.kode)
        conn.commit()
        return True

    # Berkas kembar bukan sinyal dari satu berkas. Dibuktikan API: sidik jari di arsip, lalu perbandingan.
    temuan = [dict(t) for t in hasil["temuan"] if t["cek"] != "berkas_kembar"]
    kembar = repo.cari_kembar(conn, (hasil.get("sidik_jari") or {}).get("halaman"), berkas["id"])
    if kembar:
        try:
            banding = mesin.bandingkan(
                berkas["nama_file"], isi, kembar["nama_file"], penyimpanan.baca(kembar["path_storage"])
            )
        except MesinGalat:
            banding = None
        if banding and banding["sama"]:
            region_a = banding.get("region_a") or []
            temuan.append({
                "cek": "berkas_kembar", "kekuatan": "kuat", "kalimat": banding["kalimat"],
                "region": region_a[0] if region_a else None, "skor": banding["kemiripan"], "pasangan": kembar["id"],
            })
            for t in temuan:
                if t["cek"] == "tempelan":
                    t["pasangan"] = kembar["id"]

    label = hitung_label({"kualitas_scan": hasil["kualitas_scan"], "temuan": temuan})
    repo.simpan_hasil(
        conn, berkas["id"],
        klaim=data_klaim.cari((hasil.get("isi_lembar") or {}).get("no_sep")) or klaim_awal,
        hasil=hasil, temuan=temuan, label=label, alasan=ALASAN_SARAN[label],
        ringkasan=ringkasan(temuan, hasil["kualitas_scan"], label), versi_aturan=VERSI_ATURAN,
    )
    _tutup_job(conn, job["id"], "selesai")
    conn.commit()
    return True


def jalankan(jeda: float = 1.0):
    """Loop produksi: ambil job terus-menerus."""
    import httpx
    import psycopg
    from psycopg.rows import dict_row

    from . import config
    from .penyimpanan import Penyimpanan

    mesin = KlienMesin(httpx.Client(base_url=config.mesin_url(), timeout=60), config.kunci_mesin())
    simpan = Penyimpanan(config.upload_dir())
    while True:
        with psycopg.connect(config.database_url(), row_factory=dict_row, prepare_threshold=None) as conn:
            while proses_satu(conn, mesin, simpan):
                pass
        time.sleep(jeda)


if __name__ == "__main__":
    jalankan()
