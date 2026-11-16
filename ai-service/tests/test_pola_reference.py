import csv
import json
from datetime import date
from pathlib import Path

import pytest

from vedika_ai.claim_reference import (
    _FORBIDDEN_AGGREGATE_KEYS,
    MINIMUM_SAFE_CELL_COUNT,
    ClaimReferenceError,
    assert_privacy_safe_aggregate,
    sha256_file,
)
from vedika_ai.pola_reference import (
    NATIONAL,
    aggregate,
    load_pola,
    patient_months,
    percentile,
    weighted_percentile,
)

REFERENCE_DIR = Path(__file__).parents[1] / "data" / "reference" / "pola-2024"
BENCHMARK_KEYS = {
    "bulan_pasien",
    "persen_terpicu",
    "sesi_rata",
    "sesi_p90",
    "sesi_p95",
    "kelompok",
    "terpicu_p50",
    "terpicu_p90",
    "terpicu_p95",
}


def visit(participant, day, *, group=(1, 9, 1, 7), kind="RS Swasta Setara Type C", weight=2.0):
    return {
        "peserta": participant,
        "tanggal": date.fromisoformat(day),
        "bobot": weight,
        "kelompok": group,
        "tipe": kind,
    }


def frame(participants, days, **kwargs):
    return [visit(p, day, **kwargs) for p in participants for day in days]


def test_patient_months_use_shared_features_and_sunday_only():
    days = ["2024-07-01", "2024-07-02", "2024-07-03", "2024-07-07", "2024-08-05"]
    visits = [visit(1, day) for day in days]
    visits.append(visit(1, "2024-08-06", group=(2, 3, 1, 2), kind="RS Kelas B"))
    visits.append(visit(1, "2024-08-07", group=(2, 3, 1, 2), kind="RS Kelas B"))

    july, august = sorted(patient_months(visits), key=lambda record: record["bulan"])

    assert july["fitur"] == {"sesi": 4, "maks_minggu": 4, "ahad_libur": 1, "episode": 1}
    assert (july["kombinasi"], july["dipicu"]) == ("I2+I4", True)
    assert august["fitur"] == {"sesi": 3, "maks_minggu": 3, "ahad_libur": 0, "episode": 2}
    assert (august["kombinasi"], august["dipicu"]) == ("I2", False)
    assert (august["kelompok"], august["tipe"]) == ((2, 3, 1, 2), "RS Kelas B")
    assert july["bobot"] == 2.0
    assert "peserta" not in july


def test_aggregate_suppresses_small_cells_everywhere():
    common = frame(range(1, 13), ["2024-08-05", "2024-08-12"])
    rare = frame(range(100, 103), ["2024-08-05", "2024-08-06", "2024-08-07", "2024-08-11"])

    result = aggregate(common + rare)

    assert result["histogram"] == [
        {
            "sesi": "2",
            "maks_minggu": "1",
            "ahad_libur": "0",
            "episode": "1",
            "n": 12,
            "bobot": 24.0,
        }
    ]
    assert result["suppression"]["histogram"] == {
        "cells_total": 2,
        "cells_suppressed": 1,
        "row_share_suppressed": 0.2,
        "weight_share_suppressed": 0.2,
    }
    assert result["marginal"]["marginal"]["sesi"] == {"2": 1.0}
    assert result["marginal"]["digabung"]["sesi"]["4"] == "2"
    assert result["marginal"]["marginal"]["ahad_libur"] == {"0": 1.0}
    combos = result["kombinasi"]["kombinasi"]
    assert combos["-"] == {"n": 12, "prevalensi": 0.8}
    assert combos["I2+I4"] == {"prevalensi_maks": round(10 / 15, 6)}
    assert combos["I1+I2+I3+I4"] == {"prevalensi_maks": round(10 / 15, 6)}
    assert len(combos) == 16
    assert result["pembanding_tipe"].keys() == {NATIONAL}
    assert result["suppression"]["types_omitted_under_100_patient_months"] == 1
    assert "100" not in json.dumps(result["histogram"])


def test_aggregate_keeps_months_outside_the_window_out_of_the_histogram():
    result = aggregate(frame(range(1, 13), ["2024-03-05", "2024-08-12"]))

    assert result["counts"]["participant_months"] == 24
    assert result["counts"]["histogram_participant_months"] == 12
    assert result["histogram"][0]["n"] == 12


def test_benchmark_percentiles_need_enough_groups():
    visits = []
    for group in range(20):
        triggered = group == 0
        dense = ["2024-08-05", "2024-08-06", "2024-08-07", "2024-08-11"]
        days = dense if triggered else ["2024-08-05"]
        visits += frame(range(group * 100, group * 100 + 30), days, group=(group, 9, 1, 7))

    result = aggregate(visits)

    type_c = result["pembanding_tipe"]["RS Swasta Setara Type C"]
    assert (type_c["bulan_pasien"], type_c["kelompok"]) == (600, 20)
    assert (type_c["persen_terpicu"], type_c["terpicu_p50"]) == (5.0, 0.0)
    assert type_c.keys() == BENCHMARK_KEYS
    assert result["counts"]["peer_groups_with_30_patient_months"] == 20

    fewer = aggregate([v for v in visits if v["kelompok"][0] < 19])
    assert "terpicu_p95" not in fewer["pembanding_tipe"]["RS Swasta Setara Type C"]


def test_aggregate_rejects_a_minimum_below_the_safe_cell_count():
    with pytest.raises(ClaimReferenceError, match="minimum_count"):
        aggregate([visit(1, "2024-08-05")], minimum_count=5)


def test_percentiles():
    assert percentile([0.0, 10.0], 0.5) == 5.0
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.9) == pytest.approx(4.6)
    assert weighted_percentile([(1, 9.0), (8, 1.0)], 0.9) == 1
    assert weighted_percentile([(1, 9.0), (8, 1.0)], 0.95) == 8


def read_json(name):
    return json.loads((REFERENCE_DIR / name).read_text(encoding="utf-8"))


def all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_keys(child)


def test_committed_histogram_has_only_binned_safe_cells():
    pola = load_pola()
    with (REFERENCE_DIR / "histogram.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))

    assert rows
    assert list(rows[0]) == [*pola.FITUR, "n", "bobot"]
    assert not {name.casefold() for name in rows[0]} & _FORBIDDEN_AGGREGATE_KEYS
    assert all(int(row["n"]) >= MINIMUM_SAFE_CELL_COUNT for row in rows)
    assert all(row[name] in pola.BIN[name] for row in rows for name in pola.FITUR)
    assert len({tuple(row[name] for name in pola.FITUR) for row in rows}) == len(rows)


@pytest.mark.parametrize(
    "name", ["marginal.json", "kombinasi.json", "pembanding_tipe.json", "manifest.json"]
)
def test_committed_json_has_no_identifiers_small_counts_or_extremes(name):
    payload = read_json(name)

    assert_privacy_safe_aggregate(payload)
    for key in all_keys(payload):
        assert not any(part in key.casefold() for part in ("max", "min_", "tertinggi")), key

    def counts(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ("n", "bulan_pasien"):
                    yield child
                yield from counts(child)

    assert all(count >= MINIMUM_SAFE_CELL_COUNT for count in counts(payload))


def test_committed_combinations_hide_rare_cells():
    payload = read_json("kombinasi.json")

    assert len(payload["kombinasi"]) == 16
    for cell in payload["kombinasi"].values():
        assert cell.keys() in ({"n", "prevalensi"}, {"prevalensi_maks"})
    assert 0.01 <= payload["terpicu"] <= 0.02


def test_committed_benchmarks_follow_the_export_rules():
    payload = read_json("pembanding_tipe.json")

    assert NATIONAL in payload
    for cell in payload.values():
        assert cell.keys() <= BENCHMARK_KEYS
        assert cell["bulan_pasien"] >= 100
        assert ("terpicu_p95" in cell) == (cell["kelompok"] >= 20)


def test_committed_manifest_matches_outputs_and_privacy_flags():
    manifest = read_json("manifest.json")
    rehab = json.loads(
        (REFERENCE_DIR.parent / "rehab-2024" / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["privacy"] == rehab["privacy"]
    assert manifest["source"]["filename"].endswith(".dta")
    assert "/" not in manifest["source"]["filename"]
    assert {output["filename"] for output in manifest["outputs"]} == {
        "histogram.csv",
        "marginal.json",
        "kombinasi.json",
        "pembanding_tipe.json",
    }
    for output in manifest["outputs"]:
        path = REFERENCE_DIR / output["filename"]
        assert path.stat().st_size == output["size_bytes"]
        assert sha256_file(path) == output["sha256"]


MODEL_DIR = Path(__file__).parents[2] / "data-uji-konfirmasi" / "referensi-pola"


def test_committed_model_is_a_plain_coefficient_table():
    pola = load_pola()
    model = json.loads((MODEL_DIR / "model-pola-v1.json").read_text(encoding="utf-8"))

    assert_privacy_safe_aggregate(model)
    assert model["versi"] == "pola-v1"
    assert set(model["fitur"]) <= set(pola.FITUR)
    assert all(list(model["koefisien"][name]) == pola.BIN[name] for name in model["fitur"])
    assert 0 < model["ambang_tinggi"] < 1
    assert model["dilatih_dari"] == "ai-service/data/reference/pola-2024"


def test_committed_runtime_reference_is_aggregate_only():
    reference = json.loads((MODEL_DIR / "referensi.json").read_text(encoding="utf-8"))
    source = read_json("pembanding_tipe.json")

    assert_privacy_safe_aggregate(reference)
    assert reference["marginal"] == read_json("marginal.json")["marginal"]
    assert reference["kombinasi"] == read_json("kombinasi.json")["kombinasi"]
    assert set(reference["pembanding_tipe"]) == {NATIONAL, *reference["peta_tipe"].values()}
    for label, cell in reference["pembanding_tipe"].items():
        assert cell == source[label]
        assert cell.keys() <= BENCHMARK_KEYS


def test_committed_demo_scores_cover_every_august_patient_month():
    pola = load_pola()
    model = json.loads((MODEL_DIR / "model-pola-v1.json").read_text(encoding="utf-8"))
    scores = json.loads((MODEL_DIR / "skor_demo.json").read_text(encoding="utf-8"))

    assert len(scores) == 300
    for row in scores:
        assert row["skor"] == pola.skor(model, row["fitur"])
        assert row["tinggi"] == (row["skor"] >= model["ambang_tinggi"])
        assert len(row["alasan"]) <= 2
