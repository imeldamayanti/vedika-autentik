"""Training anomali-v2: weighted pattern rarity among patients of the same age group.

The scorer is data-uji-konfirmasi/tools/anomali.py; this module only counts, chooses the smoothing
strength on a later year, and sets the threshold. The exported model holds shares of cells with at
least `minimum` participant-months and nothing else.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from vedika_ai.ml import tools
from vedika_ai.ml.privacy import MINIMUM_SAFE_CELL_COUNT, ReferenceDataError, require_safe_minimum

VERSION = "anomali-v2"
TARGET_SHARE = 0.015
ALPHAS = (10, 50, 200, 1000)
CONTEXT = "age_group"
# Compared on held-out data before choosing CONTEXT; see compare_contexts.
CANDIDATE_CONTEXTS = (None, "age_group", "condition")
MINIMUM_GROUP = 300
MINIMUM_PEER_MONTHS = 30
WINSORIZE = 0.1
OTHER = "lain"
UNSEEN_FLOOR = 1e-5


def cell(record: dict[str, Any]) -> str:
    anomali = tools.anomali()
    return anomali.cell_key(anomali.bin_features(record["anomaly_features"]))


def total_weight(records: list[dict[str, Any]]) -> float:
    return sum(r["weight"] for r in records)


def _shares(records: list[dict[str, Any]], key, minimum: int) -> dict[Any, float]:
    """Weighted share of every key held by at least `minimum` records."""

    count, weight = Counter(), Counter()
    for r in records:
        k = key(r)
        count[k] += 1
        weight[k] += r["weight"]
    total = total_weight(records)
    return {k: round(weight[k] / total, 6) for k in sorted(weight) if count[k] >= minimum}


def _bin_key(position: int):
    anomali = tools.anomali()
    return lambda r: anomali.bin_features(r["anomaly_features"])[position]


def group_of(model: dict[str, Any], record: dict[str, Any]) -> str | None:
    """The model group of a record: its context value, `lain` for a small one, None when unknown."""

    if model["context"] is None or record[model["context"]] is None:
        return None
    value = record[model["context"]]
    if value in model["groups"]:
        return value
    return OTHER if OTHER in model["groups"] else None


def score(model: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    return tools.anomali().score(model, record["anomaly_features"], group_of(model, record))


def _threshold(scored: list[tuple[float | None, float]], target: float) -> float:
    """Lowest score at which whole score levels, rare patterns first, reach `target` of the weight.

    When rare patterns alone reach it, the threshold sits just above every stored score.
    """

    by_score: dict[float, float] = defaultdict(float)
    for value, weight in scored:
        by_score[math.inf if value is None else value] += weight
    goal = target * sum(by_score.values())
    cumulative = 0.0
    for value in sorted(by_score, reverse=True):
        cumulative += by_score[value]
        if cumulative >= goal:
            if math.isinf(value):
                return round(max(v for v in by_score if not math.isinf(v)) + 0.0001, 4)
            return value
    return min(by_score)


def fit(
    records: list[dict[str, Any]],
    *,
    context: str | None = CONTEXT,
    alpha: float = 200,
    minimum: int = MINIMUM_SAFE_CELL_COUNT,
    target: float = TARGET_SHARE,
) -> dict[str, Any]:
    anomali = tools.anomali()
    require_safe_minimum(minimum)

    marginal = {}
    for position, name in enumerate(anomali.FEATURES):
        shares = _shares(records, _bin_key(position), minimum)
        size = len(anomali.BIN_UPPER_BOUNDS[name]) + 1
        if len(shares) < size:
            raise ReferenceDataError(f"A bin of {name} has fewer than {minimum} records.")
        marginal[name] = [shares[b] for b in range(size)]

    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if context is not None:
        sizes = Counter(r[context] for r in records if r[context] is not None)
        for r in records:
            if r[context] is not None:
                by_group[r[context] if sizes[r[context]] >= MINIMUM_GROUP else OTHER].append(r)
    groups = {
        name: {
            "n": len(rows),
            "patterns": _shares(rows, cell, minimum),
            "marginal": {
                feature: {str(b): share for b, share in _shares(rows, _bin_key(i), minimum).items()}
                for i, feature in enumerate(anomali.FEATURES)
            },
        }
        for name, rows in sorted(by_group.items())
        if len(rows) >= minimum
    }

    model = {
        "version": VERSION,
        "method": "weighted pattern rarity per context group, shrunk towards national shares",
        "features": list(anomali.FEATURES),
        "bin_upper_bounds": {k: list(v) for k, v in anomali.BIN_UPPER_BOUNDS.items()},
        "minimum_cell": minimum,
        "years": _year_span(records),
        "context": context,
        "alpha": alpha,
        "target_share": target,
        "threshold": 0.0,
        "patterns": _shares(records, cell, minimum),
        "marginal": marginal,
        "groups": groups,
    }
    scores = [(score(model, r)["score"], r["weight"]) for r in records]
    model["threshold"] = _threshold(scores, target)

    selected = [r["triggered"] or score(model, r)["flagged"] for r in records]
    model["selected_rate"] = round(sum(selected) / len(selected), 6)
    by_group: dict[str | None, list[bool]] = defaultdict(list)
    for r, chosen in zip(records, selected, strict=True):
        by_group[group_of(model, r)].append(chosen)
    for name in groups:
        groups[name]["selected_rate"] = round(sum(by_group[name]) / len(by_group[name]), 6)
    model["overdispersion"] = 1.0
    model["overdispersion"] = overdispersion(model, records, selected)
    return model


def peer_rows(
    model: dict[str, Any], records: list[dict[str, Any]], selected: list[bool]
) -> list[list[tuple]]:
    """(group, selected) rows of every peer group with enough participant-months."""

    by_peer: dict[Any, list[tuple]] = defaultdict(list)
    for r, chosen in zip(records, selected, strict=True):
        by_peer[r["peer_group"]].append((group_of(model, r), chosen))
    return [rows for rows in by_peer.values() if len(rows) >= MINIMUM_PEER_MONTHS]


def overdispersion(
    model: dict[str, Any], records: list[dict[str, Any]], selected: list[bool]
) -> float:
    """Multiplicative overdispersion of the hospital funnel: mean squared winsorized z, at least 1.

    Hospitals vary more than chance around their age-expected selection count; without this,
    far more of them land outside the funnel limits than the limits promise.
    """

    anomali = tools.anomali()
    z = sorted(
        anomali.hospital_funnel(model, rows)["z"] for rows in peer_rows(model, records, selected)
    )
    if not z:
        return 1.0
    cut = int(WINSORIZE * len(z))
    low, high = z[cut], z[-cut - 1]
    return round(max(1.0, sum(min(max(v, low), high) ** 2 for v in z) / len(z)), 4)


def _year_span(records: list[dict[str, Any]]) -> str:
    years = sorted({r["month"][:4] for r in records})
    return years[0] if len(years) == 1 else f"{years[0]}\u2013{years[-1]}"


def held_out_log_likelihood(model: dict[str, Any], records: list[dict[str, Any]]) -> float:
    """Weighted mean ln p of unseen records; patterns outside the table get a floor."""

    anomali = tools.anomali()
    total = 0.0
    for r in records:
        p = anomali.probability(model, r["anomaly_features"], group_of(model, r))
        total += r["weight"] * math.log(p or UNSEEN_FLOOR)
    return round(total / total_weight(records), 4)


def compare_contexts(
    train: list[dict[str, Any]], test: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Held-out log-likelihood of every candidate context and smoothing (higher is better)."""

    rows = []
    for context in CANDIDATE_CONTEXTS:
        for alpha in ALPHAS if context else ALPHAS[:1]:
            model = fit(train, context=context, alpha=alpha)
            rows.append(
                {
                    "context": context,
                    "alpha": alpha,
                    "groups": len(model["groups"]),
                    "log_likelihood": held_out_log_likelihood(model, test),
                }
            )
    return rows


def best_alpha(*comparisons: list[dict[str, Any]], context: str = CONTEXT) -> float:
    """Smoothing strength with the highest held-out log-likelihood summed over the comparisons."""

    total: dict[float, float] = defaultdict(float)
    for comparison in comparisons:
        for row in comparison:
            if row["context"] == context:
                total[row["alpha"]] += row["log_likelihood"]
    return max(total, key=total.get)
