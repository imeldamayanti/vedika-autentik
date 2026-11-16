"""Uji seed v3: konversi baris, penentuan penerima (R1.3), hapus_pada (R5.5), antrean (tanpa database),
dan skor pola yang tersimpan (schema sementara uji3)."""
import json
from datetime import timedelta

import pytest

from app import pola_v3
from scripts import seed_v3

SKOR_DEMO = json.loads((seed_v3.DATA / "referensi-pola" / "skor_demo.json").read_text(encoding="utf-8"))

WAKTU = seed_v3.JADWAL_RIWAYAT["CALL-LATAR-001"][0]


def peserta(**ubah):
    r = {
        "id_peserta": "P-X", "nama": "Uji Satu", "tanggal_lahir": "1970-01-01", "umur": "56", "jenis_kelamin": "L",
        "no_hp": "0800-0000-0001", "kontak_keluarga": "", "hubungan_keluarga": "", "no_hp_keluarga": "",
        "hubungi_keluarga": "tidak", "catatan": "",
    }
    r.update(ubah)
    return r


@pytest.fixture(scope="module")
def data():
    return seed_v3.muat_data()


def test_baris_peserta_kosong_jadi_none_dan_ya_jadi_bool():
    b = seed_v3.baris_peserta(peserta(tanggal_lahir="", hubungi_keluarga="ya", kontak_keluarga="Wali Uji"))
    assert b[2] is None and b[3] == 56
    assert b[6] == "Wali Uji" and b[7] is None
    assert b[9] is True and b[10] is None


def test_baris_klaim_tarif_jadi_int():
    r = {"id_klaim": "K1", "id_peserta": "P-X", "id_rs": "RS01", "tanggal": "2026-08-03", "kode_cbg": "A",
         "kode_icd10": "M54", "diagnosis": "Uji", "tarif": "250000"}
    assert seed_v3.baris_klaim(r) == ("K1", "P-X", "RS01", "2026-08-03", "A", "M54", "Uji", 250000)


def test_penerima_keluarga_jika_hubungi_keluarga_ya():
    pes = peserta(hubungi_keluarga="ya", kontak_keluarga="Wali Uji", hubungan_keluarga="anak")
    assert seed_v3.tentukan_penerima(pes) == ("keluarga", "Wali Uji", "anak")


def test_penerima_peserta_jika_tidak_hubungi_keluarga():
    assert seed_v3.tentukan_penerima(peserta()) == ("peserta", "Uji Satu", None)


def test_penerima_peserta_jika_keluarga_tanpa_kontak():
    assert seed_v3.tentukan_penerima(peserta(hubungi_keluarga="ya"))[0] == "peserta"


@pytest.mark.parametrize("label", ["Tidak sesuai", "Tidak yakin", "Tidak terhubung", "Menolak"])
def test_hapus_pada_kosong_selain_sesuai(label):
    assert seed_v3.hapus_pada(label, WAKTU) is None


def test_hapus_pada_sesuai_30_hari():
    assert seed_v3.hapus_pada("Sesuai", WAKTU) == WAKTU + timedelta(days=30)


def test_id_panggilan_mudah_dibaca():
    assert seed_v3.id_panggilan("P-S1", "2026-08") == "CALL-P-S1-2026-08"


def test_baris_antre_dari_indikator():
    h = {"id_peserta": "P-X", "id_rs": "RS01", "bulan": "2026-08", "sesi_ditagih": 10}
    b = seed_v3.baris_antre(h, peserta(hubungi_keluarga="ya", kontak_keluarga="Wali Uji", hubungan_keluarga="anak"))
    assert b[:9] == ("CALL-P-X-2026-08", "P-X", "RS01", "2026-08", 10, "keluarga", "Wali Uji", "anak", "antre")
    assert b[9] == 0 and b[10:16] == (None,) * 6 and b[17] is None


def test_baris_riwayat_selesai_dengan_retensi_per_label(data):
    for p in data["riwayat"]:
        b = seed_v3.baris_panggilan(p, data["peta_peserta"])
        mulai, durasi = seed_v3.JADWAL_RIWAYAT[p["id_panggilan"]]
        selesai = mulai + timedelta(seconds=durasi)
        assert b[8] == "selesai" and b[16] == "sintetis-riwayat"
        assert (b[13], b[14], b[17]) == (mulai, selesai, durasi)
        assert b[15] == (selesai + timedelta(days=30) if p["label"] == "Sesuai" else None)


def test_riwayat_waktu_dan_durasi_sama_dengan_data_demo_fe(data):
    jadwal = [seed_v3.baris_panggilan(p, data["peta_peserta"]) for p in data["riwayat"]]
    assert [b[13].isoformat() for b in jadwal] == [
        "2026-10-05T09:42:00+07:00", "2026-10-05T10:05:00+07:00",
        "2026-10-05T10:31:00+07:00", "2026-10-05T11:18:00+07:00",
    ]
    assert [b[17] for b in jadwal] == [84, 71, 66, 74]


def test_riwayat_penerima_keluarga_untuk_anak_mengikuti_r13(data):
    """CALL-LATAR-001 (5 tahun) dan 004 (8 tahun) ditelepon ke orang tua; jawaban ikut disesuaikan."""
    per_id = {b[0]: b for b in (seed_v3.baris_panggilan(p, data["peta_peserta"]) for p in data["riwayat"])}
    for id_ in ("CALL-LATAR-001", "CALL-LATAR-004"):
        b = per_id[id_]
        assert b[5] == "keluarga" and b[7] == "orang tua"
        assert b[10].obj["penerima"] == "keluarga" and b[10].obj["hubungan"] == "orang tua"
    for id_ in ("CALL-LATAR-002", "CALL-LATAR-003"):
        assert per_id[id_][5] == "peserta" and per_id[id_][10].obj["hubungan"] is None


def test_data_sesuai_prd(data):
    assert len(data["rs"]) == 5
    assert len(data["peserta"]) == 408
    assert len(data["klaim"]) == 4913
    assert len(data["indikator"]) == 300
    assert sum(h["dipicu"] for h in data["indikator"].values()) == 30


def test_antre_26_baris_tanpa_duplikat_riwayat(data):
    antre = data["antre"]
    assert len(antre) == 26
    assert len({b[0] for b in antre}) == 26
    riwayat = {(p["id_peserta"], p["id_rs"]) for p in data["riwayat"]}
    assert not riwayat & {(b[1], b[2]) for b in antre}
    assert all(b[8] == "antre" for b in antre)


def test_s7_tidak_menghasilkan_panggilan(data):
    assert "P-S7" not in {b[1] for b in data["antre"]}


def test_skenario_antre_dengan_penerima_benar(data):
    per_pasien = {b[1]: b for b in data["antre"]}
    assert {f"P-S{i}" for i in (1, 2, 3, 4, 5, 6, 8)} <= per_pasien.keys()
    assert per_pasien["P-S1"][5:8] == ("peserta", "Andi Pratama", None)
    assert per_pasien["P-S1"][4] == 11
    assert per_pasien["P-S2"][5:8] == ("keluarga", "Dewi Rahmawati", "anak")
    assert per_pasien["P-S4"][5:8] == ("keluarga", "Bayu Lestari", "anak")


# ---- skor pola ----

def test_fitur_pola_untuk_300_bulan_pasien_sama_dengan_skor_demo(data):
    assert len(data["fitur_pola"]) == 300 and data["fitur_pola"].keys() == data["indikator"].keys()
    assert {(r["id_peserta"], r["id_rs"]): r["fitur"] for r in SKOR_DEMO} == data["fitur_pola"]


def test_skor_tidak_mengubah_indikator_dan_pemicu(data):
    """baris_indikator hanya menambah tiga kolom skor di belakang; 12 kolom aturan tetap dari aturan.py."""
    h = data["indikator"][("P-S7", "RS04")]
    b = seed_v3.baris_indikator(h, {"skor": 0.999, "tinggi": True, "alasan": []})
    assert b[3:9] == (4, 1, False, False, True, False) and b[10:12] == (1, False)
    assert (b[12], b[13].obj, b[14]) == (0.999, [], True)


def test_seed_menyimpan_skor_semua_bulan_pasien_sama_dengan_skor_demo(conn_v3):
    baris = conn_v3.execute("select id_peserta, id_rs, skor_pola, alasan_pola, pola_tinggi from indikator_bulanan").fetchall()
    ada = {(b["id_peserta"], b["id_rs"]): (round(b["skor_pola"], 3), b["alasan_pola"], b["pola_tinggi"]) for b in baris}
    assert len(ada) == 300
    assert ada == {(r["id_peserta"], r["id_rs"]): (r["skor"], r["alasan"], r["tinggi"]) for r in SKOR_DEMO}
    assert repr(conn_v3.execute("select nilai from pengaturan where kunci = 'versi_pola'").fetchone()["nilai"]) == "'pola-v1'"


def test_seed_ulang_mengisi_skor_di_database_lama_tanpa_mengubah_indikator(conn_v3):
    conn_v3.execute("update indikator_bulanan set skor_pola = null, alasan_pola = '[]', pola_tinggi = false, dipicu = false")
    seed_v3.isi_ke(conn_v3, seed_v3.muat_data())
    r = conn_v3.execute(
        "select count(*) filter (where skor_pola is not null) as berskor, count(*) filter (where pola_tinggi) as tinggi,"
        " count(*) filter (where dipicu) as dipicu, count(*) as n from indikator_bulanan"
    ).fetchone()
    assert r == {"berskor": 300, "tinggi": 22, "dipicu": 0, "n": 300}  # kolom aturan baris lama tidak ditimpa


def test_reset_panggilan_tidak_menghapus_skor(conn_v3):
    seed_v3.reset_panggilan(conn_v3, seed_v3.muat_data())
    n = conn_v3.execute("select count(*) as n from indikator_bulanan where skor_pola is not null").fetchone()["n"]
    assert n == 300


def test_seed_memakai_versi_model_di_pengaturan(conn_v3, monkeypatch):
    """versi_pola di pengaturan menentukan model yang dipakai seed; bawaan pola-v1."""
    dipakai = []
    asli = pola_v3.nilai
    monkeypatch.setattr(pola_v3, "nilai", lambda fitur, versi: dipakai.append(versi) or asli(fitur))
    conn_v3.execute("update pengaturan set nilai = '\"pola-v2\"' where kunci = 'versi_pola'")
    seed_v3.isi_ke(conn_v3, seed_v3.muat_data())
    assert set(dipakai) == {"pola-v2"} and len(dipakai) == 300
