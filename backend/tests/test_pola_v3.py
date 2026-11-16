"""Uji app/pola_v3.py tanpa database: model dan referensi agregat, teks kombinasi, posisi pembanding."""
import pytest

from app import config, pola_v3


def test_model_dan_referensi_dimuat_dari_data_uji():
    m = pola_v3.model()
    assert m["versi"] == "pola-v1" and 0 < m["ambang_tinggi"] < 1
    assert pola_v3.referensi()["peta_tipe"]["Swasta setara kelas C"] == "RS Swasta Setara Type C"
    assert (config.DATA_UJI / "referensi-pola" / "referensi.json").exists()


def test_nilai_s1_tinggi_dengan_dua_alasan():
    n = pola_v3.nilai({"sesi": 11, "maks_minggu": 4, "ahad_libur": 2, "episode": 3})
    assert n["skor"] >= pola_v3.model()["ambang_tinggi"] and n["tinggi"] is True
    assert [a["fitur"] for a in n["alasan"]] == ["ahad_libur", "maks_minggu"]


def test_nilai_pasien_wajar_rendah():
    n = pola_v3.nilai({"sesi": 4, "maks_minggu": 1, "ahad_libur": 0, "episode": 2})
    assert n["skor"] < 0.1 and n["tinggi"] is False


def test_kombinasi_pasti_dan_tersembunyi():
    assert pola_v3.kombinasi(True, True, False, False) == {
        "kunci": "I1+I2", "teks": "Kombinasi I1+I2 terjadi pada 0,80% bulan-pasien fisioterapi nasional 2024.",
    }
    assert pola_v3.kombinasi(True, True, True, True)["teks"] == (
        "Kombinasi I1+I2+I3+I4 terjadi pada kurang dari 0,03% bulan-pasien fisioterapi nasional 2024."
    )


@pytest.mark.parametrize("persen,posisi", [(39.7, "di_atas_p95"), (8.3, "di_atas_p95"), (8.2, "di_atas_p90"),
                                           (4.4, "di_atas_p90"), (4.3, "wajar"), (0.0, "wajar")])
def test_pembanding_posisi_terhadap_rs_sejenis(persen, posisi):
    p = pola_v3.pembanding("Swasta setara kelas C", 68, persen)
    assert (p["tipe"], p["posisi"], p["terpicu_p95_kelompok"]) == ("RS Swasta Setara Type C", posisi, 8.2)


def test_pembanding_tipe_tak_dikenal_memakai_nasional_dan_tanpa_pasien_tanpa_pembanding():
    assert pola_v3.pembanding("Klinik entah", 10, 1.0)["tipe"] == "Nasional"
    assert pola_v3.pembanding(None, 10, 9.5)["posisi"] == "di_atas_p95"
    assert pola_v3.pembanding("Pemerintah kelas B", 0, 0.0)["posisi"] == "tidak_ada_pembanding"


def test_backend_tidak_bergantung_pada_pustaka_data():
    syarat = (config.AKAR / "backend" / "requirements.txt").read_text().lower()
    assert not any(nama in syarat for nama in ("numpy", "pandas", "scikit-learn", "sklearn"))
    sumber = (config.AKAR / "backend" / "app" / "pola_v3.py").read_text()
    assert "kunci_kebenaran" not in sumber and "Folder Data Asli" not in sumber
