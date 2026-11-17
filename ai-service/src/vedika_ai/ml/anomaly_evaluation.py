"""How anomali-v2 behaves on real data. No fraud labels exist, so these are behaviour, not accuracy.

Every count written out is at least MINIMUM_SAFE_CELL_COUNT; smaller ones are dropped.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from vedika_ai.ml import tools
from vedika_ai.ml.anomaly_model import (
    MINIMUM_PEER_MONTHS,
    cell,
    fit,
    group_of,
    peer_rows,
    score,
    total_weight,
)
from vedika_ai.ml.privacy import MINIMUM_SAFE_CELL_COUNT

# Upper tail above the funnel limits if every hospital behaved as its age mix predicts.
NULL_SHARE = {"above_95": 0.025, "above_99_8": 0.001}


def percent(records: list[dict[str, Any]], total: float) -> float:
    return round(100 * total_weight(records) / total, 2)


def jaccard(a: set, b: set) -> float:
    return round(len(a & b) / len(a | b), 3) if a | b else 1.0


def flagged_indices(model: dict[str, Any], records: list[dict[str, Any]]) -> set[int]:
    return {i for i, r in enumerate(records) if score(model, r)["flagged"]}


def _group_row(
    name: str, rows: list[dict[str, Any]], total: float, months: int
) -> dict[str, Any] | None:
    if len(rows) < MINIMUM_SAFE_CELL_COUNT:
        return None
    return {
        "group": name,
        "patient_months": len(rows),
        "visits": sum(r["features"]["sesi"] for r in rows),
        "percent": percent(rows, total),
        "per_month_national": round(total_weight(rows) / months),
    }


def behaviour(model: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    anomali = tools.anomali()
    total = total_weight(records)
    months = sorted({r["month"] for r in records})
    flagged = flagged_indices(model, records)
    is_flagged = [i in flagged for i in range(len(records))]

    def pick(keep):
        return [r for r, f in zip(records, is_flagged, strict=True) if keep(r, f)]

    groups = [
        _group_row("flagged_by_model", pick(lambda r, f: f), total, len(months)),
        _group_row("triggered_by_rules", pick(lambda r, f: r["triggered"]), total, len(months)),
        _group_row("both", pick(lambda r, f: f and r["triggered"]), total, len(months)),
        _group_row("model_only", pick(lambda r, f: f and not r["triggered"]), total, len(months)),
        _group_row("rules_only", pick(lambda r, f: r["triggered"] and not f), total, len(months)),
        _group_row("called", pick(lambda r, f: f or r["triggered"]), total, len(months)),
    ]

    model_only = pick(lambda r, f: f and not r["triggered"])
    first_reason = Counter()
    for r in model_only:
        rare_bins = anomali.reasons(model, r["anomaly_features"], group_of(model, r))["rare_bins"]
        first_reason[rare_bins[0]["feature"] if rare_bins else "pattern"] += 1
    top_cells = Counter(cell(r) for r in model_only)

    by_month: dict[str, list[bool]] = defaultdict(list)
    by_age: dict[str, list[tuple[dict[str, Any], bool]]] = defaultdict(list)
    for r, f in zip(records, is_flagged, strict=True):
        by_month[r["month"]].append(f)
        by_age[r["age_group"] or "tidak diketahui"].append((r, f))
    monthly = [round(100 * sum(v) / len(v), 2) for v in by_month.values()]

    return {
        "patient_months": len(records),
        "months": len(months),
        "groups": [g for g in groups if g],
        "first_reason_model_only": [
            {"feature": k, "patient_months": n}
            for k, n in first_reason.most_common()
            if n >= MINIMUM_SAFE_CELL_COUNT
        ],
        "top_patterns_model_only": [
            {
                "pattern": [
                    anomali.BIN_LABELS[name][int(b)]
                    for name, b in zip(anomali.FEATURES, key.split("|"), strict=True)
                ],
                "patient_months": n,
            }
            for key, n in top_cells.most_common(5)
            if n >= MINIMUM_SAFE_CELL_COUNT
        ],
        "monthly_percent": {"low": min(monthly), "high": max(monthly)},
        "by_age_group": [
            {
                "age_group": age,
                "patient_months": len(rows),
                "percent_flagged": percent(
                    [r for r, f in rows if f], total_weight([r for r, _ in rows])
                ),
            }
            for age, rows in sorted(by_age.items())
            if len(rows) >= MINIMUM_SAFE_CELL_COUNT
        ],
    }


def over_time(
    train: list[dict[str, Any]], test: list[dict[str, Any]], **fit_args
) -> dict[str, Any]:
    """Fit on an earlier year, apply to a later one, compare with the later year's own model."""

    past, present = fit(train, **fit_args), fit(test, **fit_args)
    total = total_weight(test)
    by_past, by_present = flagged_indices(past, test), flagged_indices(present, test)
    unknown = [r for r in test if cell(r) not in past["patterns"]]
    return {
        "train_years": sorted({r["month"][:4] for r in train}),
        "test_years": sorted({r["month"][:4] for r in test}),
        "percent_flagged_by_past_model": percent([test[i] for i in by_past], total),
        "percent_flagged_by_own_model": percent([test[i] for i in by_present], total),
        "jaccard": jaccard(by_past, by_present),
        "percent_model_only_by_past_model": percent(
            [test[i] for i in by_past if not test[i]["triggered"]], total
        ),
        "percent_patterns_unknown_to_past_model": percent(unknown, total),
    }


def outside(
    name: str, records: list[dict[str, Any]], model: dict[str, Any]
) -> dict[str, Any] | None:
    """Apply the final model to a disease-specific sample it was not trained on."""

    if len(records) < MINIMUM_SAFE_CELL_COUNT:
        return None
    total = total_weight(records)
    flagged = flagged_indices(model, records)
    return {
        "sample": name,
        "patient_months": len(records),
        "years": sorted({r["month"][:4] for r in records}),
        "percent_flagged": percent([records[i] for i in flagged], total),
        "percent_triggered": percent([r for r in records if r["triggered"]], total),
        "percent_model_only": percent(
            [records[i] for i in flagged if not records[i]["triggered"]], total
        ),
    }


def hospitals(model: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    """Funnel plot over peer groups: selected (rules OR model) against the number expected from age.

    Counts only; no peer-group identity is returned.
    """

    anomali = tools.anomali()
    selected = [r["triggered"] or score(model, r)["flagged"] for r in records]
    funnels = [anomali.hospital_funnel(model, rows) for rows in peer_rows(model, records, selected)]
    selected = sum(f["selected"] for f in funnels)
    positions = Counter(f["position"] for f in funnels)
    above_95 = positions["above_95"] + positions["above_99_8"]
    return {
        "peer_groups": len(funnels),
        "minimum_patient_months": MINIMUM_PEER_MONTHS,
        "overdispersion": model["overdispersion"],
        "above_95": above_95,
        "above_99_8": positions["above_99_8"],
        "expected_by_chance": {k: round(v * len(funnels), 1) for k, v in NULL_SHARE.items()},
        "percent_selected_in_above_99_8": round(
            100 * sum(f["selected"] for f in funnels if f["position"] == "above_99_8") / selected, 1
        )
        if selected
        else 0.0,
    }
