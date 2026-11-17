"""Uji D-03: endpoint tulis untuk FE (pengaturan, mulai, keputusan, rekaman, reset demo)."""
import json

import pytest

from tests.util_v3 import jam_palsu, ubah, wib

S1 = "CALL-P-S1-2026-08"


def selesaikan(conn, id_="CALL-P-S1-2026-08", label="Tidak sesuai"):
    ubah(conn, id_, status="selesai", label=label, waktu_selesai=wib(2026, 10, 6, 10, 13))


def kunci(conn, kunci_):
    return conn.execute("select nilai from pengaturan where kunci = %s", (kunci_,)).fetchone()["nilai"]


# ---- PUT /pengaturan ----

def test_nyalakan_mode_otomatis(klien_v3, conn_v3):
    r = klien_v3.put("/api/v1/pengaturan", json={"mode_otomatis": True})
    assert r.status_code == 200
    assert r.json() == {"mode_otomatis": True, "jeda": False, "jam_mulai": "09:00", "jam_selesai": "17:00",
                        "jeda_wa_menit": 1, "jeda_percobaan_menit": 2}
    assert kunci(conn_v3, "mode_otomatis") is True
    assert klien_v3.get("/api/v1/pengaturan").json()["mode_otomatis"] is True


def test_jeda_dan_lanjutkan(klien_v3):
    klien_v3.put("/api/v1/pengaturan", json={"mode_otomatis": True})
    assert klien_v3.put("/api/v1/pengaturan", json={"jeda": True}).json()["jeda"] is True
    assert klien_v3.put("/api/v1/pengaturan", json={"jeda": False}).json() == {
        "mode_otomatis": True, "jeda": False, "jam_mulai": "09:00", "jam_selesai": "17:00",
        "jeda_wa_menit": 1, "jeda_percobaan_menit": 2,
    }


def test_mengubah_mode_mematikan_jeda(klien_v3):
    klien_v3.put("/api/v1/pengaturan", json={"mode_otomatis": True})
    klien_v3.put("/api/v1/pengaturan", json={"jeda": True})
    h = klien_v3.put("/api/v1/pengaturan", json={"mode_otomatis": True}).json()  # nilai sama pun mematikan Jeda
    assert h["mode_otomatis"] is True and h["jeda"] is False
    klien_v3.put("/api/v1/pengaturan", json={"jeda": True})
    h = klien_v3.put("/api/v1/pengaturan", json={"mode_otomatis": False}).json()
    assert h["mode_otomatis"] is False and h["jeda"] is False


def test_jeda_ditolak_bila_mode_mati(klien_v3):
    klien_v3.put("/api/v1/pengaturan", json={"mode_otomatis": False})
    r = klien_v3.put("/api/v1/pengaturan", json={"jeda": True})
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "pengaturan_tidak_valid"
    assert klien_v3.get("/api/v1/pengaturan").json()["jeda"] is False


def test_pengaturan_sebagian_dan_field_asing_diabaikan(klien_v3):
    h = klien_v3.put("/api/v1/pengaturan", json={"jeda_wa_menit": 3, "jam_mulai": "08:30", "ngawur": 1}).json()
    assert (h["jeda_wa_menit"], h["jam_mulai"], h["jam_selesai"], h["jeda_percobaan_menit"]) == (3, "08:30", "17:00", 2)
    assert "ngawur" not in h


@pytest.mark.parametrize("body", [
    {"mode_otomatis": "ya"}, {"mode_otomatis": 1}, {"jam_mulai": "9:00"}, {"jam_mulai": "25:00"},
    {"jeda_wa_menit": -1}, {"jeda_wa_menit": "1"}, {"jeda_percobaan_menit": True}, {"jeda_wa_menit": 1.5},
    {"jam_mulai": "17:00"}, {"jam_selesai": "08:00"},
])
def test_pengaturan_tidak_valid_ditolak_dan_tidak_menyimpan(klien_v3, body):
    r = klien_v3.put("/api/v1/pengaturan", json=body)
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "pengaturan_tidak_valid"
    assert klien_v3.get("/api/v1/pengaturan").json() == {
        "mode_otomatis": True, "jeda": False, "jam_mulai": "09:00", "jam_selesai": "17:00",
        "jeda_wa_menit": 1, "jeda_percobaan_menit": 2,
    }


def test_pengaturan_tidak_bisa_menimpa_detak_stasiun(klien_v3, conn_v3):
    detak = {"terakhir_terlihat": "2026-10-06T10:00:00+07:00", "siap": True, "alasan": None, "perangkat": "uji"}
    conn_v3.execute("insert into pengaturan (kunci, nilai) values ('stasiun', %s)", (json.dumps(detak),))
    h = klien_v3.put("/api/v1/pengaturan", json={"stasiun": {"siap": False}, "jeda_wa_menit": 2}).json()
    assert "stasiun" not in h and h["jeda_wa_menit"] == 2
    assert kunci(conn_v3, "stasiun") == detak


# ---- POST /panggilan/{id}/mulai ----

def test_dahulukan_menandai_prioritas(klien_v3, conn_v3):
    r = klien_v3.post("/api/v1/panggilan/CALL-P-S3-2026-08/mulai")
    assert r.status_code == 200
    assert r.json()["id"] == "CALL-P-S3-2026-08" and r.json()["prioritas"] is True and r.json()["status"] == "antre"
    assert conn_v3.execute("select prioritas from panggilan where id = 'CALL-P-S3-2026-08'").fetchone()["prioritas"] is True
    ids = [b["id"] for b in klien_v3.get("/api/v1/antrean").json()["baris"]]
    assert ids[0] == "CALL-P-S3-2026-08"  # prioritas mendahului S1


def test_telepon_sekarang_menolak_yang_bukan_antre_dan_tidak_ada(klien_v3, conn_v3):
    r = klien_v3.post("/api/v1/panggilan/CALL-LATAR-001/mulai")
    assert r.status_code == 409 and r.json()["galat"]["kode"] == "bukan_antre"
    ubah(conn_v3, S1, status="menelepon")
    assert klien_v3.post(f"/api/v1/panggilan/{S1}/mulai").status_code == 409
    r = klien_v3.post("/api/v1/panggilan/CALL-NGAWUR/mulai")
    assert r.status_code == 404 and r.json()["galat"]["kode"] == "panggilan_tidak_ada"


# ---- POST /panggilan/{id}/keputusan ----

def test_ikut_saran_memakai_saran_label(klien_v3, conn_v3, monkeypatch):
    jam_palsu(monkeypatch, jam_=10, menit=15, detik=20)
    selesaikan(conn_v3)
    r = klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan", json={"ikut_saran": True})
    assert r.status_code == 201
    k = r.json()
    assert (k["panggilan_id"], k["verifikator"], k["tindakan"], k["ikut_saran"], k["alasan"]) == (S1, "R. Santoso", "klarifikasi", True, None)
    assert k["waktu"] == "2026-10-06T10:15:20+07:00" and isinstance(k["id"], int)
    row = conn_v3.execute("select tindakan from keputusan_panggilan where panggilan_id = %s", (S1,)).fetchone()
    assert row["tindakan"] == "minta_klarifikasi_rs"
    assert klien_v3.get(f"/api/v1/panggilan/{S1}").json()["keputusan"] == k


def test_ikut_saran_pantau_untuk_label_tanpa_tindakan(klien_v3, conn_v3):
    ubah(conn_v3, "CALL-P-S4-2026-08", status="selesai", label="Tidak yakin")
    k = klien_v3.post("/api/v1/panggilan/CALL-P-S4-2026-08/keputusan", json={"ikut_saran": True, "tindakan": "tutup"}).json()
    assert k["tindakan"] == "pantau"  # ikut_saran memakai saran, tindakan kiriman diabaikan


def test_tidak_ikut_saran_butuh_alasan(klien_v3, conn_v3):
    selesaikan(conn_v3)
    for alasan in (None, "", "   "):
        r = klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan", json={"ikut_saran": False, "tindakan": "teruskan", "alasan": alasan})
        assert r.status_code == 422 and r.json()["galat"]["kode"] == "alasan_wajib", alasan
    assert conn_v3.execute("select count(*) as n from keputusan_panggilan").fetchone()["n"] == 0


def test_tidak_ikut_saran_dengan_alasan_tersimpan(klien_v3, conn_v3):
    selesaikan(conn_v3)
    r = klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan",
                      json={"ikut_saran": False, "tindakan": "teruskan", "alasan": "  Pola serupa di dua pasien lain.  "})
    assert r.status_code == 201
    assert (r.json()["tindakan"], r.json()["ikut_saran"], r.json()["alasan"]) == ("teruskan", False, "Pola serupa di dua pasien lain.")


@pytest.mark.parametrize("tindakan", [None, "pantau", "ngawur", "tutup_kasus"])
def test_tindakan_tidak_dikenal(klien_v3, conn_v3, tindakan):
    selesaikan(conn_v3)
    r = klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan", json={"ikut_saran": False, "tindakan": tindakan, "alasan": "x"})
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "tindakan_tidak_dikenal"


def test_tindakan_sama_dengan_saran_ditolak(klien_v3, conn_v3):
    selesaikan(conn_v3)
    r = klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan", json={"ikut_saran": False, "tindakan": "klarifikasi", "alasan": "x"})
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "tindakan_sama_saran"


def test_keputusan_sebelum_selesai_dan_panggilan_tidak_ada(klien_v3, conn_v3):
    r = klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan", json={"ikut_saran": True})
    assert r.status_code == 409 and r.json()["galat"]["kode"] == "belum_selesai"
    ubah(conn_v3, S1, status="membaca_jawaban")
    assert klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan", json={"ikut_saran": True}).status_code == 409
    r = klien_v3.post("/api/v1/panggilan/CALL-NGAWUR/keputusan", json={"ikut_saran": True})
    assert r.status_code == 404 and r.json()["galat"]["kode"] == "panggilan_tidak_ada"


def test_ikut_saran_wajib_ada(klien_v3, conn_v3):
    selesaikan(conn_v3)
    r = klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan", json={"tindakan": "tutup"})
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "validasi"


def test_keputusan_baru_menggantikan_yang_lama_tetapi_riwayat_tersimpan(klien_v3, conn_v3):
    selesaikan(conn_v3)
    klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan", json={"ikut_saran": True})
    klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan", json={"ikut_saran": False, "tindakan": "teruskan", "alasan": "Ubah."})
    h = klien_v3.get("/api/v1/keputusan").json()
    assert [(k["tindakan"], k["terkini"]) for k in h] == [("teruskan", True), ("klarifikasi", False)]
    assert klien_v3.get(f"/api/v1/panggilan/{S1}").json()["keputusan"]["tindakan"] == "teruskan"
    baris = {b["id"]: b for b in klien_v3.get("/api/v1/antrean").json()["baris"]}
    assert baris[S1]["keputusan_tindakan"] == "teruskan"
    assert klien_v3.get("/api/v1/antrean").json()["angka"]["menunggu_keputusan"] == 2  # hanya dua riwayat Tidak sesuai yang belum diputuskan


# ---- GET /panggilan/{id}/rekaman ----

def simpan_rekaman(tmp_path, id_=S1, isi=b"0123456789" * 100, ekstensi=".webm"):
    rel = f"rekaman/{id_}{ekstensi}"
    (tmp_path / "rekaman").mkdir(exist_ok=True)
    (tmp_path / rel).write_bytes(isi)
    return rel


def test_rekaman_diputar_dengan_tipe_audio_dan_range(klien_v3, conn_v3, tmp_path, monkeypatch):
    jam_palsu(monkeypatch)
    selesaikan(conn_v3)
    ubah(conn_v3, S1, rekaman_path=simpan_rekaman(tmp_path))
    r = klien_v3.get(f"/api/v1/panggilan/{S1}/rekaman")
    assert r.status_code == 200 and r.headers["content-type"].startswith("audio/webm") and len(r.content) == 1000
    r = klien_v3.get(f"/api/v1/panggilan/{S1}/rekaman", headers={"Range": "bytes=10-19"})
    assert r.status_code == 206 and r.content == b"0123456789" and r.headers["content-range"] == "bytes 10-19/1000"


def test_rekaman_mp3_dari_stub_agen_bertipe_mpeg(klien_v3, conn_v3, tmp_path, monkeypatch):
    jam_palsu(monkeypatch)
    selesaikan(conn_v3)
    ubah(conn_v3, S1, rekaman_path=simpan_rekaman(tmp_path, ekstensi=".mp3"))
    assert klien_v3.get(f"/api/v1/panggilan/{S1}/rekaman").headers["content-type"].startswith("audio/mpeg")


def test_rekaman_tidak_ada_untuk_berbagai_sebab(klien_v3, conn_v3, tmp_path, monkeypatch):
    jam_palsu(monkeypatch)
    # belum ada path
    selesaikan(conn_v3)
    r = klien_v3.get(f"/api/v1/panggilan/{S1}/rekaman")
    assert r.status_code == 404 and r.json()["galat"]["kode"] == "rekaman_tidak_ada"
    # path ada tapi berkas hilang
    ubah(conn_v3, S1, rekaman_path="rekaman/hilang.webm")
    assert klien_v3.get(f"/api/v1/panggilan/{S1}/rekaman").status_code == 404
    # label tanpa rekaman (R5.5)
    ubah(conn_v3, S1, label="Tidak yakin", rekaman_path=simpan_rekaman(tmp_path))
    assert klien_v3.get(f"/api/v1/panggilan/{S1}/rekaman").status_code == 404
    # sudah lewat hapus_pada
    ubah(conn_v3, "CALL-LATAR-003", rekaman_path=simpan_rekaman(tmp_path, "CALL-LATAR-003"))
    assert klien_v3.get("/api/v1/panggilan/CALL-LATAR-003/rekaman").status_code == 200
    jam_palsu(monkeypatch, bulan=12)
    assert klien_v3.get("/api/v1/panggilan/CALL-LATAR-003/rekaman").status_code == 404
    # panggilan tidak ada
    assert klien_v3.get("/api/v1/panggilan/CALL-NGAWUR/rekaman").json()["galat"]["kode"] == "panggilan_tidak_ada"


def test_rekaman_tidak_bisa_keluar_dari_penyimpanan(klien_v3, conn_v3, tmp_path, monkeypatch):
    jam_palsu(monkeypatch)
    selesaikan(conn_v3)
    ubah(conn_v3, S1, rekaman_path="../../etc/hosts")
    assert klien_v3.get(f"/api/v1/panggilan/{S1}/rekaman").status_code == 404


# ---- POST /demo/reset ----

def test_reset_demo_mengembalikan_keadaan_awal(klien_v3, conn_v3, tmp_path):
    klien_v3.put("/api/v1/pengaturan", json={"mode_otomatis": False})
    selesaikan(conn_v3)
    rel = simpan_rekaman(tmp_path)
    ubah(conn_v3, S1, rekaman_path=rel, prioritas=True)
    ubah(conn_v3, "CALL-P-S3-2026-08", status="menelepon", percobaan=1)
    conn_v3.execute("insert into panggilan_log (panggilan_id, status) values (%s, 'menelepon')", (S1,))
    klien_v3.post(f"/api/v1/panggilan/{S1}/keputusan", json={"ikut_saran": True})
    klien_v3.post("/api/v1/panggilan/CALL-LATAR-001/keputusan", json={"ikut_saran": True})
    assert (tmp_path / rel).exists()

    r = klien_v3.post("/api/v1/demo/reset")
    assert r.status_code == 200 and r.json() == {"ok": True}

    h = klien_v3.get("/api/v1/antrean").json()
    assert h["angka"] == {
        "pasien_aktif": 304, "terpicu": 32, "dipilih": 34, "hanya_model": 2, "sudah_ditelepon": 32, "tidak_sesuai": 25,
        "rs_perlu_klarifikasi": 1, "antre": 2, "menunggu_keputusan": 25,
    }
    assert h["pengaturan"]["mode_otomatis"] is False and h["pengaturan"]["jeda"] is False  # demo: verifikator menyalakan
    antre = [b for b in h["baris"] if b["status"] == "antre"]
    assert [(b["pasien"], b["penerima"]["nama"]) for b in antre] == [("Hartono", "Imelda"), ("Zahra", "Zahra")]
    assert all(not b["prioritas"] and b["percobaan"] == 0 for b in antre)
    assert conn_v3.execute("select count(*) as n from panggilan_log").fetchone()["n"] == 0
    assert klien_v3.get("/api/v1/keputusan").json() == []
    assert not (tmp_path / rel).exists()


def test_reset_demo_tidak_menyentuh_data_master(klien_v3, conn_v3):
    n = lambda t: conn_v3.execute(f"select count(*) as n from {t}").fetchone()["n"]
    tabel = ("rumah_sakit", "peserta", "klaim_sesi", "libur_nasional", "indikator_bulanan")
    sebelum = [n(t) for t in tabel]
    assert sebelum == [5, 410, 4938, 4, 302]
    klien_v3.post("/api/v1/demo/reset")
    assert [n(t) for t in tabel] == [5, 412, 4957, 4, 304]  # hanya dua pasien demo yang ditambahkan
    conn_v3.execute("update peserta set nama = 'Lama', no_hp_keluarga = '+6281111111111' where id_peserta = 'P-D1'")
    conn_v3.execute("update peserta set nama = 'Pasien Lain' where id_peserta = 'P0001'")
    conn_v3.execute("delete from klaim_sesi where id_klaim = 'SEP-DEMO-000001'")
    klien_v3.post("/api/v1/demo/reset")
    assert [n(t) for t in tabel] == [5, 412, 4957, 4, 304]
    baris = lambda pid: conn_v3.execute("select nama, no_hp_keluarga from peserta where id_peserta = %s", (pid,)).fetchone()
    assert baris("P-D1") == {"nama": "Hartono", "no_hp_keluarga": "+6281111111111"}  # data demo diperbarui, nomor tetap
    assert baris("P0001")["nama"] == "Pasien Lain"


def test_reset_demo_mematikan_mode_otomatis_dan_jeda(klien_v3):
    klien_v3.put("/api/v1/pengaturan", json={"mode_otomatis": True, "jeda": True})
    klien_v3.post("/api/v1/demo/reset")
    p = klien_v3.get("/api/v1/pengaturan").json()
    assert (p["mode_otomatis"], p["jeda"]) == (False, False)


# ---- POST /panggilan/{id}/batal ----

def log_db(conn, id_):
    return [(r["status"], r["percobaan"], r["catatan"]) for r in conn.execute(
        "select status, percobaan, catatan from panggilan_log where panggilan_id = %s order by waktu, id", (id_,))]


@pytest.mark.parametrize("status,percobaan", [("wa_terkirim", 0), ("menelepon", 1), ("tersambung", 1), ("merekam", 1)])
def test_batal_percobaan_pertama_kembali_antre(klien_v3, conn_v3, monkeypatch, status, percobaan):
    jam_palsu(monkeypatch, menit=4)
    ubah(conn_v3, S1, status=status, percobaan=percobaan, diambil_pada=wib(2026, 10, 6, 10, 0),
         transkrip=json.dumps([{"detik": 0, "pembicara": "ai", "teks": "Halo."}]), tangkapan_sementara=json.dumps({"hadir": True}))
    r = klien_v3.post(f"/api/v1/panggilan/{S1}/batal")
    assert r.status_code == 200
    b = r.json()
    assert (b["id"], b["status"], b["percobaan"], b["coba_lagi_setelah"]) == (S1, "antre", 1, "2026-10-06T10:06:00+07:00")
    db = conn_v3.execute("select diambil_pada, transkrip, tangkapan_sementara, label from panggilan where id = %s", (S1,)).fetchone()
    assert db == {"diambil_pada": None, "transkrip": None, "tangkapan_sementara": None, "label": None}
    assert log_db(conn_v3, S1) == [("menelepon", 1, "dibatalkan_verifikator")]


def test_batal_percobaan_kedua_menjadi_tidak_terhubung_dan_chat_cadangan(klien_v3, conn_v3, monkeypatch):
    jam_palsu(monkeypatch, menit=4)
    ubah(conn_v3, S1, status="menelepon", percobaan=2)
    b = klien_v3.post(f"/api/v1/panggilan/{S1}/batal").json()
    assert (b["status"], b["label"], b["percobaan"], b["coba_lagi_setelah"]) == ("tidak_terhubung", "tidak_terhubung", 2, None)
    assert log_db(conn_v3, S1) == [("menelepon", 2, "dibatalkan_verifikator"), ("tidak_terhubung", 2, "chat:simulasi")]
    assert conn_v3.execute("select chat_cadangan_terkirim as c from panggilan where id = %s", (S1,)).fetchone()["c"] is True


def test_batal_antre_yang_sudah_diambil_hanya_melepas_kunci(klien_v3, conn_v3):
    ubah(conn_v3, S1, percobaan=1, diambil_pada=wib(2026, 10, 6, 10, 0))
    b = klien_v3.post(f"/api/v1/panggilan/{S1}/batal").json()
    assert (b["status"], b["percobaan"]) == ("antre", 1)
    assert conn_v3.execute("select diambil_pada from panggilan where id = %s", (S1,)).fetchone()["diambil_pada"] is None
    assert log_db(conn_v3, S1) == []


def test_batal_ditolak_bila_tidak_berjalan(klien_v3, conn_v3):
    for id_, ubahan in ((S1, {}), ("CALL-LATAR-001", {}), ("CALL-P-S3-2026-08", {"status": "membaca_jawaban"})):
        if ubahan:
            ubah(conn_v3, id_, **ubahan)
        r = klien_v3.post(f"/api/v1/panggilan/{id_}/batal")
        assert r.status_code == 409 and r.json()["galat"]["kode"] == "tidak_bisa_dibatalkan", id_
    r = klien_v3.post("/api/v1/panggilan/CALL-NGAWUR/batal")
    assert r.status_code == 404 and r.json()["galat"]["kode"] == "panggilan_tidak_ada"


def test_antrean_melepas_panggilan_macet_tanpa_stasiun(klien_v3, conn_v3, monkeypatch):
    ubah(conn_v3, S1, status="menelepon", percobaan=1, diambil_pada=wib(2026, 10, 6, 10, 0))
    jam_palsu(monkeypatch, menit=4, detik=59)
    baris = {b["id"]: b for b in klien_v3.get("/api/v1/antrean").json()["baris"]}
    assert baris[S1]["status"] == "menelepon"
    jam_palsu(monkeypatch, menit=5, detik=1)
    baris = {b["id"]: b for b in klien_v3.get("/api/v1/antrean").json()["baris"]}
    assert (baris[S1]["status"], baris[S1]["coba_lagi_setelah"]) == ("antre", "2026-10-06T10:07:01+07:00")
    assert log_db(conn_v3, S1) == [("menelepon", 1, "macet")]
