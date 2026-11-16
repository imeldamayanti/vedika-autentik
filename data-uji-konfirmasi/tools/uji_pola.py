"""Tests for tools/pola.py, standard library only.

  python3 tools/uji_pola.py
"""
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pola  # noqa: E402
from aturan import hitung_indikator  # noqa: E402

MONTH = "2026-08"


def demo_features():
    """(participant, hospital) -> raw August 2026 features from klaim_sesi.csv."""
    holidays = {date.fromisoformat(r["tanggal"]) for r in csv.DictReader(open(ROOT / "libur_nasional_2026.csv"))}
    sessions = [
        ((r["id_peserta"], r["id_rs"]), date.fromisoformat(r["tanggal"]))
        for r in csv.DictReader(open(ROOT / "klaim_sesi.csv"))
    ]
    return pola.features_per_patient(sessions, MONTH, holidays), holidays


def uji_parity_with_rules():
    features, holidays = demo_features()
    sessions = [
        {"id_peserta": r["id_peserta"], "id_rs": r["id_rs"], "tanggal": date.fromisoformat(r["tanggal"])}
        for r in csv.DictReader(open(ROOT / "klaim_sesi.csv"))
    ]
    expected = hitung_indikator(sessions, holidays, MONTH)
    assert len(features) == len(expected) == 302, (len(features), len(expected))
    for key, h in expected.items():
        f = features[key]
        assert f["sesi"] == h["sesi_ditagih"], key
        assert f["maks_minggu"] == h["maks_sesi_seminggu"], key
        assert f["ahad_libur"] == len(h["tanggal_libur"]), key
        flags = pola.indicators(f)
        assert flags == (h["I1_lebih_8_sebulan"], h["I2_3x_seminggu"], h["I3_episode_6_bulan"], h["I4_hari_libur"]), key
        assert (sum(flags) >= 2) == h["dipicu"], key


def uji_month_features():
    days = [date(2026, 8, d) for d in (3, 4, 6, 10, 16, 17)]
    f = pola.month_features(days, {"2026-08", "2026-07", "2026-06", "2026-04"}, "2026-08", {date(2026, 8, 17)})
    assert f == {"sesi": 6, "maks_minggu": 3, "ahad_libur": 2, "episode": 3}, f
    long_run = {pola.previous_month("2026-08", n) for n in range(12)}
    assert pola.month_features(days, long_run, "2026-08", set())["episode"] == pola.EPISODE_MAX
    assert pola.month_features(days, {"2026-08"}, "2026-08", set())["ahad_libur"] == 1
    assert pola.previous_month("2026-02", 3) == "2025-11"


def uji_features_per_patient():
    sessions = [("A", date(2026, 7, 6)), ("A", date(2026, 8, 3)), ("A", date(2026, 8, 9)), ("B", date(2026, 7, 6))]
    result = pola.features_per_patient(sessions, "2026-08", set())
    assert result == {"A": {"sesi": 2, "maks_minggu": 2, "ahad_libur": 1, "episode": 2}}, result  # B not active in August


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("uji_")]
    for test in tests:
        test()
        print("  LULUS", test.__name__)
    print(f"HASIL: LULUS ({len(tests)} uji)")
