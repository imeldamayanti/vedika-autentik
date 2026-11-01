"""Worker antrean: ambil job, panggil mesin AI (Kontrak B), simpan hasil, hitung label.

Jalankan sebagai proses terpisah dengan `python -m app.worker`, atau panggil proses_satu langsung.

Ketahanan: semua galat saat memproses berujung berkas `gagal` berlabel Perlu dicek (gagal aman),
tidak pernah crash dan tidak pernah Lolos. Job yang nyangkut `jalan` lebih dari BATAS_NYANGKUT
diambil ulang, maksimal MAKS_PERCOBAAN kali.
"""
import time

from . import klaim as data_klaim
from . import repo
from .config import VERSI_ATURAN
from .label import ALASAN_SARAN, hitung_label
from .mesin import KlienMesin, MesinGalat
from .tampilan import ringkasan

BATAS_NYANGKUT = "5 minutes"
MAKS_PERCOBAAN = 3
KALIMAT_GAGAL = "Berkas tidak bisa diproses oleh mesin pemeriksa. Ditandai Perlu dicek."
ALASAN_GAGAL = "Berkas tidak bisa diproses, sehingga tidak bisa dinyatakan Lolos."


def _gabungkan_hasil_banding(temuan: list[dict], banding: dict, pasangan_id: str) -> None:
    """Ubah bukti pasangan dari mesin menjadi temuan yang disimpan API."""
    if not banding.get("sama"):
        return

    region_a = banding.get("region_a") or []
    temuan.append(
        {
            "cek": "berkas_kembar",
            "kekuatan": "kuat",
            "kalimat": banding["kalimat"],
            "region": region_a[0] if region_a else None,
            "skor": banding["kemiripan"],
            "pasangan": pasangan_id,
        }
    )

    tempelan = banding.get("tempelan") or []
    if tempelan and not any(item["cek"] == "tempelan" for item in temuan):
        area = [item["region_a"] for item in tempelan]
        temuan.append(
            {
                "cek": "tempelan",
                "kekuatan": "kuat",
                "kalimat": (
                    f"{len(area)} bagian memiliki pola piksel yang sama dengan "
                    "berkas pembanding."
                ),
                "region": area[0],
                "area": area,
                "skor": max(item["kemiripan"] for item in tempelan),
                "pasangan": pasangan_id,
            }
        )

    for item in temuan:
        if item["cek"] == "tempelan":
            item["pasangan"] = pasangan_id


def _ambil_job(conn):
    job = conn.execute(
        "select id, berkas_id from job"
        " where status = 'menunggu' or (status = 'jalan' and percobaan < %s and diambil < now() - %s::interval)"
        " order by dibuat, id for update skip locked limit 1",
        (MAKS_PERCOBAAN, BATAS_NYANGKUT),
    ).fetchone()
    if job:
        conn.execute(
            "update job set status = 'jalan', percobaan = percobaan + 1, diambil = now() where id = %s", (job["id"],)
        )
    conn.commit()
    return job


def _tutup_job(conn, job_id, status, galat=None):
    conn.execute("update job set status = %s, galat = %s, selesai = now() where id = %s", (status, galat, job_id))


def _gagal(conn, berkas_id, job_id, kode):
    repo.simpan_gagal(conn, berkas_id, galat=kode, kalimat=KALIMAT_GAGAL, alasan=ALASAN_GAGAL, versi_aturan=VERSI_ATURAN)
    _tutup_job(conn, job_id, "gagal", kode)


def _proses(conn, job, mesin: KlienMesin, penyimpanan):
    berkas = repo.ambil_berkas(conn, job["berkas_id"])
    isi = penyimpanan.baca(berkas["path_storage"])
    klaim_awal = data_klaim.cari(berkas["sep"])  # SEP dari unggahan, bila ada
    konteks_mesin = dict(klaim_awal or {})
    konteks_mesin["kode_faskes"] = berkas["kode_faskes"]
    try:
        hasil = mesin.analisis(berkas["nama_file"], isi, konteks_mesin)
    except MesinGalat as e:
        _gagal(conn, berkas["id"], job["id"], e.kode)
        return

    # Berkas kembar bukan sinyal dari satu berkas. Dibuktikan API: sidik jari di arsip, lalu perbandingan.
    temuan = [dict(t) for t in hasil["temuan"] if t["cek"] != "berkas_kembar"]
    kembar = None
    if hasil["kualitas_scan"]["status"] == "baik":
        kembar = repo.cari_kembar(
            conn,
            (hasil.get("sidik_jari") or {}).get("halaman"),
            berkas["id"],
        )
    if kembar:
        try:
            banding = mesin.bandingkan(
                berkas["nama_file"], isi, kembar["nama_file"], penyimpanan.baca(kembar["path_storage"])
            )
        except MesinGalat:
            banding = None
        if banding and banding["sama"]:
            _gabungkan_hasil_banding(temuan, banding, kembar["id"])

    label = hitung_label({"kualitas_scan": hasil["kualitas_scan"], "temuan": temuan})
    repo.simpan_hasil(
        conn, berkas["id"],
        klaim=data_klaim.cari((hasil.get("isi_lembar") or {}).get("no_sep")) or klaim_awal,
        hasil=hasil, temuan=temuan, label=label, alasan=ALASAN_SARAN[label],
        ringkasan=ringkasan(temuan, hasil["kualitas_scan"], label), versi_aturan=VERSI_ATURAN,
    )
    _tutup_job(conn, job["id"], "selesai")


def proses_satu(conn, mesin: KlienMesin, penyimpanan) -> bool:
    """Memproses satu job. True bila ada job yang diproses (berhasil atau gagal aman)."""
    job = _ambil_job(conn)
    if job is None:
        return False
    try:
        with conn.transaction():  # savepoint: hasil setengah jadi dibuang bila ada galat
            _proses(conn, job, mesin, penyimpanan)
    except Exception as e:  # noqa: BLE001 - apa pun yang salah harus berujung gagal aman, bukan macet
        with conn.transaction():
            _gagal(conn, job["berkas_id"], job["id"], getattr(e, "kode", None) or "galat_internal")
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
        try:
            with psycopg.connect(config.database_url(), row_factory=dict_row, prepare_threshold=None) as conn:
                while proses_satu(conn, mesin, simpan):
                    pass
        except psycopg.Error as e:
            print(f"worker: koneksi database bermasalah ({type(e).__name__}), coba lagi", flush=True)
        time.sleep(jeda)


if __name__ == "__main__":
    jalankan()
