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
