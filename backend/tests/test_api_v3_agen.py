"""Uji D-04: endpoint agen (Kontrak B1) dan pembacaan hasil (aturan percobaan, jeda, pembaca gagal, label)."""
import io
import json
from datetime import timedelta

import pytest

from app import config
from app.mesin import MesinGalat
from tests.util_v3 import jam_palsu, ubah, wib

DATA = config.AKAR / "data-uji-konfirmasi"
SKENARIO = {s["id_skenario"]: s for s in json.loads((DATA / "skenario_uji.json").read_text())}
S1 = "CALL-P-S1-2026-08"
BASE = "/api/v1"


def id_skenario(sid):
    return f"CALL-{SKENARIO[sid]['id_peserta']}-2026-08"


def nyalakan(klien, **kolom):
    return klien.put(f"{BASE}/pengaturan", json={"mode_otomatis": True, **kolom})


def lapor(klien, id_, laporan, **kw):
    return klien.post(f"{BASE}/panggilan/{id_}/status", json={"laporan": laporan, **kw})


def detail(klien, id_):
    return klien.get(f"{BASE}/panggilan/{id_}").json()


def baris_db(conn, id_):
    return conn.execute("select * from panggilan where id = %s", (id_,)).fetchone()


def log_db(conn, id_):
    return [(r["status"], r["percobaan"], r["catatan"]) for r in conn.execute(
        "select status, percobaan, catatan from panggilan_log where panggilan_id = %s order by waktu, id", (id_,))]


def sampai_merekam(klien, monkeypatch, id_=S1, menit=0):
    """Verifikator menekan Telepon sekarang, agen mengambil, melapor sampai merekam. Mengembalikan jam terakhir."""
    jam_palsu(monkeypatch, menit=menit)
    assert klien.post(f"{BASE}/panggilan/{id_}/mulai").status_code == 200
    assert klien.post(f"{BASE}/agen/ambil").json()["id"] == id_
    assert lapor(klien, id_, "wa_terkirim").status_code == 200
    jam_palsu(monkeypatch, menit=menit + 1, detik=5)
    assert lapor(klien, id_, "menelepon").status_code == 200
    assert lapor(klien, id_, "tersambung").status_code == 200
    assert lapor(klien, id_, "merekam").status_code == 200


def kirim_hasil(klien, id_=S1, transkrip=None, durasi=63, rekaman=b"suara-uji", nama="rekaman.webm", **kw):
    berkas = {"rekaman": (nama, io.BytesIO(rekaman), "audio/webm")} if rekaman is not None else None
    data = {"transkrip": json.dumps([] if transkrip is None else transkrip), "durasi": str(durasi)}
    return klien.post(f"{BASE}/panggilan/{id_}/hasil", data=data, files=berkas, **kw)


TRANSKRIP = [{"detik": 0, "pembicara": "ai", "teks": "Selamat siang."}, {"detik": 5, "pembicara": "penerima", "teks": "Iya."}]


# ---- kunci agen ----

@pytest.mark.parametrize("metode,path,kw", [
    ("post", f"{BASE}/agen/ambil", {}),
    ("post", f"{BASE}/panggilan/{S1}/status", {"json": {"laporan": "wa_terkirim"}}),
    ("post", f"{BASE}/panggilan/{S1}/transkrip", {"json": {"baris": []}}),
    ("post", f"{BASE}/panggilan/{S1}/hasil", {"data": {"transkrip": "[]", "durasi": "1"}}),
])
def test_endpoint_agen_menolak_kunci_kosong_atau_salah(klien_agen, metode, path, kw):
    for kunci in ("", "salah"):
        r = klien_agen.request(metode, path, headers={"X-Kunci-Agen": kunci}, **kw)
        assert r.status_code == 401 and r.json() == {"galat": {"kode": "kunci_salah", "pesan": "Header X-Kunci-Agen kosong atau salah."}}


def test_tanpa_agen_key_di_env_semua_ditolak(klien_agen, monkeypatch):
    monkeypatch.delenv("AGEN_KEY")
    assert klien_agen.post(f"{BASE}/agen/ambil").status_code == 401


def test_endpoint_fe_tidak_butuh_kunci_agen(klien_agen):
    assert klien_agen.get(f"{BASE}/antrean", headers={"X-Kunci-Agen": ""}).status_code == 200


# ---- agen/ambil ----

def test_ambil_204_selama_mode_mati(klien_agen, monkeypatch):
    jam_palsu(monkeypatch)
    assert klien_agen.post(f"{BASE}/agen/ambil").status_code == 204


def test_ambil_tugas_s1_bentuk_kontrak(klien_agen, conn_v3, monkeypatch):
    jam_palsu(monkeypatch)
    nyalakan(klien_agen)
    r = klien_agen.post(f"{BASE}/agen/ambil")
    assert r.status_code == 200
    t = r.json()
    teks = detail(klien_agen, S1)["pesan_wa"]["pemberitahuan"]
    assert t == {
        "id": S1, "percobaan": 1, "no_tujuan": "081234567890",
        "skrip": {"nama_penerima": "Andi Pratama", "sapaan_penerima": "Bapak", "hubungan": "peserta",
                  "nama_pasien": "Andi Pratama", "sapaan_pasien": "Bapak", "nama_rs": "RS Melati Sehat", "bulan": "Agustus",
                  "tanggal_libur": ["16 Agustus", "17 Agustus"]},
        "wa": {"lewati": False, "teks": teks, "tautan": t["wa"]["tautan"]},
        "jeda_wa_menit": 1, "batas_detik": 150,
    }
    assert t["wa"]["tautan"].startswith("https://wa.me/6281234567890?text=Halo%20Andi%20Pratama.")
    assert "http" not in teks
    b = baris_db(conn_v3, S1)
    assert b["no_tujuan"] == "081234567890" and b["jeda_wa_menit"] == 1 and b["diambil_pada"] is not None
    assert b["status"] == "antre" and b["percobaan"] == 0  # naik saat agen melapor 'menelepon'


def test_ambil_tugas_keluarga_dan_tanpa_libur(klien_agen, conn_v3, monkeypatch):
    jam_palsu(monkeypatch)
    klien_agen.post(f"{BASE}/panggilan/{id_skenario('S2')}/mulai")
    t = klien_agen.post(f"{BASE}/agen/ambil").json()
    assert t["skrip"] == {"nama_penerima": "Dewi Rahmawati", "sapaan_penerima": "Bapak/Ibu", "hubungan": "anak",
                          "nama_pasien": "Siti Rahmawati", "sapaan_pasien": "Ibu", "nama_rs": "RS Melati Sehat",
                          "bulan": "Agustus", "tanggal_libur": ["23 Agustus"]}
    assert lapor(klien_agen, t["id"], "wa_terkirim").status_code == 200
    ubah(conn_v3, t["id"], status="selesai", label="Sesuai")
    klien_agen.post(f"{BASE}/panggilan/{id_skenario('S3')}/mulai")
    t3 = klien_agen.post(f"{BASE}/agen/ambil").json()
    assert t3["id"] == id_skenario("S3") and t3["skrip"]["tanggal_libur"] == []  # I4 tidak aktif: agen tidak bertanya libur


def test_ambil_mengikuti_urutan_antrean_dan_satu_panggilan_aktif(klien_agen, conn_v3, monkeypatch):
    jam_palsu(monkeypatch)
    nyalakan(klien_agen)
    assert klien_agen.post(f"{BASE}/agen/ambil").json()["id"] == S1
    assert klien_agen.post(f"{BASE}/agen/ambil").status_code == 204  # S1 terkunci, satu panggilan aktif
    ubah(conn_v3, S1, status="selesai", label="Sesuai", diambil_pada=None)
    assert klien_agen.post(f"{BASE}/agen/ambil").json()["id"] == id_skenario("S2")


def test_ambil_menolak_bila_ada_panggilan_berjalan(klien_agen, conn_v3, monkeypatch):
    jam_palsu(monkeypatch)
    nyalakan(klien_agen)
    for status in ("wa_terkirim", "menelepon", "tersambung", "merekam", "membaca_jawaban"):
        ubah(conn_v3, S1, status=status)
        assert klien_agen.post(f"{BASE}/agen/ambil").status_code == 204, status
    ubah(conn_v3, S1, status="selesai", label="Sesuai")
    assert klien_agen.post(f"{BASE}/agen/ambil").status_code == 200


def test_kunci_ambil_lepas_setelah_lima_menit(klien_agen, monkeypatch):
    jam_palsu(monkeypatch, menit=0)
    nyalakan(klien_agen)
    assert klien_agen.post(f"{BASE}/agen/ambil").json()["id"] == S1
    jam_palsu(monkeypatch, menit=4, detik=59)
    assert klien_agen.post(f"{BASE}/agen/ambil").status_code == 204
    jam_palsu(monkeypatch, menit=5, detik=1)
    assert klien_agen.post(f"{BASE}/agen/ambil").json()["id"] == S1  # agen tidak melapor: tugas dilepas


@pytest.mark.parametrize("jam_,menit,boleh", [(8, 59, False), (9, 0, True), (16, 59, True), (17, 0, False), (23, 0, False)])
def test_ambil_hanya_dalam_jam_kerja_termasuk_prioritas(klien_agen, monkeypatch, jam_, menit, boleh):
    jam_palsu(monkeypatch, jam_=jam_, menit=menit)
    nyalakan(klien_agen)
    klien_agen.post(f"{BASE}/panggilan/CALL-P-S3-2026-08/mulai")
    assert (klien_agen.post(f"{BASE}/agen/ambil").status_code == 200) is boleh


def test_ambil_jeda_menahan_otomatis_tetapi_prioritas_tetap_jalan(klien_agen, monkeypatch):
    jam_palsu(monkeypatch)
    nyalakan(klien_agen)
    klien_agen.put(f"{BASE}/pengaturan", json={"jeda": True})
    assert klien_agen.post(f"{BASE}/agen/ambil").status_code == 204
    klien_agen.post(f"{BASE}/panggilan/CALL-P-S6-2026-08/mulai")
    assert klien_agen.post(f"{BASE}/agen/ambil").json()["id"] == "CALL-P-S6-2026-08"


def test_ambil_prioritas_walau_mode_mati_dan_mendahului_urutan(klien_agen, monkeypatch):
    jam_palsu(monkeypatch)
    klien_agen.post(f"{BASE}/panggilan/CALL-P-S8-2026-08/mulai")
    assert klien_agen.post(f"{BASE}/agen/ambil").json()["id"] == "CALL-P-S8-2026-08"


# ---- status: urutan, jeda WA, tidak diangkat ----

def test_alur_status_normal_menulis_log_dan_waktu(klien_agen, conn_v3, monkeypatch):
    sampai_merekam(klien_agen, monkeypatch)
    b = baris_db(conn_v3, S1)
    assert (b["status"], b["percobaan"]) == ("merekam", 1)
    assert b["waktu_wa"] == wib(2026, 10, 6, 10, 0, 0) and b["waktu_mulai"] == wib(2026, 10, 6, 10, 1, 5)
    assert log_db(conn_v3, S1) == [("wa_terkirim", 1, None), ("menelepon", 1, None), ("tersambung", 1, None), ("merekam", 1, None)]
    d = detail(klien_agen, S1)
    assert d["waktu"] == "2026-10-06T10:01:05+07:00" and d["status"] == "merekam"


def test_balasan_status_bentuk_kontrak(klien_agen, monkeypatch):
    jam_palsu(monkeypatch)
    klien_agen.post(f"{BASE}/panggilan/{S1}/mulai")
    klien_agen.post(f"{BASE}/agen/ambil")
    assert lapor(klien_agen, S1, "wa_terkirim").json() == {"status": "wa_terkirim", "percobaan": 0, "coba_lagi_setelah": None, "chat_cadangan": None}
    jam_palsu(monkeypatch, menit=1)
    assert lapor(klien_agen, S1, "menelepon").json() == {"status": "menelepon", "percobaan": 1, "coba_lagi_setelah": None, "chat_cadangan": None}


def test_jeda_wa_belum_lewat_ditolak(klien_agen, conn_v3, monkeypatch):
    jam_palsu(monkeypatch)
    klien_agen.post(f"{BASE}/panggilan/{S1}/mulai")
    klien_agen.post(f"{BASE}/agen/ambil")
    lapor(klien_agen, S1, "wa_terkirim")
    jam_palsu(monkeypatch, detik=59)
    r = lapor(klien_agen, S1, "menelepon")
    assert r.status_code == 409 and r.json()["galat"]["kode"] == "jeda_belum_lewat"
    assert baris_db(conn_v3, S1)["status"] == "wa_terkirim" and len(log_db(conn_v3, S1)) == 1
    jam_palsu(monkeypatch, menit=1)
    assert lapor(klien_agen, S1, "menelepon").status_code == 200


def test_jeda_wa_mengikuti_pengaturan_saat_tugas_diambil(klien_agen, monkeypatch):
    jam_palsu(monkeypatch)
    klien_agen.put(f"{BASE}/pengaturan", json={"jeda_wa_menit": 3})
    klien_agen.post(f"{BASE}/panggilan/{S1}/mulai")
    assert klien_agen.post(f"{BASE}/agen/ambil").json()["jeda_wa_menit"] == 3
    lapor(klien_agen, S1, "wa_terkirim")
    jam_palsu(monkeypatch, menit=2, detik=59)
    assert lapor(klien_agen, S1, "menelepon").status_code == 409
    jam_palsu(monkeypatch, menit=3)
    assert lapor(klien_agen, S1, "menelepon").status_code == 200


@pytest.mark.parametrize("urutan", [
    ["menelepon"], ["tersambung"], ["merekam"], ["tidak_diangkat"], ["chat_cadangan_terkirim"],
    ["wa_terkirim", "wa_terkirim"], ["wa_terkirim", "tersambung"], ["wa_terkirim", "merekam"],
])
def test_urutan_salah_ditolak(klien_agen, conn_v3, monkeypatch, urutan):
    jam_palsu(monkeypatch)
    klien_agen.post(f"{BASE}/panggilan/{S1}/mulai")
    klien_agen.post(f"{BASE}/agen/ambil")
    for laporan in urutan[:-1]:
        assert lapor(klien_agen, S1, laporan).status_code == 200
    r = lapor(klien_agen, S1, urutan[-1])
    assert r.status_code == 409 and r.json()["galat"]["kode"] == "urutan_salah"


def test_urutan_salah_setelah_tersambung_dan_laporan_tak_dikenal_dan_404(klien_agen, monkeypatch):
    sampai_merekam(klien_agen, monkeypatch)
    for laporan in ("wa_terkirim", "menelepon", "tersambung", "merekam", "tidak_diangkat"):
        assert lapor(klien_agen, S1, laporan).json()["galat"]["kode"] == "urutan_salah", laporan
    r = lapor(klien_agen, S1, "ngawur")
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "laporan_tidak_dikenal"
    r = lapor(klien_agen, "CALL-NGAWUR", "wa_terkirim")
    assert r.status_code == 404 and r.json()["galat"]["kode"] == "panggilan_tidak_ada"
    assert klien_agen.post(f"{BASE}/panggilan/{S1}/status", json={}).json()["galat"]["kode"] == "validasi"


def test_waktu_dari_agen_dipakai_di_log(klien_agen, conn_v3, monkeypatch):
    jam_palsu(monkeypatch)
    klien_agen.post(f"{BASE}/panggilan/{S1}/mulai")
    klien_agen.post(f"{BASE}/agen/ambil")
    lapor(klien_agen, S1, "wa_terkirim", waktu="2026-10-06T10:11:00+07:00", catatan="dikirim manual")
    assert conn_v3.execute("select waktu, catatan from panggilan_log where panggilan_id = %s", (S1,)).fetchone() == {
        "waktu": wib(2026, 10, 6, 10, 11), "catatan": "dikirim manual"}
    assert baris_db(conn_v3, S1)["waktu_wa"] == wib(2026, 10, 6, 10, 11)


S5 = "CALL-P-S5-2026-08"


def test_s5_tidak_diangkat_dua_kali_lalu_chat_cadangan(klien_agen, conn_v3, monkeypatch):
    jam_palsu(monkeypatch, menit=0)
    klien_agen.post(f"{BASE}/panggilan/{S5}/mulai")
    assert klien_agen.post(f"{BASE}/agen/ambil").json()["percobaan"] == 1
    lapor(klien_agen, S5, "wa_terkirim")
    jam_palsu(monkeypatch, menit=1)
    lapor(klien_agen, S5, "menelepon")
    r = lapor(klien_agen, S5, "tidak_diangkat").json()
    assert r == {"status": "antre", "percobaan": 1, "coba_lagi_setelah": "2026-10-06T10:03:00+07:00", "chat_cadangan": None}
    b = baris_db(conn_v3, S5)
    assert (b["status"], b["percobaan"], b["diambil_pada"], b["label"]) == ("antre", 1, None, None)

    jam_palsu(monkeypatch, menit=2, detik=59)
    assert klien_agen.post(f"{BASE}/agen/ambil").status_code == 204  # jeda percobaan belum lewat
    jam_palsu(monkeypatch, menit=3)
    t = klien_agen.post(f"{BASE}/agen/ambil").json()
    assert t["id"] == S5 and t["percobaan"] == 2 and t["wa"]["lewati"] is True
    assert t["wa"]["teks"].startswith("Halo Joko Prasetyo.") and t["wa"]["tautan"].startswith("https://wa.me/")

    assert lapor(klien_agen, S5, "wa_terkirim").json()["galat"]["kode"] == "urutan_salah"  # WA dilewati
    assert lapor(klien_agen, S5, "menelepon").json() == {"status": "menelepon", "percobaan": 2, "coba_lagi_setelah": None, "chat_cadangan": None}
    r = lapor(klien_agen, S5, "tidak_diangkat").json()
    assert r["status"] == "tidak_terhubung" and r["percobaan"] == 2 and r["coba_lagi_setelah"] is None
    assert r["chat_cadangan"]["teks"].startswith("Kami belum berhasil menelepon. Kira-kira berapa kali Joko Prasetyo")
    assert r["chat_cadangan"]["tautan"].startswith("https://wa.me/6281234567890?text=Kami%20belum%20berhasil")
    b = baris_db(conn_v3, S5)
    assert (b["status"], b["label"], b["alasan"]) == ("tidak_terhubung", "Tidak terhubung", "Panggilan tidak diangkat setelah 2 kali percobaan.")
    assert b["jawaban"]["status_panggilan"] == "tidak_terhubung" and b["waktu_selesai"] is not None and b["hapus_pada"] is None

    assert lapor(klien_agen, S5, "chat_cadangan_terkirim").status_code == 200
    assert baris_db(conn_v3, S5)["chat_cadangan_terkirim"] is True
    assert log_db(conn_v3, S5) == [
        ("wa_terkirim", 1, None), ("menelepon", 1, None), ("menelepon", 1, "tidak_diangkat"),
        ("menelepon", 2, None), ("menelepon", 2, "tidak_diangkat"), ("tidak_terhubung", 2, "chat_cadangan_terkirim"),
    ]
    d = detail(klien_agen, S5)
    assert d["label"] == "tidak_terhubung" and d["saran"] == "pantau" and d["pesan_wa"]["cadangan"] is not None
    assert d["waktu"] == "2026-10-06T10:01:00+07:00"  # tidak pernah tersambung: waktu 'menelepon' pertama
    ringkas = klien_agen.get(f"{BASE}/ringkasan-rs").json()
    rs03 = next(r for r in ringkas["rs"] if r["id_rs"] == "RS03")
    assert (rs03["tidak_terhubung"], rs03["terjawab"], rs03["status"]) == (1, 0, "Normal")  # tidak dihitung
    assert klien_agen.post(f"{BASE}/agen/ambil").status_code == 204  # tidak antre lagi


def test_jeda_percobaan_mengikuti_pengaturan(klien_agen, monkeypatch):
    jam_palsu(monkeypatch)
    klien_agen.put(f"{BASE}/pengaturan", json={"jeda_percobaan_menit": 10})
    klien_agen.post(f"{BASE}/panggilan/{S5}/mulai")
    klien_agen.post(f"{BASE}/agen/ambil")
    lapor(klien_agen, S5, "wa_terkirim")
    jam_palsu(monkeypatch, menit=1)
    lapor(klien_agen, S5, "menelepon")
    assert lapor(klien_agen, S5, "tidak_diangkat").json()["coba_lagi_setelah"] == "2026-10-06T10:11:00+07:00"


# ---- transkrip ----

def test_transkrip_ditolak_sebelum_tersambung(klien_agen, monkeypatch):
    jam_palsu(monkeypatch)
    klien_agen.post(f"{BASE}/panggilan/{S1}/mulai")
    klien_agen.post(f"{BASE}/agen/ambil")
    r = klien_agen.post(f"{BASE}/panggilan/{S1}/transkrip", json={"baris": TRANSKRIP})
    assert r.status_code == 409 and r.json()["galat"]["kode"] == "bukan_berlangsung"
    assert klien_agen.post(f"{BASE}/panggilan/CALL-NGAWUR/transkrip", json={"baris": []}).status_code == 404


def test_transkrip_ditambahkan_dan_tangkapan_diganti(klien_agen, monkeypatch):
    sampai_merekam(klien_agen, monkeypatch)
    r = klien_agen.post(f"{BASE}/panggilan/{S1}/transkrip", json={"baris": TRANSKRIP[:1]})
    assert r.status_code == 204 and r.content == b""
    assert detail(klien_agen, S1)["tangkapan_sementara"] is None
    klien_agen.post(f"{BASE}/panggilan/{S1}/transkrip", json={
        "baris": TRANSKRIP[1:], "tangkapan_sementara": {"penerima": "peserta", "hadir": True, "label": "sesuai", "ngawur": 1}})
    d = detail(klien_agen, S1)
    assert d["transkrip"] == TRANSKRIP
    assert d["tangkapan_sementara"] == {"penerima": "peserta", "hadir": True}  # field di luar skema dibuang, label tak pernah masuk
    klien_agen.post(f"{BASE}/panggilan/{S1}/transkrip", json={"baris": [], "tangkapan_sementara": {"jumlah_min": 3, "jumlah_maks": 3}})
    assert detail(klien_agen, S1)["tangkapan_sementara"] == {"jumlah_min": 3, "jumlah_maks": 3}
    klien_agen.post(f"{BASE}/panggilan/{S1}/transkrip", json={"baris": []})
    assert detail(klien_agen, S1)["tangkapan_sementara"] == {"jumlah_min": 3, "jumlah_maks": 3}  # tanpa kiriman: tidak berubah


@pytest.mark.parametrize("baris", [
    [{"detik": 1, "pembicara": "robot", "teks": "x"}], [{"detik": -1, "pembicara": "ai", "teks": "x"}],
])
def test_transkrip_baris_tidak_valid(klien_agen, monkeypatch, baris):
    sampai_merekam(klien_agen, monkeypatch)
    r = klien_agen.post(f"{BASE}/panggilan/{S1}/transkrip", json={"baris": baris})
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "transkrip_tidak_valid"
    assert klien_agen.post(f"{BASE}/panggilan/{S1}/transkrip", json={"baris": [{"detik": 1}]}).json()["galat"]["kode"] == "validasi"


# ---- hasil + label ----

def jawaban_skenario(sid):
    return {**SKENARIO[sid]["expected_jawaban"], "versi_pembaca": "pembaca-uji"}


def test_hasil_s1_sampai_kartu_bukti_dan_rs_melati_perlu_klarifikasi(klien_agen, conn_v3, pembaca, tmp_path, monkeypatch):
    pembaca.balasan = [jawaban_skenario("S1")]
    sampai_merekam(klien_agen, monkeypatch)
    jam_palsu(monkeypatch, menit=3)
    r = kirim_hasil(klien_agen, transkrip=TRANSKRIP, durasi=63, rekaman=b"suara-s1")
    assert r.status_code == 202 and r.json() == {"status": "membaca_jawaban"}
    b = baris_db(conn_v3, S1)
    assert (b["status"], b["label"], b["alasan"]) == ("selesai", "Tidak sesuai", SKENARIO["S1"]["expected_alasan"])
    assert b["jawaban"]["jumlah_maks"] == 3 and b["jawaban"]["versi_pembaca"] == "pembaca-uji"
    assert b["durasi_detik"] == 63 and b["waktu_selesai"] == wib(2026, 10, 6, 10, 3) and b["hapus_pada"] is None
    assert b["transkrip"] == [{"detik": 0.0, "pembicara": "ai", "teks": "Selamat siang."}, {"detik": 5.0, "pembicara": "penerima", "teks": "Iya."}]
    assert b["rekaman_path"] == f"rekaman/{S1}.webm" and (tmp_path / b["rekaman_path"]).read_bytes() == b"suara-s1"
    assert b["tangkapan_sementara"] is None and b["galat_pembaca"] is None
    assert [x[0] for x in log_db(conn_v3, S1)][-2:] == ["membaca_jawaban", "selesai"]
    # permintaan ke pembaca (Kontrak B2)
    assert pembaca.permintaan == [{
        "id": S1, "transkrip": b["transkrip"],
        "konteks": {"sesi_ditagih": 11, "tanggal_libur": ["2026-08-16", "2026-08-17"], "nama_pasien": "Andi Pratama", "bulan": "2026-08"},
    }]
    # kartu bukti
    d = detail(klien_agen, S1)
    assert (d["label"], d["selisih"], d["saran"], d["status"], d["durasi"]) == ("tidak_sesuai", 8, "klarifikasi", "selesai", 63)
    assert d["rekaman"] == f"/api/v1/panggilan/{S1}/rekaman" and d["transkrip"] == b["transkrip"]
    assert d["konteks_rs"] == {"rs": "RS01", "tidak_sesuai": 3, "terjawab": 5, "status": "Perlu klarifikasi RS"}
    assert klien_agen.get(d["rekaman"]).content == b"suara-s1"
    melati = klien_agen.get(f"{BASE}/ringkasan-rs").json()["rs"][0]
    assert (melati["status"], melati["tidak_sesuai"], melati["terjawab"]) == ("Perlu klarifikasi RS", 3, 5)
    assert klien_agen.get(f"{BASE}/antrean").json()["angka"]["rs_perlu_klarifikasi"] == 1
    assert klien_agen.post(f"{BASE}/panggilan/{S1}/keputusan", json={"ikut_saran": True}).status_code == 201


@pytest.mark.parametrize("sid", ["S1", "S2", "S3", "S4", "S6", "S8"])
def test_label_dan_retensi_per_skenario(klien_agen, conn_v3, pembaca, tmp_path, monkeypatch, sid):
    """Pembaca palsu menjawab expected_jawaban; label, alasan, dan retensi dihitung API (aturan.py, R5.5)."""
    id_ = id_skenario(sid)
    pembaca.balasan = [SKENARIO[sid]["expected_jawaban"]]
    sampai_merekam(klien_agen, monkeypatch, id_)
    jam_palsu(monkeypatch, menit=3)
    assert kirim_hasil(klien_agen, id_, transkrip=TRANSKRIP, rekaman=b"suara").status_code == 202
    b = baris_db(conn_v3, id_)
    assert b["status"] == "selesai" and b["label"] == SKENARIO[sid]["expected_label"]
    assert b["alasan"] == SKENARIO[sid]["expected_alasan"]
    simpan = SKENARIO[sid]["expected_bukti"]["simpan_rekaman"]
    assert (b["rekaman_path"] is not None) is simpan and (b["transkrip"] is not None) is simpan
    assert (tmp_path / f"rekaman/{id_}.webm").exists() is simpan
    if b["label"] == "Sesuai":
        assert b["hapus_pada"] == b["waktu_selesai"] + timedelta(days=30)
    else:
        assert b["hapus_pada"] is None
    d = detail(klien_agen, id_)
    assert (d["rekaman"] is not None) is simpan and (d["transkrip"] != []) is simpan


def test_hasil_tanpa_rekaman_sah_untuk_penolakan(klien_agen, conn_v3, pembaca, monkeypatch):
    pembaca.balasan = [SKENARIO["S8"]["expected_jawaban"]]
    id_ = id_skenario("S8")
    sampai_merekam(klien_agen, monkeypatch, id_)
    assert kirim_hasil(klien_agen, id_, rekaman=None).status_code == 202
    b = baris_db(conn_v3, id_)
    assert (b["label"], b["rekaman_path"]) == ("Menolak", None)


def test_ekstensi_rekaman_mp3_dari_stub_agen_dipertahankan(klien_agen, conn_v3, pembaca, tmp_path, monkeypatch):
    pembaca.balasan = [jawaban_skenario("S1")]
    sampai_merekam(klien_agen, monkeypatch)
    kirim_hasil(klien_agen, nama="S1.mp3", rekaman=b"mp3")
    assert baris_db(conn_v3, S1)["rekaman_path"] == f"rekaman/{S1}.mp3" and (tmp_path / f"rekaman/{S1}.mp3").exists()


# ---- pembaca gagal: ulang 1 kali, lalu Tidak yakin ----

def hasil_gagal(klien_agen, conn_v3, pembaca, monkeypatch, *balasan):
    pembaca.balasan = list(balasan)
    sampai_merekam(klien_agen, monkeypatch)
    assert kirim_hasil(klien_agen, transkrip=TRANSKRIP).status_code == 202
    return baris_db(conn_v3, S1)


@pytest.mark.parametrize("galat", [
    MesinGalat("llm_gagal", "LLM gagal.", 502), MesinGalat("batas_waktu", "Terlalu lama.", 504),
    MesinGalat("mesin_tidak_tersedia", "Mesin tidak bisa dihubungi (ConnectError)."),
])
def test_pembaca_gagal_dua_kali_label_tidak_yakin(klien_agen, conn_v3, pembaca, tmp_path, monkeypatch, galat):
    b = hasil_gagal(klien_agen, conn_v3, pembaca, monkeypatch, galat)
    assert len(pembaca.permintaan) == 2  # diulang 1 kali
    assert (b["status"], b["label"]) == ("selesai", "Tidak yakin") and b["alasan"].startswith("Jawaban belum bisa dibaca otomatis")
    assert galat.kode in b["galat_pembaca"]
    assert b["jawaban"]["status_panggilan"] == "terjawab" and b["jawaban"]["jumlah_maks"] is None
    assert b["rekaman_path"] is None and b["transkrip"] is None and not (tmp_path / f"rekaman/{S1}.webm").exists()  # R5.5
    d = detail(klien_agen, S1)
    assert d["label"] == "tidak_yakin" and d["saran"] == "pantau" and d["rekaman"] is None and d["galat_pembaca"] == b["galat_pembaca"]
    ringkas = klien_agen.get(f"{BASE}/ringkasan-rs").json()["rs"][0]
    assert (ringkas["tidak_yakin"], ringkas["terjawab"], ringkas["status"]) == (1, 4, "Normal")  # tidak dihitung


def test_pembaca_gagal_sekali_lalu_berhasil(klien_agen, conn_v3, pembaca, monkeypatch):
    b = hasil_gagal(klien_agen, conn_v3, pembaca, monkeypatch, MesinGalat("batas_waktu", "x", 504), jawaban_skenario("S1"))
    assert len(pembaca.permintaan) == 2
    assert b["label"] == "Tidak sesuai" and b["galat_pembaca"] is None


def test_pembaca_json_tidak_lolos_skema_diulang_lalu_tidak_yakin(klien_agen, conn_v3, pembaca, monkeypatch):
    rusak = {**jawaban_skenario("S1"), "status_panggilan": "ngawur"}
    b = hasil_gagal(klien_agen, conn_v3, pembaca, monkeypatch, rusak)
    assert len(pembaca.permintaan) == 2 and b["label"] == "Tidak yakin" and b["galat_pembaca"].startswith("skema_tidak_valid")


@pytest.mark.parametrize("rusak", [
    ["bukan", "objek"], {"status_panggilan": "terjawab", "tanda_bahaya": ["menipu"]},
    {"status_panggilan": "terjawab", "keyakinan": "sedang"}, {"status_panggilan": "terjawab", "jumlah_maks": "3"},
    {"status_panggilan": "terjawab", "jumlah_maks": -1}, {"status_panggilan": "terjawab", "penerima": "tetangga"},
])
def test_skema_pembaca_menolak_bentuk_salah(rusak):
    from app import agen
    assert agen.lolos_skema(rusak) is not None
    assert agen.lolos_skema(SKENARIO["S1"]["expected_jawaban"]) is None
    assert all(agen.lolos_skema(s["expected_jawaban"]) is None for s in SKENARIO.values() if s["expected_label"])


def test_transkrip_kosong_dari_pembaca_tidak_diulang(klien_agen, conn_v3, pembaca, monkeypatch):
    b = hasil_gagal(klien_agen, conn_v3, pembaca, monkeypatch, MesinGalat("transkrip_kosong", "Kosong.", 422))
    assert len(pembaca.permintaan) == 1 and b["label"] == "Tidak yakin" and "transkrip_kosong" in b["galat_pembaca"]


def test_galat_tak_terduga_di_pemrosesan_tetap_berakhir_tidak_yakin(klien_agen, conn_v3, pembaca, monkeypatch):
    b = hasil_gagal(klien_agen, conn_v3, pembaca, monkeypatch, RuntimeError("meledak"))
    assert (b["status"], b["label"]) == ("selesai", "Tidak yakin") and b["galat_pembaca"] == "galat_internal: RuntimeError"


# ---- hasil: galat permintaan ----

def test_hasil_ditolak_bila_belum_berlangsung(klien_agen, conn_v3, monkeypatch):
    jam_palsu(monkeypatch)
    r = kirim_hasil(klien_agen)
    assert r.status_code == 409 and r.json()["galat"]["kode"] == "bukan_berlangsung"
    assert kirim_hasil(klien_agen, "CALL-NGAWUR").status_code == 404
    assert baris_db(conn_v3, S1)["status"] == "antre"


@pytest.mark.parametrize("transkrip", ["bukan json", '{"a": 1}', '[{"detik": 1}]', '[{"detik": 1, "pembicara": "robot", "teks": "x"}]', "[1, 2]"])
def test_hasil_transkrip_tidak_valid(klien_agen, conn_v3, monkeypatch, transkrip):
    sampai_merekam(klien_agen, monkeypatch)
    r = klien_agen.post(f"{BASE}/panggilan/{S1}/hasil", data={"transkrip": transkrip, "durasi": "5"})
    assert r.status_code == 422 and r.json()["galat"]["kode"] == "transkrip_tidak_valid"
    assert baris_db(conn_v3, S1)["status"] == "merekam"


def test_hasil_rekaman_terlalu_besar(klien_agen, conn_v3, tmp_path, monkeypatch):
    sampai_merekam(klien_agen, monkeypatch)
    r = kirim_hasil(klien_agen, rekaman=b"x" * (10 * 1024 * 1024 + 1))
    assert r.status_code == 413 and r.json()["galat"]["kode"] == "terlalu_besar"
    assert baris_db(conn_v3, S1)["status"] == "merekam" and not (tmp_path / "rekaman").exists()


def test_hasil_durasi_wajib_bilangan_bulat_tak_negatif(klien_agen, monkeypatch):
    sampai_merekam(klien_agen, monkeypatch)
    for durasi in ("-1", "abc"):
        r = klien_agen.post(f"{BASE}/panggilan/{S1}/hasil", data={"transkrip": "[]", "durasi": durasi})
        assert r.status_code == 422 and r.json()["galat"]["kode"] == "validasi"
