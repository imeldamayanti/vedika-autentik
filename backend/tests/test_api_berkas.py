"""Uji Kontrak A (FE <-> API): unggah, proses, detail, antrean, keputusan."""
from app.penyimpanan import Penyimpanan
from app.worker import proses_satu


def proses_semua(conn, mesin, tmp_path):
    n = 0
    while proses_satu(conn, mesin, Penyimpanan(tmp_path)):
        n += 1
    return n


def unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, nama, **kw):
    r = unggah(nama, **kw)
    assert r.status_code == 202, r.text
    id_ = r.json()["id"]
    proses_semua(conn, mesin, tmp_path)
    return id_, klien.get(f"/api/v1/berkas/{id_}").json()


# ---------- unggah ----------

def test_unggah_format_tidak_didukung(unggah):
    r = unggah("catatan.txt", tipe="text/plain")
    assert r.status_code == 400
    assert r.json()["galat"]["kode"] == "format_tidak_didukung"


def test_unggah_faskes_tidak_dikenal(unggah):
    r = unggah("VA-ASL-01.pdf", kode_faskes="9999X999")
    assert r.status_code == 422
    assert r.json()["galat"]["kode"] == "faskes_tidak_dikenal"


def test_unggah_terlalu_besar(unggah):
    r = unggah("VA-ASL-01.pdf", isi=b"x" * (10 * 1024 * 1024 + 1))
    assert r.status_code == 413
    assert r.json()["galat"]["kode"] == "berkas_terlalu_besar"


def test_unggah_diterima_berstatus_diproses(unggah, klien):
    r = unggah("VA-ASL-01.pdf")
    assert r.status_code == 202
    h = r.json()
    assert h["id"].startswith("b_") and h["status"] == "diproses"
    detail = klien.get(f"/api/v1/berkas/{h['id']}").json()
    assert detail["status"] == "diproses"
    assert "label" not in detail


def test_detail_tidak_ada(klien):
    r = klien.get("/api/v1/berkas/b_tidakada")
    assert r.status_code == 404


# ---------- worker ----------

def test_antrean_kosong_tidak_memproses_apa_apa(conn, mesin, tmp_path):
    assert proses_satu(conn, mesin, Penyimpanan(tmp_path)) is False


def test_berkas_asli_lolos(unggah, klien, conn, mesin, tmp_path):
    _, h = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-ASL-01.pdf")
    assert h["status"] == "selesai"
    assert h["label"] == "lolos"
    assert h["saran"] == "wajar"
    assert h["temuan"] == []
    assert h["klaim"]["sesi_ditagih"] == 8
    assert h["versi_aturan"]


def test_angka_disunting_prioritas(unggah, klien, conn, mesin, tmp_path):
    _, h = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-DST-01.pdf")
    assert h["label"] == "prioritas"
    assert h["saran"] == "telaah"
    assert {t["cek"] for t in h["temuan"]} == {"kecocokan_klaim", "suntingan"}
    assert h["klaim"]["peserta"] == "Ratna Kusuma"


def test_scan_buram_scan_ulang(unggah, klien, conn, mesin, tmp_path):
    _, h = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-BRM-01.pdf")
    assert h["label"] == "ulang"
    assert h["saran"] == "scanUlang"


def test_berkas_di_luar_dataset_gagal_aman_jadi_perlu_dicek(unggah, klien, conn, mesin, tmp_path):
    _, h = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "foto-juri.jpg", tipe="image/jpeg")
    assert h["status"] == "gagal"
    assert h["label"] == "cek"
    assert h["label"] != "lolos"
    assert h["temuan"][0]["kekuatan"] == "info"


def test_berkas_kembar_ditemukan_lewat_sidik_jari(unggah, klien, conn, mesin, tmp_path):
    asal, _ = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-KMB-00.pdf")
    kembar, h = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-KMB-01.pdf")
    assert h["label"] == "prioritas"
    k = next(t for t in h["temuan"] if t["cek"] == "berkas_kembar")
    assert k["kekuatan"] == "kuat"
    assert k["pasangan"] == asal
    assert h["keluarga"] == {"akar": asal, "anggota": sorted([asal, kembar])}


def test_berkas_kembar_tanpa_pasangan_di_arsip_tidak_dituduh(unggah, klien, conn, mesin, tmp_path):
    """Tanpa berkas asal di arsip, kembar tidak bisa dibuktikan, jadi bukan sinyal kuat."""
    _, h = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-KMB-01.pdf")
    assert not any(t["cek"] == "berkas_kembar" for t in h["temuan"])


# ---------- ketahanan worker ----------

class PenyimpananRusak:
    """File berkas hilang (mis. disk container diganti)."""

    def baca(self, rel):
        raise FileNotFoundError(rel)


class PenyimpananTanpaKembaran:
    """File berkas ada, tetapi file kembarannya di arsip hilang."""

    def __init__(self, asli, hilang):
        self.asli, self.hilang = asli, hilang

    def baca(self, rel):
        if rel == self.hilang:
            raise FileNotFoundError(rel)
        return self.asli.baca(rel)


def test_file_hilang_gagal_aman_dan_tidak_macet(unggah, klien, conn, mesin):
    id_ = unggah("VA-ASL-01.pdf").json()["id"]
    assert proses_satu(conn, mesin, PenyimpananRusak()) is True
    h = klien.get(f"/api/v1/berkas/{id_}").json()
    assert h["status"] == "gagal" and h["label"] == "cek"
    assert proses_satu(conn, mesin, PenyimpananRusak()) is False  # job tidak nyangkut


def test_file_kembaran_hilang_tidak_boleh_berujung_lolos(unggah, klien, conn, mesin, tmp_path):
    asal, _ = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-KMB-00.pdf")
    path_asal = conn.execute("select path_storage from berkas where id = %s", (asal,)).fetchone()["path_storage"]
    id_ = unggah("VA-KMB-01.pdf").json()["id"]
    assert proses_satu(conn, mesin, PenyimpananTanpaKembaran(Penyimpanan(tmp_path), path_asal)) is True
    h = klien.get(f"/api/v1/berkas/{id_}").json()
    assert h["status"] == "gagal" and h["label"] == "cek"


def test_job_nyangkut_diambil_ulang_setelah_batas_waktu(unggah, klien, conn, mesin, tmp_path):
    id_ = unggah("VA-ASL-01.pdf").json()["id"]
    conn.execute("update job set status = 'jalan', percobaan = 1, diambil = now() - interval '10 minutes'")
    assert proses_satu(conn, mesin, Penyimpanan(tmp_path)) is True
    assert klien.get(f"/api/v1/berkas/{id_}").json()["status"] == "selesai"


def test_job_yang_sedang_dikerjakan_tidak_diambil_ganda(unggah, conn, mesin, tmp_path):
    unggah("VA-ASL-01.pdf")
    conn.execute("update job set status = 'jalan', percobaan = 1, diambil = now()")
    assert proses_satu(conn, mesin, Penyimpanan(tmp_path)) is False


def test_job_terlalu_sering_gagal_tidak_diulang_terus(unggah, conn, mesin, tmp_path):
    unggah("VA-ASL-01.pdf")
    conn.execute("update job set status = 'jalan', percobaan = 3, diambil = now() - interval '10 minutes'")
    assert proses_satu(conn, mesin, Penyimpanan(tmp_path)) is False


# ---------- detail dan CORS untuk FE ----------

def test_detail_memuat_nama_berkas_asli(unggah, klien, conn, mesin, tmp_path):
    _, h = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-ASL-01.pdf")
    assert h["berkas"]["nama"] == "VA-ASL-01.pdf"


def test_cors_mengizinkan_fe_lokal(klien):
    r = klien.options(
        "/api/v1/berkas",
        headers={"Origin": "http://localhost:8899", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:8899"


def test_cors_menolak_origin_asing(klien):
    r = klien.options(
        "/api/v1/berkas",
        headers={"Origin": "https://jahat.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in r.headers


# ---------- klaim dari SEP ----------

class MesinSpy:
    """Membungkus mesin asli dan mencatat klaim yang dikirim API."""

    def __init__(self, asli):
        self.asli, self.klaim = asli, []

    def analisis(self, nama, isi, klaim=None):
        self.klaim.append(klaim)
        return self.asli.analisis(nama, isi, klaim)

    def bandingkan(self, *a):
        return self.asli.bandingkan(*a)


def test_sep_saat_unggah_membuat_api_mengirim_klaim_ke_mesin(unggah, conn, mesin, tmp_path):
    unggah("VA-DST-01.pdf", sep="0901R0140826V583301")
    spy = MesinSpy(mesin)
    assert proses_satu(conn, spy, Penyimpanan(tmp_path))
    assert spy.klaim[0]["sesi_ditagih"] == 8
    assert spy.klaim[0]["sep"] == "0901R0140826V583301"


def test_tanpa_sep_klaim_dikirim_kosong(unggah, conn, mesin, tmp_path):
    unggah("VA-DST-01.pdf")
    spy = MesinSpy(mesin)
    proses_satu(conn, spy, Penyimpanan(tmp_path))
    assert not spy.klaim[0]


def test_sep_tidak_dikenal_tetap_diproses_tanpa_klaim(unggah, conn, mesin, tmp_path):
    unggah("VA-ASL-01.pdf", sep="0000X0000000V000000")
    spy = MesinSpy(mesin)
    assert proses_satu(conn, spy, Penyimpanan(tmp_path))
    assert not spy.klaim[0]


# ---------- antrean ----------

def test_antrean_urut_prioritas_dulu_dan_bisa_disaring(unggah, klien, conn, mesin, tmp_path):
    for nama in ["VA-ASL-01.pdf", "VA-DST-01.pdf", "VA-BRM-01.pdf"]:
        unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, nama)
    semua = klien.get("/api/v1/berkas").json()
    assert semua["total"] == 3
    assert [i["label"] for i in semua["item"]] == ["prioritas", "ulang", "lolos"]
    hanya = klien.get("/api/v1/berkas", params={"label": "ulang"}).json()
    assert hanya["total"] == 1 and hanya["item"][0]["label"] == "ulang"


def test_antrean_halaman(unggah, klien, conn, mesin, tmp_path):
    for nama in ["VA-ASL-01.pdf", "VA-DST-01.pdf", "VA-BRM-01.pdf"]:
        unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, nama)
    h = klien.get("/api/v1/berkas", params={"per_halaman": 2, "halaman": 2}).json()
    assert h["total"] == 3 and len(h["item"]) == 1


# ---------- keputusan ----------

def test_keputusan_sesuai_saran_boleh_tanpa_catatan(unggah, klien, conn, mesin, tmp_path):
    id_, h = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-DST-01.pdf")
    r = klien.post(f"/api/v1/berkas/{id_}/keputusan", json={"tindakan": "telaah"})
    assert r.status_code == 201
    assert r.json()["laporan"]["url"].endswith(f"/berkas/{id_}/laporan")
    assert klien.get(f"/api/v1/berkas/{id_}").json()["keputusan"]["tindakan"] == "telaah"


def test_keputusan_beda_dari_saran_wajib_catatan(unggah, klien, conn, mesin, tmp_path):
    id_, _ = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-DST-01.pdf")
    r = klien.post(f"/api/v1/berkas/{id_}/keputusan", json={"tindakan": "wajar"})
    assert r.status_code == 422
    assert r.json()["galat"]["kode"] == "catatan_wajib"
    ok = klien.post(f"/api/v1/berkas/{id_}/keputusan", json={"tindakan": "wajar", "catatan": "Sudah dikonfirmasi RS."})
    assert ok.status_code == 201
    assert "laporan" not in ok.json()


def test_keputusan_tindakan_tidak_dikenal(unggah, klien, conn, mesin, tmp_path):
    id_, _ = unggah_dan_proses(unggah, klien, conn, mesin, tmp_path, "VA-ASL-01.pdf")
    r = klien.post(f"/api/v1/berkas/{id_}/keputusan", json={"tindakan": "hapus"})
    assert r.status_code == 422


def test_keputusan_untuk_berkas_belum_selesai_ditolak(unggah, klien):
    id_ = unggah("VA-ASL-01.pdf").json()["id"]
    r = klien.post(f"/api/v1/berkas/{id_}/keputusan", json={"tindakan": "wajar"})
    assert r.status_code == 409


# ---------- kesehatan ----------

def test_kesehatan(klien):
    h = klien.get("/api/v1/kesehatan").json()
    assert h == {"api": "ok", "db": "ok", "mesin": "ok"}
