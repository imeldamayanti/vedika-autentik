"""Uji D-02: endpoint baca untuk FE (Kontrak A v3). Berjalan di schema sementara uji3 yang di-seed penuh."""
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import config, jam
from app.deps import get_conn, get_mesin
from app.main import app
from app.mesin import KlienMesin
from stub_mesin.main import app as app_stub

DATA = config.AKAR / "data-uji-konfirmasi"
S1 = "CALL-P-S1-2026-08"


@pytest.fixture
def klien_v3(conn_v3):
    app.dependency_overrides[get_conn] = lambda: conn_v3
    app.dependency_overrides[get_mesin] = lambda: KlienMesin(TestClient(app_stub))
    yield TestClient(app)
    app.dependency_overrides.clear()


def jam_palsu(monkeypatch, tahun=2026, bulan=10, tanggal=6, jam_=10, menit=0):
    waktu = datetime(tahun, bulan, tanggal, jam_, menit, tzinfo=config.ZONA)
    monkeypatch.setattr(jam, "sekarang", lambda: waktu)
    return waktu


def ubah(conn, id_, **kolom):
    sets = ", ".join(f"{k} = %s" for k in kolom)
    conn.execute(f"update panggilan set {sets} where id = %s", (*kolom.values(), id_))


# ---- GET /antrean ----

def test_antrean_angka_awal_demo(klien_v3):
    h = klien_v3.get("/api/v1/antrean").json()
    assert h["bulan"] == "2026-08"
    assert h["angka"] == {
        "pasien_aktif": 300, "terpicu": 30, "sudah_ditelepon": 4, "tidak_sesuai": 2, "rs_perlu_klarifikasi": 0,
        "antre": 26, "menunggu_keputusan": 2,
    }
    assert len(h["baris"]) == 30
    assert [r["nama"] for r in h["daftar_rs"]][:2] == ["RS Melati Sehat", "RSU Bakti Mulia"] and len(h["daftar_rs"]) == 5


def test_antrean_s7_tidak_pernah_muncul(klien_v3):
    ids = {r["id"] for r in klien_v3.get("/api/v1/antrean").json()["baris"]}
    assert "CALL-P-S7-2026-08" not in ids
    assert all(len(r["indikator"]) >= 2 for r in klien_v3.get("/api/v1/antrean").json()["baris"])


def test_antrean_urutan_skenario_dulu_riwayat_terbaru_di_akhir(klien_v3):
    ids = [r["id"] for r in klien_v3.get("/api/v1/antrean").json()["baris"]]
    assert ids[:7] == [f"CALL-P-S{n}-2026-08" for n in (1, 2, 3, 4, 5, 6, 8)]
    assert ids[-4:] == ["CALL-LATAR-004", "CALL-LATAR-003", "CALL-LATAR-002", "CALL-LATAR-001"]


def test_antrean_bentuk_baris_s1_dan_riwayat(klien_v3):
    baris = {r["id"]: r for r in klien_v3.get("/api/v1/antrean").json()["baris"]}
    assert baris[S1] == {
        "id": S1, "pasien": "Andi Pratama", "umur": 54, "rs": "RS01", "nama_rs": "RS Melati Sehat", "ditagih": 11,
        "indikator": ["I1", "I2", "I4"], "penerima": {"nama": "Andi Pratama", "hubungan": "peserta"},
        "status": "antre", "label": None, "keputusan_tindakan": None, "prioritas": False, "percobaan": 0,
    }
    assert baris["CALL-P-S2-2026-08"]["penerima"] == {"nama": "Dewi Rahmawati", "hubungan": "anak"}
    r1 = baris["CALL-LATAR-001"]
    assert (r1["status"], r1["label"], r1["penerima"]["hubungan"], r1["pasien"]) == ("selesai", "tidak_sesuai", "orang tua", "Bayu Utami")


def test_antrean_filter_tidak_mengubah_angka(klien_v3):
    h = klien_v3.get("/api/v1/antrean", params={"id_rs": "RS03", "status": "antre"}).json()
    assert {r["rs"] for r in h["baris"]} == {"RS03"} and {r["status"] for r in h["baris"]} == {"antre"}
    assert 1 <= len(h["baris"]) < 26 and h["angka"]["antre"] == 26


def test_antrean_urutan_berjalan_prioritas_antre_selesai(klien_v3, conn_v3):
    ubah(conn_v3, "CALL-P-S3-2026-08", status="menelepon")
    ubah(conn_v3, "CALL-P-S8-2026-08", prioritas=True)
    ubah(conn_v3, S1, status="tidak_terhubung", label="Tidak terhubung", waktu_selesai=datetime(2026, 10, 6, 12, tzinfo=config.ZONA))
    ids = [r["id"] for r in klien_v3.get("/api/v1/antrean").json()["baris"]]
    assert ids[:2] == ["CALL-P-S3-2026-08", "CALL-P-S8-2026-08"]
    assert ids[2] == "CALL-P-S2-2026-08"
    assert ids[-5] == S1  # selesai terbaru dulu, di atas empat riwayat


def test_antrean_pengaturan_dan_jam(klien_v3, monkeypatch):
    jam_palsu(monkeypatch, jam_=10)
    p = klien_v3.get("/api/v1/antrean").json()["pengaturan"]
    assert p == {
        "mode_otomatis": False, "jeda": False, "jam_mulai": "09:00", "jam_selesai": "17:00", "jeda_wa_menit": 1,
        "jeda_percobaan_menit": 2, "dalam_jam": True, "waktu_server": "2026-10-06T10:00:00+07:00",
    }
    jam_palsu(monkeypatch, jam_=17, menit=0)
    assert klien_v3.get("/api/v1/antrean").json()["pengaturan"]["dalam_jam"] is False
    jam_palsu(monkeypatch, jam_=8, menit=59)
    assert klien_v3.get("/api/v1/antrean").json()["pengaturan"]["dalam_jam"] is False


def test_antrean_bulan_tanpa_data_dan_bulan_salah(klien_v3):
    h = klien_v3.get("/api/v1/antrean", params={"bulan": "2026-09"}).json()
    assert h["baris"] == [] and h["angka"]["pasien_aktif"] == 0
    r = klien_v3.get("/api/v1/antrean", params={"bulan": "Agustus"})
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "validasi"


# ---- GET /panggilan/{id} ----

def test_detail_s1_sebelum_ditelepon(klien_v3):
    d = klien_v3.get(f"/api/v1/panggilan/{S1}").json()
    assert d["sumber"] == "panggilan" and d["status"] == "antre" and d["percobaan"] == 0
    assert d["ditagih"] == 11 and len(d["tanggal"]) == 11 and d["tanggal"][0] == "2026-08-03"
    assert d["tanda_tanggal"] == {"2026-08-16": "Minggu", "2026-08-17": "Libur nasional"}
    assert d["tanggal_libur"] == ["2026-08-16", "2026-08-17"] and d["indikator"] == ["I1", "I2", "I4"]
    assert d["penerima"] == {"nama": "Andi Pratama", "hubungan": "peserta"}
    for kunci in ("jawaban", "label", "alasan", "selisih", "saran", "rekaman", "waktu", "durasi", "keputusan", "hapus_pada"):
        assert d[kunci] is None, kunci
    assert d["log"] == [] and d["transkrip"] == [] and d["tangkapan_sementara"] is None
    assert d["toleransi"] == 2 and d["galat_pembaca"] is None
    assert d["konteks_rs"] == {"rs": "RS01", "tidak_sesuai": 2, "terjawab": 4, "status": "Normal"}


def test_detail_pesan_wa_persis_lampiran_b(klien_v3):
    wa = klien_v3.get(f"/api/v1/panggilan/{S1}").json()["pesan_wa"]
    assert wa["dari"] == "0800-0000-0165" and wa["cadangan"] is None
    assert wa["pemberitahuan"] == (
        "Halo Andi Pratama. Ini BPJS Kesehatan. Dalam 1 menit kami akan menelepon dari nomor 0800-0000-0165 untuk "
        "konfirmasi singkat layanan fisioterapi Andi Pratama di RS Melati Sehat bulan Agustus. Ini bukan tagihan. "
        "Kami tidak akan meminta data pribadi, kode OTP, atau pembayaran. Untuk memastikan pesan ini, hubungi Care Center 165."
    )
    assert "http" not in wa["pemberitahuan"]


def test_detail_minggu_dan_libur_tidak_dobel(klien_v3):
    d = klien_v3.get("/api/v1/panggilan/CALL-P-S2-2026-08").json()
    assert d["tanda_tanggal"] == {"2026-08-23": "Minggu"}
    assert d["penerima"] == {"nama": "Dewi Rahmawati", "hubungan": "anak"}


def test_detail_riwayat_latar_tidak_sesuai(klien_v3):
    d = klien_v3.get("/api/v1/panggilan/CALL-LATAR-001").json()
    assert d["sumber"] == "sintetis-riwayat" and d["status"] == "selesai" and d["label"] == "tidak_sesuai"
    assert d["waktu"] == "2026-10-05T09:42:00+07:00" and d["durasi"] == 84
    assert d["penerima"] == {"nama": "Wahyu Gunawan", "hubungan": "orang tua"}
    assert d["jawaban"]["penerima"] == "keluarga" and d["jawaban"]["hubungan"] == "orang tua"
    assert d["jawaban"]["membantah_tanggal_libur"] is None  # key yang tak ada di baris lama dilengkapi null
    assert (d["selisih"], d["saran"], d["alasan"]) == (10, "klarifikasi", "Ditagih 11 sesi, versi penerima paling banyak 1 sesi (selisih 10).")
    assert d["log"] == [] and d["transkrip"] == [] and d["rekaman"] is None and d["hapus_pada"] is None


def test_detail_riwayat_sesuai_punya_hapus_pada_30_hari(klien_v3):
    d = klien_v3.get("/api/v1/panggilan/CALL-LATAR-003").json()
    assert d["label"] == "sesuai" and d["saran"] == "tutup" and d["selisih"] == 0
    assert d["hapus_pada"] == "2026-11-04T10:32:06+07:00"


def test_detail_menurut_sesi_berjalan_menyembunyikan_hasil(klien_v3, conn_v3):
    ubah(conn_v3, S1, status="merekam", waktu_mulai=datetime(2026, 10, 6, 10, 12, 8, tzinfo=config.ZONA),
         transkrip=json.dumps([{"detik": 0, "pembicara": "ai", "teks": "Selamat siang"}]),
         tangkapan_sementara=json.dumps({"penerima": "peserta", "hadir": True}))
    conn_v3.execute("insert into panggilan_log (panggilan_id, status, waktu, percobaan) values (%s,'menelepon',%s,1)",
                    (S1, datetime(2026, 10, 6, 10, 12, tzinfo=config.ZONA)))
    d = klien_v3.get(f"/api/v1/panggilan/{S1}").json()
    assert d["waktu"] == "2026-10-06T10:12:08+07:00"
    assert d["transkrip"] == [{"detik": 0, "pembicara": "ai", "teks": "Selamat siang"}]
    assert d["tangkapan_sementara"] == {"penerima": "peserta", "hadir": True}
    assert d["log"] == [{"status": "menelepon", "waktu": "2026-10-06T10:12:00+07:00", "percobaan": 1, "catatan": None}]
    assert d["jawaban"] is None and d["label"] is None and d["rekaman"] is None


def test_detail_waktu_dari_log_bila_tidak_pernah_tersambung(klien_v3, conn_v3):
    conn_v3.execute("insert into panggilan_log (panggilan_id, status, waktu, percobaan, catatan) values (%s,'menelepon',%s,1,'tidak_diangkat')",
                    (S1, datetime(2026, 10, 6, 10, 20, tzinfo=config.ZONA)))
    assert klien_v3.get(f"/api/v1/panggilan/{S1}").json()["waktu"] == "2026-10-06T10:20:00+07:00"


def test_detail_tidak_terhubung_menyusun_jawaban_dan_chat_cadangan(klien_v3, conn_v3):
    ubah(conn_v3, "CALL-P-S5-2026-08", status="tidak_terhubung", label="Tidak terhubung", percobaan=2)
    d = klien_v3.get("/api/v1/panggilan/CALL-P-S5-2026-08").json()
    assert d["label"] == "tidak_terhubung" and d["saran"] == "pantau"
    assert d["jawaban"]["status_panggilan"] == "tidak_terhubung" and d["jawaban"]["ringkasan"] == "Panggilan tidak diangkat 2 kali."
    assert d["pesan_wa"]["cadangan"].startswith("Kami belum berhasil menelepon. Kira-kira berapa kali Joko Prasetyo")
    assert d["transkrip"] == [] and d["rekaman"] is None and d["selisih"] is None


def test_detail_rekaman_hanya_untuk_sesuai_dan_tidak_sesuai_sebelum_hapus_pada(klien_v3, conn_v3, monkeypatch):
    jam_palsu(monkeypatch)
    ubah(conn_v3, "CALL-LATAR-001", rekaman_path="rekaman/CALL-LATAR-001.webm")
    assert klien_v3.get("/api/v1/panggilan/CALL-LATAR-001").json()["rekaman"] == "/api/v1/panggilan/CALL-LATAR-001/rekaman"
    ubah(conn_v3, "CALL-LATAR-003", rekaman_path="rekaman/CALL-LATAR-003.webm")
    assert klien_v3.get("/api/v1/panggilan/CALL-LATAR-003").json()["rekaman"] is not None
    jam_palsu(monkeypatch, tahun=2026, bulan=12)  # lewat hapus_pada (4 Nov)
    d = klien_v3.get("/api/v1/panggilan/CALL-LATAR-003").json()
    assert d["rekaman"] is None and d["transkrip"] == []
    ubah(conn_v3, "CALL-P-S4-2026-08", status="selesai", label="Tidak yakin", rekaman_path="rekaman/x.webm")
    assert klien_v3.get("/api/v1/panggilan/CALL-P-S4-2026-08").json()["rekaman"] is None


def test_detail_konteks_rs_ikut_berubah(klien_v3, conn_v3):
    ubah(conn_v3, S1, status="selesai", label="Tidak sesuai")
    assert klien_v3.get(f"/api/v1/panggilan/{S1}").json()["konteks_rs"] == {
        "rs": "RS01", "tidak_sesuai": 3, "terjawab": 5, "status": "Perlu klarifikasi RS",
    }


def test_detail_tidak_ada(klien_v3):
    r = klien_v3.get("/api/v1/panggilan/CALL-NGAWUR")
    assert r.status_code == 404 and r.json() == {"galat": {"kode": "panggilan_tidak_ada", "pesan": "Panggilan tidak ditemukan."}}


# ---- GET /ringkasan-rs ----

def test_ringkasan_rs_awal_sama_dengan_expected(klien_v3):
    h = klien_v3.get("/api/v1/ringkasan-rs").json()
    harapan = json.loads((DATA / "expected_ringkasan_rs.json").read_text())
    assert h["aturan"] == harapan["aturan"] and h["bulan"] == "2026-08" and h["panggilan_selesai"] == 4
    assert [r["id_rs"] for r in h["rs"]] == ["RS01", "RS02", "RS03", "RS04", "RS05"]
    for r in h["rs"]:
        pemicu = harapan["pemicu_per_rs_2026-08"][r["id_rs"]]
        assert (r["aktif"], r["terpicu"], r["persen"]) == (pemicu["pasien_aktif"], pemicu["pasien_dipicu"], pemicu["persen_dipicu"])
        ada = harapan["sebelum_skenario"].get(r["id_rs"], {})
        for kunci in ("sesuai", "tidak_sesuai", "tidak_yakin", "tidak_terhubung", "menolak", "terjawab", "status"):
            assert r[kunci] == ada.get(kunci, "Normal" if kunci == "status" else 0), (r["id_rs"], kunci)
        assert r["rasio"] == ada.get("rasio_tidak_sesuai", 0.0)
    melati = h["rs"][0]
    assert [p["id"] for p in melati["panggilan"]] == ["CALL-LATAR-004", "CALL-LATAR-003", "CALL-LATAR-002", "CALL-LATAR-001"]
    assert melati["panggilan"][1] == {"id": "CALL-LATAR-003", "pasien": "Ani Siregar", "label": "sesuai", "ditagih": 9,
                                      "jumlah_min": 8, "jumlah_maks": 10, "selisih": 0}


def test_ringkasan_rs_setelah_semua_langkah_expected(klien_v3, conn_v3):
    """Setiap langkah di expected_ringkasan_rs.json: label diberikan lewat DB, status RS = hasil aturan.py."""
    harapan = json.loads((DATA / "expected_ringkasan_rs.json").read_text())
    skenario = {s["id_skenario"]: s for s in json.loads((DATA / "skenario_uji.json").read_text())}
    for langkah in harapan["langkah"]:
        sid = langkah["setelah"]
        s = skenario[sid]
        if s["expected_label"] is not None:
            ubah(conn_v3, f"CALL-{s['id_peserta']}-2026-08", status="selesai", label=s["expected_label"])
        h = klien_v3.get("/api/v1/ringkasan-rs").json()
        for id_rs, exp in langkah["ringkasan"].items():
            r = next(x for x in h["rs"] if x["id_rs"] == id_rs)
            assert {k: r[k] for k in ("sesuai", "tidak_sesuai", "tidak_yakin", "tidak_terhubung", "menolak", "terjawab", "status")} == {
                k: exp[k] for k in ("sesuai", "tidak_sesuai", "tidak_yakin", "tidak_terhubung", "menolak", "terjawab", "status")
            }, (sid, id_rs)


def test_ringkasan_rs_menjadi_perlu_klarifikasi_setelah_s1(klien_v3, conn_v3):
    ubah(conn_v3, S1, status="selesai", label="Tidak sesuai", waktu_selesai=datetime(2026, 10, 6, 10, 13, tzinfo=config.ZONA),
         jawaban=json.dumps({"status_panggilan": "terjawab", "jumlah_min": 3, "jumlah_maks": 3}))
    melati = klien_v3.get("/api/v1/ringkasan-rs").json()["rs"][0]
    assert (melati["tidak_sesuai"], melati["terjawab"], melati["status"], melati["rasio"]) == (3, 5, "Perlu klarifikasi RS", 0.6)
    assert melati["panggilan"][0] == {"id": S1, "pasien": "Andi Pratama", "label": "tidak_sesuai", "ditagih": 11,
                                      "jumlah_min": 3, "jumlah_maks": 3, "selisih": 8}
    assert klien_v3.get("/api/v1/antrean").json()["angka"]["rs_perlu_klarifikasi"] == 1


# ---- GET /keputusan, /pengaturan, /kesehatan ----

def test_keputusan_kosong_lalu_terkini_per_panggilan(klien_v3, conn_v3):
    assert klien_v3.get("/api/v1/keputusan").json() == []
    for tindakan, waktu in (("minta_klarifikasi_rs", 10), ("pantau", 11)):
        conn_v3.execute(
            "insert into keputusan_panggilan (panggilan_id, verifikator, tindakan, ikut_saran, alasan, waktu)"
            " values ('CALL-LATAR-001', 'R. Santoso', %s, %s, %s, %s)",
            (tindakan, tindakan == "minta_klarifikasi_rs", None if tindakan == "minta_klarifikasi_rs" else "Cek ulang.",
             datetime(2026, 10, 6, waktu, tzinfo=config.ZONA)),
        )
    h = klien_v3.get("/api/v1/keputusan").json()
    assert [(k["tindakan"], k["terkini"]) for k in h] == [("pantau", True), ("klarifikasi", False)]
    assert h[0]["pasien"] == "Bayu Utami" and h[0]["nama_rs"] == "RS Melati Sehat" and h[0]["label"] == "tidak_sesuai"
    assert h[0]["waktu"] == "2026-10-06T11:00:00+07:00"
    baris = {r["id"]: r for r in klien_v3.get("/api/v1/antrean").json()["baris"]}
    assert baris["CALL-LATAR-001"]["keputusan_tindakan"] == "pantau"
    assert klien_v3.get("/api/v1/antrean").json()["angka"]["menunggu_keputusan"] == 1
    assert klien_v3.get("/api/v1/panggilan/CALL-LATAR-001").json()["keputusan"]["tindakan"] == "pantau"


def test_pengaturan_baca(klien_v3):
    assert klien_v3.get("/api/v1/pengaturan").json() == {
        "mode_otomatis": False, "jeda": False, "jam_mulai": "09:00", "jam_selesai": "17:00",
        "jeda_wa_menit": 1, "jeda_percobaan_menit": 2,
    }


def test_kesehatan_memuat_pembaca_dan_versi_aturan(klien_v3):
    h = klien_v3.get("/api/v1/kesehatan").json()
    assert h == {"api": "ok", "db": "ok", "mesin": "ok", "pembaca": "ok", "versi_aturan": config.VERSI_ATURAN_V3}
