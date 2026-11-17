import json
import math

import pytest

from vedika_ai.ml import anomaly_evaluation, anomaly_model, tools
from vedika_ai.ml.privacy import MINIMUM_SAFE_CELL_COUNT, ReferenceDataError, assert_privacy_safe

anomali = tools.anomali()
COMMON = {
    "sesi": 4,
    "maks_minggu": 2,
    "ahad_libur": 0,
    "episode": 1,
    "tanpa_rujukan": 0.0,
    "lintas_wilayah": 0.0,
}


def record(
    age_group="40-59", weight=1.0, triggered=False, peer_group=(1,), condition=None, **changes
):
    features = COMMON | changes
    return {
        "month": "2024-08",
        "features": {k: features[k] for k in ("sesi", "maks_minggu", "ahad_libur", "episode")},
        "anomaly_features": features,
        "age_group": age_group,
        "condition": condition,
        "weight": weight,
        "triggered": triggered,
        "peer_group": peer_group,
    }


def every_bin():
    """At least 10 records in every bin of every feature, so fit() accepts the data."""
    rows = []
    for name, bounds in anomali.BIN_UPPER_BOUNDS.items():
        values = {"tanpa_rujukan": (0.0, 0.5, 1.0), "lintas_wilayah": (0.0, 0.5, 1.0)}.get(
            name, tuple(b + 1 for b in (-1, *bounds))
        )
        for value in values[: len(bounds) + 1]:
            rows += [
                record(
                    **{name: max(value, 1) if name in ("sesi", "maks_minggu", "episode") else value}
                )
            ] * 10
    return rows


def population():
    return every_bin() + [
        record(age_group=age) for age in ("<18", "18-39", "40-59", "60+") for _ in range(400)
    ]


@pytest.mark.parametrize(
    ("feature", "value", "expected"),
    [
        ("sesi", 4, 0),
        ("sesi", 5, 1),
        ("sesi", 8, 1),
        ("sesi", 9, 2),
        ("sesi", 13, 3),
        ("ahad_libur", 0, 0),
        ("ahad_libur", 1, 1),
        ("ahad_libur", 3, 2),
        ("tanpa_rujukan", 0.0, 0),
        ("tanpa_rujukan", 0.5, 1),
        ("tanpa_rujukan", 1.0, 2),
    ],
)
def test_bins_sit_on_the_rule_thresholds(feature, value, expected):
    assert anomali.bin_value(feature, value) == expected


@pytest.mark.parametrize(
    ("age", "group"), [(None, None), (17, "<18"), (18, "18-39"), (59, "40-59"), (60, "60+")]
)
def test_age_groups(age, group):
    assert anomali.age_group(age) == group


def test_referral_features_default_to_a_local_fktp_referral():
    visits = [{}, {"referred": False}, {"referred": False, "other_district": True}, {}]
    assert anomali.referral_features(visits) == {"tanpa_rujukan": 0.5, "lintas_wilayah": 0.25}


def test_smoothed_shares_of_a_group_sum_to_one():
    national = {"a": 0.5, "b": 0.3, "c": 0.2}
    stored = {"a": 0.8}
    total = sum(anomali.smoothed_share(100, 50, stored, national, k) for k in national)
    assert total == pytest.approx(1.0)
    assert anomali.smoothed_share(100, 0, stored, national, "b") == pytest.approx(0.2 * 0.3 / 0.5)
    assert anomali.smoothed_share(100, 1e9, stored, national, "a") == pytest.approx(0.5)


def test_fit_flags_about_the_target_share_and_patterns_too_rare_to_store():
    rows = (
        population()
        + [record(sesi=6, ahad_libur=2)] * 40
        + [record(sesi=13, maks_minggu=4, ahad_libur=2)] * 3
    )
    model = anomaly_model.fit(rows, target=0.02)

    flagged = [r for r in rows if anomaly_model.score(model, r)["flagged"]]
    assert sum(r["weight"] for r in flagged) / len(rows) >= 0.02
    rare = anomaly_model.score(model, rows[-1])
    assert rare == {"score": None, "probability": None, "flagged": True, "rare": True}
    assert anomaly_model.score(model, record())["flagged"] is False


def test_a_rare_middle_value_is_flagged():
    """anomali-v1 (Isolation Forest on ordered bin numbers) scored every stored pattern with a
    middle bin, such as 'some visits without a referral', below its threshold."""
    rows = population() + [record(tanpa_rujukan=1.0)] * 400
    model = anomaly_model.fit(rows, target=0.05)
    middle, full = (anomaly_model.score(model, record(tanpa_rujukan=v)) for v in (0.5, 1.0))

    assert middle["flagged"] is True
    assert full["flagged"] is False
    assert middle["score"] > full["score"]


def test_the_exported_model_holds_only_cells_with_enough_records():
    rows = population() + [record(sesi=6, ahad_libur=2)] * 9
    model = anomaly_model.fit(rows)

    assert (
        anomali.cell_key(anomali.bin_features(record(sesi=6, ahad_libur=2)["anomaly_features"]))
        not in model["patterns"]
    )
    for group in model["groups"].values():
        assert group["n"] >= anomaly_model.MINIMUM_GROUP
        assert set(group["patterns"]) <= set(model["patterns"])
    assert_privacy_safe(model)


def test_fit_rejects_unsafe_minimums_and_missing_bins():
    with pytest.raises(ReferenceDataError, match="minimum_count"):
        anomaly_model.fit(population(), minimum=5)
    with pytest.raises(ReferenceDataError, match="fewer than"):
        anomaly_model.fit([record()] * 50)


def test_unknown_and_small_groups_fall_back():
    rows = population() + [record(age_group=None)] * 20
    model = anomaly_model.fit(rows)
    assert anomaly_model.group_of(model, record(age_group=None)) is None

    by_condition = anomaly_model.fit(
        population() + [record(condition="M54")] * 400 + [record(condition="G81")] * 20,
        context="condition",
    )
    assert anomaly_model.group_of(by_condition, record(condition="M54")) == "M54"
    assert anomaly_model.group_of(by_condition, record(condition="G81")) == anomaly_model.OTHER
    assert anomaly_model.group_of(by_condition, record(condition="Z99")) == anomaly_model.OTHER


def test_age_changes_what_counts_as_rare():
    children = [record(age_group="<18", sesi=8)] * 300
    rows = population() + children
    model = anomaly_model.fit(rows, alpha=10)

    child = anomaly_model.score(model, record(age_group="<18", sesi=8))
    adult = anomaly_model.score(model, record(age_group="60+", sesi=8))
    assert child["probability"] > adult["probability"]


def test_context_comparison_reports_every_candidate():
    rows = population()
    comparison = anomaly_model.compare_contexts(rows, rows)

    assert {r["context"] for r in comparison} == set(anomaly_model.CANDIDATE_CONTEXTS)
    assert all(r["log_likelihood"] <= 0 for r in comparison)
    assert anomaly_model.best_alpha(comparison, comparison) in anomaly_model.ALPHAS


def test_hospital_funnel_marks_hospitals_far_above_their_expected_count():
    model = {
        "groups": {"40-59": {"selected_rate": 0.03}},
        "selected_rate": 0.03,
        "overdispersion": 1.0,
    }
    busy = anomali.hospital_funnel(model, [("40-59", True)] * 20 + [("40-59", False)] * 40)
    usual = anomali.hospital_funnel(model, [("40-59", True)] * 2 + [("40-59", False)] * 58)

    assert busy["position"] == "above_99_8"
    assert usual["position"] == "within"
    assert (usual["expected"], usual["selected"]) == (1.8, 2)
    wider = anomali.hospital_funnel(
        model | {"overdispersion": 4.0}, [("40-59", True)] * 20 + [("40-59", False)] * 40
    )
    assert wider["z"] == pytest.approx(busy["z"] / 2, abs=0.01)


def test_reasons_name_the_age_group_and_never_say_fraud():
    model = anomaly_model.fit(population() + [record(sesi=6, ahad_libur=2)] * 20)
    why = anomali.reasons(model, record(sesi=6, ahad_libur=2)["anomaly_features"], "40-59")

    assert "pasien 40\u201359 tahun" in why["pattern"]
    assert {r["feature"] for r in why["rare_bins"]} == {"sesi", "ahad_libur"}
    assert not any(word in json.dumps(why).lower() for word in ("fraud", "curang"))


def test_behaviour_and_hospital_summaries_report_only_safe_counts():
    rows = population() + [record(sesi=6, ahad_libur=2, peer_group=(2,))] * 40
    model = anomaly_model.fit(rows)

    behaviour = anomaly_evaluation.behaviour(model, rows)
    hospitals = anomaly_evaluation.hospitals(model, rows)
    assert all(g["patient_months"] >= MINIMUM_SAFE_CELL_COUNT for g in behaviour["groups"])
    assert hospitals["peer_groups"] == 2
    assert hospitals["overdispersion"] >= 1.0
    assert_privacy_safe(behaviour | hospitals)


MODEL = tools.MODEL_DIR / "model-anomali-v2.json"
REAL = tools.REFERENCE_DIR / "anomali" / "anomali-nyata.json"
DEMO = tools.MODEL_DIR / "anomali_demo.json"


def counts(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("n", "patient_months"):
                yield child
            yield from counts(child)
    elif isinstance(value, list):
        for child in value:
            yield from counts(child)


def test_committed_model_is_a_safe_share_table():
    model = json.loads(MODEL.read_text(encoding="utf-8"))

    assert_privacy_safe(model)
    assert model["version"] == "anomali-v2"
    assert model["features"] == list(anomali.FEATURES)
    assert model["minimum_cell"] >= MINIMUM_SAFE_CELL_COUNT
    assert sum(model["patterns"].values()) <= 1.0
    assert all(
        math.isclose(sum(shares), 1.0, abs_tol=1e-4) for shares in model["marginal"].values()
    )
    for group in model["groups"].values():
        assert group["n"] >= anomaly_model.MINIMUM_GROUP
        assert set(group["patterns"]) <= set(model["patterns"])
    assert model["overdispersion"] >= 1.0


def test_committed_real_behaviour_reports_only_counts_of_ten_or_more():
    real = json.loads(REAL.read_text(encoding="utf-8"))

    assert_privacy_safe(real)
    assert all(n >= MINIMUM_SAFE_CELL_COUNT for n in counts(real))


def test_committed_demo_results_match_the_model():
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    demo = json.loads(DEMO.read_text(encoding="utf-8"))

    assert demo["versi"] == model["version"]
    assert demo["ringkas"]["model"] == 2
    for pid in ("P-M1", "P-M2"):
        assert demo["pasien"][pid]["dipilih"] == "model"
    assert demo["rs"]["RS01"]["position"] == "above_99_8"
    assert all(demo["rs"][rs]["position"] == "within" for rs in ("RS02", "RS03", "RS04", "RS05"))
