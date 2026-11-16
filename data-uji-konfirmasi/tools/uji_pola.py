"""Uji tools/pola.py tanpa pustaka luar.

  python3 tools/uji_pola.py
"""
import csv, math, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pola  # noqa: E402
from aturan import hitung_indikator  # noqa: E402

BULAN = "2026-08"


def fitur_demo():
    """(id_peserta, id_rs) -> fitur mentah Agustus 2026 dari klaim_sesi.csv."""
    libur = {date.fromisoformat(r["tanggal"]) for r in csv.DictReader(open(ROOT / "libur_nasional_2026.csv"))}
    sesi = [((r["id_peserta"], r["id_rs"]), date.fromisoformat(r["tanggal"])) for r in csv.DictReader(open(ROOT / "klaim_sesi.csv"))]
    return pola.fitur_per_pasien(sesi, BULAN, libur), libur


def uji_paritas_dengan_aturan():
    fitur, libur = fitur_demo()
    sesi = [{"id_peserta": r["id_peserta"], "id_rs": r["id_rs"], "tanggal": date.fromisoformat(r["tanggal"])}
            for r in csv.DictReader(open(ROOT / "klaim_sesi.csv"))]
    ind = hitung_indikator(sesi, libur, BULAN)
    assert len(fitur) == len(ind) == 302, (len(fitur), len(ind))
    for kunci, h in ind.items():
        f = fitur[kunci]
        assert f["sesi"] == h["sesi_ditagih"], kunci
        assert f["maks_minggu"] == h["maks_sesi_seminggu"], kunci
        assert (f["ahad_libur"] > 0) == h["I4_hari_libur"], kunci
        assert f["ahad_libur"] == len(h["tanggal_libur"]), kunci
        assert (f["episode"] >= 6) == h["I3_episode_6_bulan"], kunci
        i = pola.indikator(f)
        assert i == (h["I1_lebih_8_sebulan"], h["I2_3x_seminggu"], h["I3_episode_6_bulan"], h["I4_hari_libur"]), kunci
        assert (sum(i) >= 2) == h["dipicu"], kunci


def uji_fitur_bulan():
    tgl = [date(2026, 8, d) for d in (3, 4, 6, 10, 16, 17)]
    f = pola.fitur_bulan(tgl, {"2026-08", "2026-07", "2026-06", "2026-04"}, "2026-08", {date(2026, 8, 17)})
    assert f == {"sesi": 6, "maks_minggu": 3, "ahad_libur": 2, "episode": 3}, f
    lama = {pola.bulan_sebelumnya("2026-08", n) for n in range(12)}
    assert pola.fitur_bulan(tgl, lama, "2026-08", set())["episode"] == 7
    assert pola.fitur_bulan(tgl, {"2026-08"}, "2026-08", set())["ahad_libur"] == 1
    assert pola.bulan_sebelumnya("2026-02", 3) == "2025-11"


def uji_fitur_per_pasien():
    sesi = [("A", date(2026, 7, 6)), ("A", date(2026, 8, 3)), ("A", date(2026, 8, 9)), ("B", date(2026, 7, 6))]
    hasil = pola.fitur_per_pasien(sesi, "2026-08", set())
    assert hasil == {"A": {"sesi": 2, "maks_minggu": 2, "ahad_libur": 1, "episode": 2}}, hasil  # B tidak aktif Agustus


def uji_bin():
    assert pola.bin_fitur({"sesi": 1, "maks_minggu": 1, "ahad_libur": 0, "episode": 1}) == {
        "sesi": "1", "maks_minggu": "1", "ahad_libur": "0", "episode": "1"}
    assert pola.bin_fitur({"sesi": 12, "maks_minggu": 5, "ahad_libur": 1, "episode": 6}) == {
        "sesi": "12", "maks_minggu": "5", "ahad_libur": "1", "episode": "6"}
    assert pola.bin_fitur({"sesi": 20, "maks_minggu": 7, "ahad_libur": 4, "episode": 7}) == {
        "sesi": "13+", "maks_minggu": "6+", "ahad_libur": "2+", "episode": "7+"}
    assert all(len(set(b)) == len(b) for b in pola.BIN.values())


def uji_kombinasi():
    assert pola.kombinasi(True, True, False, True) == "I1+I2+I4"
    assert pola.kombinasi(False, False, True, False) == "I3"
    assert pola.kombinasi(False, False, False, False) == "-"


MODEL = {
    "fitur": ["sesi", "maks_minggu", "ahad_libur"], "intersep": -2.0,
    "koefisien": {
        "sesi": {"3": -0.5, "11": 1.5}, "maks_minggu": {"1": -0.2, "4": 0.8},
        "ahad_libur": {"0": -0.1, "2+": 2.0}, "episode": {"1": 9.0},
    },
}
REFERENSI = {"marginal": {
    "sesi": {"3": 0.9, "11": 0.1}, "maks_minggu": {"1": 0.8, "4": 0.2},
    "ahad_libur": {"0": 0.99, "2+": 0.01}, "episode": {"1": 1.0},
}}
S1 = {"sesi": 11, "maks_minggu": 4, "ahad_libur": 2, "episode": 3}


def uji_skor_hitung_tangan():
    # z = -2 + 1.5 + 0.8 + 2.0 = 2.3; episode tidak ada di model["fitur"], jadi diabaikan
    assert pola.skor(MODEL, S1) == round(1 / (1 + math.exp(-2.3)), 3) == 0.909
    assert pola.logit(MODEL, S1) == 2.3
    # skor sama setelah dibulatkan, logit tetap membedakan
    tinggi = {"sesi": 11, "maks_minggu": 4, "ahad_libur": 2, "episode": 1}
    model_kuat = {**MODEL, "intersep": 8.0}
    assert pola.skor(model_kuat, S1) == pola.skor(model_kuat, tinggi) == 1.0
    assert pola.logit(model_kuat, S1) == 12.3 and pola.logit(model_kuat, tinggi) == 12.3
    assert pola.logit(model_kuat, {**S1, "ahad_libur": 0}) == 10.2
    # bin yang tidak ada di model bernilai 0: z = -2
    assert pola.skor(MODEL, {"sesi": 5, "maks_minggu": 2, "ahad_libur": 1, "episode": 1}) == 0.119


def uji_alasan_urut_dan_positif():
    a = pola.alasan(MODEL, REFERENSI, S1)
    # sumbangan: ahad 2.0-(0.99*-0.1+0.01*2.0)=2.079; sesi 1.5-(0.9*-0.5+0.1*1.5)=1.8; minggu 0.8-(-0.16+0.16)=0.8
    assert [(x["fitur"], x["kontribusi"]) for x in a] == [("ahad_libur", 2.079), ("sesi", 1.8)], a
    assert a[0]["teks"] == "2 sesi pada hari Minggu atau libur. Hanya 1% tagihan bulanan nasional memuat sesi seperti ini."
    assert a[1]["teks"] == "11 sesi dalam sebulan, lebih banyak dari 90% tagihan bulanan fisioterapi nasional."
    assert (a[0]["nilai"], a[0]["persentil_nasional"], a[1]["persentil_nasional"]) == (2, 100.0, 100.0)
    assert len(pola.alasan(MODEL, REFERENSI, S1, n=3)) == 3
    wajar = pola.alasan(MODEL, REFERENSI, {"sesi": 3, "maks_minggu": 1, "ahad_libur": 0, "episode": 1})
    assert wajar == [], wajar


def uji_persen():
    assert [pola.persen(x) for x in (99.0, 0.4, 99.96, 0.02, 0, 100, 12.34)] == [
        "99", "0,4", "99,9", "kurang dari 0,1", "0", "100", "12,3"]


if __name__ == "__main__":
    daftar = [v for k, v in sorted(globals().items()) if k.startswith("uji_")]
    for uji in daftar:
        uji()
        print("  LULUS", uji.__name__)
    print(f"HASIL: LULUS ({len(daftar)} uji)")
