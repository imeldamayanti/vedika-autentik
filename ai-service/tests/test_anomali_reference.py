import json
from datetime import date
from pathlib import Path

import pytest

from vedika_ai.anomali_reference import in_window, table, threshold, top_share
from vedika_ai.claim_reference import (
    MINIMUM_SAFE_CELL_COUNT,
    ClaimReferenceError,
    assert_privacy_safe_aggregate,
)
from vedika_ai.pola_reference import load_anomali, patient_months

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "data-uji-konfirmasi" / "referensi-pola" / "model-anomali-v1.json"
REAL = Path(__file__).parents[1] / "data" / "reference" / "pola-2024" / "anomali-nyata.json"
anomali = load_anomali()

BIASA = {
    "sesi": 3,
    "maks_minggu": 1,
    "ahad_libur": 0,
    "episode": 1,
    "tanpa_rujukan": 0.0,
    "lintas_wilayah": 0.0,
}
MODEL_KECIL = {
    "tahun": "2024",
    "ambang": 0.6,
    "minimum_sel": 10,
    "marginal": {
        "sesi": [0.7, 0.27, 0.02, 0.01],
        "maks_minggu": [0.97, 0.02, 0.01],
        "ahad_libur": [0.99, 0.006, 0.004],
        "episode": [0.6, 0.31, 0.09],
        "tanpa_rujukan": [0.8, 0.03, 0.17],
        "lintas_wilayah": [0.84, 0.01, 0.15],
    },
    "sel": {
        "0|0|0|0|0|0": {"skor": 0.37, "pangsa": 0.3},
        "0|0|0|2|2|2": {"skor": 0.7, "pangsa": 0.002},
    },
}


def test_bins_follow_hand_set_edges():
    assert anomali.bin_fitur(BIASA) == (0, 0, 0, 0, 0, 0)
    padat = BIASA | {
        "sesi": 9,
        "maks_minggu": 4,
        "ahad_libur": 2,
        "episode": 6,
        "tanpa_rujukan": 0.5,
        "lintas_wilayah": 1.0,
    }
    assert anomali.bin_fitur(padat) == (2, 2, 2, 2, 1, 2)
    assert anomali.bin_fitur(BIASA | {"sesi": 13}) == (3, 0, 0, 0, 0, 0)


def test_referral_features_are_visit_shares():
    kunjungan = [
        {"rujukan": True, "lintas": False},
        {"rujukan": False, "lintas": True},
        {"rujukan": False, "lintas": True},
        {"rujukan": True, "lintas": False},
    ]
    assert anomali.fitur_rujukan(kunjungan) == {"tanpa_rujukan": 0.5, "lintas_wilayah": 0.5}


def test_patient_months_carry_referral_features():
    visits = [
        {
            "peserta": 1,
            "tanggal": date(2024, 7, d),
            "bobot": 2.0,
            "kelompok": (1, 9, 1, 7),
            "tipe": "C",
            "rujukan": d != 1,
            "lintas": d == 1,
            "dx": "Z50",
            "cbg": "M-3-16-0",
        }
        for d in (1, 8)
    ]
    (record,) = patient_months(visits)
    assert record["fitur_anomali"] == {
        "sesi": 2,
        "maks_minggu": 1,
        "ahad_libur": 0,
        "episode": 1,
        "tanpa_rujukan": 0.5,
        "lintas_wilayah": 0.5,
    }
    assert record["kode"] == [("Z50", "M-3-16-0"), ("Z50", "M-3-16-0")]


def test_score_lookup_and_unseen_combinations_are_flagged():
    assert anomali.nilai(MODEL_KECIL, BIASA) == {"skor": 0.37, "ditandai": False, "langka": False}
    assert anomali.alasan(MODEL_KECIL, BIASA) == {
        "alasan": [],
        "gabungan": "Gabungan pola ini muncul pada 30% tagihan bulanan fisioterapi nasional 2024.",
    }
    jauh = BIASA | {"episode": 6, "tanpa_rujukan": 1.0, "lintas_wilayah": 1.0}
    assert anomali.nilai(MODEL_KECIL, jauh) == {"skor": 0.7, "ditandai": True, "langka": False}
    langka = BIASA | {"sesi": 13, "ahad_libur": 2}
    assert anomali.nilai(MODEL_KECIL, langka) == {"skor": None, "ditandai": True, "langka": True}


def test_reasons_name_rare_bins_rarest_first_and_the_combination():
    jauh = BIASA | {"episode": 6, "tanpa_rujukan": 1.0, "lintas_wilayah": 1.0}
    hasil = anomali.alasan(MODEL_KECIL, jauh)
    assert [a["fitur"] for a in hasil["alasan"]] == ["episode"]
    assert (
        hasil["alasan"][0]["teks"]
        == "6 bulan atau lebih berturut-turut: hanya 9% tagihan bulanan fisioterapi nasional."
    )
    assert (
        hasil["gabungan"]
        == "Gabungan 6 bulan atau lebih berturut-turut, semua kunjungan tanpa rujukan FKTP, dan"
        " semua dirujuk dari kab/kota lain muncul pada 0,2% tagihan bulanan fisioterapi"
        " nasional 2024."
    )
    langka = anomali.alasan(MODEL_KECIL, BIASA | {"sesi": 13, "ahad_libur": 2})
    assert [a["fitur"] for a in langka["alasan"]] == ["ahad_libur", "sesi"]
    assert (
        langka["gabungan"]
        == "Gabungan 13 sesi atau lebih sebulan dan 2 sesi atau lebih hari Minggu muncul pada"
        " kurang dari 10 tagihan bulanan di data sampel BPJS 2024."
    )


def records(n, weight=1.0):
    return [{"bobot": weight} for _ in range(n)]


def test_table_keeps_only_cells_with_enough_records():
    recs = records(12) + records(3)
    rows = [(0, 0, 0, 0, 0, 0)] * 12 + [(3, 2, 2, 2, 2, 2)] * 3
    cells, left_out = table(recs, rows, [0.4] * 12 + [0.9] * 3, MINIMUM_SAFE_CELL_COUNT)
    assert cells == {"0|0|0|0|0|0": {"skor": 0.4, "pangsa": 0.8}}
    assert left_out == pytest.approx(0.2)
    with pytest.raises(ClaimReferenceError):
        table(recs, rows, [0.4] * 15, MINIMUM_SAFE_CELL_COUNT - 1)


def test_threshold_counts_unseen_combinations_toward_the_target():
    cells = {
        "a": {"skor": 0.9, "pangsa": 0.01},
        "b": {"skor": 0.7, "pangsa": 0.02},
        "c": {"skor": 0.3, "pangsa": 0.96},
    }
    assert threshold(cells, 0.0, 0.015) == 0.7
    assert threshold(cells, 0.01, 0.015) == 0.9


def test_top_share_is_weighted():
    recs = [{"bobot": 1.0}, {"bobot": 8.0}, {"bobot": 1.0}]
    assert top_share(recs, [0.9, 0.5, 0.1], 0.1) == {0}
    assert top_share(recs, [0.9, 0.5, 0.1], 0.5) == {0, 1}


def test_committed_model_is_a_safe_table():
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    assert_privacy_safe_aggregate(model)
    assert model["fitur"] == list(anomali.FITUR)
    assert model["batas"] == {k: list(v) for k, v in anomali.BATAS.items()}
    assert model["minimum_sel"] >= MINIMUM_SAFE_CELL_COUNT
    assert all(set(cell) == {"skor", "pangsa"} for cell in model["sel"].values())
    assert all(len(key.split("|")) == len(anomali.FITUR) for key in model["sel"])
    for name, shares in model["marginal"].items():
        assert len(shares) == len(anomali.BATAS[name]) + 1
        assert sum(shares) == pytest.approx(1, abs=1e-4)
    assert 0.98 < sum(c["pangsa"] for c in model["sel"].values()) <= 1


def test_committed_real_behaviour_reports_only_counts_of_ten_or_more():
    real = json.loads(REAL.read_text(encoding="utf-8"))
    assert_privacy_safe_aggregate(real)
    counts = [g["bulan_pasien"] for g in real["kelompok"]]
    counts += [r["bulan_pasien"] for r in real["alasan_pertama_hanya_model"]]
    counts += [p["bulan_pasien"] for p in real["pola_teratas_hanya_model"]]
    assert counts and min(counts) >= MINIMUM_SAFE_CELL_COUNT
    assert "kelompok" not in real["rs"] and set(real["rs"]) == {
        "kelompok_rs",
        "ditandai",
        "pemicu_utama",
        "median_nasional",
    }


def test_only_months_with_a_full_six_month_look_back_are_used():
    months = [f"2024-{m:02d}" for m in range(1, 13)] + ["2023-07"]
    kept = [r["bulan"] for r in in_window([{"bulan": b} for b in months])]
    assert kept == ["2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12", "2023-07"]


def test_committed_method_comparison_holds_only_shares():
    path = Path(__file__).parents[1] / "data" / "reference" / "pola-2024" / "banding-metode.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    assert_privacy_safe_aggregate(result)
    assert set(result["hasil"]) >= {"Isolation Forest", "Local Outlier Factor", "One-Class SVM"}
    for row in result["hasil"].values():
        assert 0 <= row["persen_ditandai"] <= 100
