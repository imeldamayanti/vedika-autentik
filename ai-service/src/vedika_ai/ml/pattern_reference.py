"""National aggregates behind the pola-v1 queue score.

Histogram, marginals, rule combinations, and hospital-type benchmarks.

Output keys are Indonesian because the trainer, the backend, and the tests read them as they are.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any

from loguru import logger

from vedika_ai.ml import tools
from vedika_ai.ml.cohort import check_source, patient_months, read_visits
from vedika_ai.ml.privacy import (
    MINIMUM_SAFE_CELL_COUNT,
    PRIVACY_FLAGS,
    ReferenceDataError,
    assert_privacy_safe,
    file_entry,
    require_safe_minimum,
    write_csv,
    write_json,
)

GENERATOR_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0"
HISTOGRAM_MONTHS = tuple(f"2024-{month:02d}" for month in range(7, 13))
MINIMUM_GROUP_MONTHS = 30
MINIMUM_GROUPS_FOR_PERCENTILES = 20
MINIMUM_TYPE_MONTHS = 100
# A hospital type whose largest peer group holds more than half of its patient-months is left out:
# its figures would mostly describe one hospital group.
MAXIMUM_DOMINANT_GROUP_SHARE = 0.5
NATIONAL = "Nasional"
RULES = ("I1", "I2", "I3", "I4")


def percentile(values: list[float], q: float) -> float:
    """Linear interpolation, as numpy's default."""

    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def weighted_percentile(pairs: list[tuple[float, float]], q: float) -> float:
    """Smallest value whose cumulative weight share reaches q."""

    total = sum(weight for _, weight in pairs)
    cumulative = 0.0
    for value, weight in sorted(pairs):
        cumulative += weight
        if cumulative >= q * total:
            return value
    return max(value for value, _ in pairs)


def _bands(*groups: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    def label(group: tuple[str, ...]) -> str:
        if len(group) == 1:
            return group[0]
        return f"{group[0]}+" if group[-1].endswith("+") else f"{group[0]}-{group[-1]}"

    return {label(group): group for group in groups}


# Coarser levels for histogram cells under the minimum. Band edges sit on the rule thresholds
# (sesi > 8, maks_minggu >= 3, episode >= 6, ahad_libur > 0), so every exported cell keeps exact
# indicators. Level 0 is pola.BIN itself.
COARSE_LEVELS = (
    {
        "sesi": _bands(
            ("1", "2"), ("3", "4"), ("5", "6"), ("7", "8"), ("9", "10", "11", "12"), ("13+",)
        ),
        "maks_minggu": _bands(("1",), ("2",), ("3",), ("4", "5", "6+")),
        "ahad_libur": _bands(("0",), ("1",), ("2+",)),
        "episode": _bands(("1",), ("2", "3"), ("4", "5"), ("6",), ("7+",)),
    },
    {
        "sesi": _bands(("1", "2", "3", "4"), ("5", "6", "7", "8"), ("9", "10", "11", "12", "13+")),
        "maks_minggu": _bands(("1", "2"), ("3", "4", "5", "6+")),
        "ahad_libur": _bands(("0",), ("1", "2+")),
        "episode": _bands(("1", "2", "3", "4", "5"), ("6", "7+")),
    },
)


def histogram_levels() -> list[dict[str, dict[str, tuple[str, ...]]]]:
    """All levels, finest first: feature -> band label -> fine bins."""

    pola = tools.pola()
    fine = {name: {label: (label,) for label in pola.BIN[name]} for name in pola.FITUR}
    return [fine, *COARSE_LEVELS]


def _histogram(records: list[dict[str, Any]], minimum: int) -> tuple[list[dict[str, Any]], dict]:
    """Each record counts once, in the finest cell with >= minimum rows; the rest is suppressed."""

    features = tools.pola().FITUR
    bins = [tuple(r["bins"][name] for name in features) for r in records]
    weights = [r["weight"] for r in records]
    pending = list(range(len(records)))
    rows: list[dict[str, Any]] = []
    cells_per_level = []
    for depth, level in enumerate(histogram_levels()):
        band_of = {
            name: {fine: band for band, members in level[name].items() for fine in members}
            for name in features
        }
        cells: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for i in pending:
            cells[tuple(band_of[name][bins[i][n]] for n, name in enumerate(features))].append(i)
        kept = sorted(
            (key for key, members in cells.items() if len(members) >= minimum),
            key=lambda key: [list(level[name]).index(key[n]) for n, name in enumerate(features)],
        )
        for key in kept:
            rows.append(
                {
                    "tingkat": depth,
                    **dict(zip(features, key, strict=True)),
                    "n": len(cells[key]),
                    "bobot": round(sum(weights[i] for i in cells[key]), 2),
                }
            )
        cells_per_level.append(len(kept))
        kept_keys = set(kept)
        pending = [i for key, members in cells.items() if key not in kept_keys for i in members]

    total_weight = sum(weights)
    suppression = {
        "cells_per_level": cells_per_level,
        "rows_suppressed": len(pending),
        "row_share_suppressed": round(len(pending) / len(records), 4) if records else 0.0,
        "weight_share_suppressed": (
            round(sum(weights[i] for i in pending) / total_weight, 4) if total_weight else 0.0
        ),
    }
    return rows, suppression


def _marginal(records: list[dict[str, Any]], minimum: int) -> dict[str, Any]:
    """Weighted share per bin; a bin under the minimum merges into its neighbour."""

    pola = tools.pola()
    total = sum(r["weight"] for r in records)
    shares: dict[str, dict[str, float]] = {}
    merged: dict[str, dict[str, str]] = {}
    for name in pola.FITUR:
        labels = list(pola.BIN[name])
        count = Counter(r["bins"][name] for r in records)
        weight: Counter[str] = Counter()
        for r in records:
            weight[r["bins"][name]] += r["weight"]
        merged[name] = {}
        while len(labels) > 1 and (small := next((b for b in labels if count[b] < minimum), None)):
            position = labels.index(small)
            target = labels[position - 1] if position else labels[1]
            count[target] += count.pop(small, 0)
            weight[target] += weight.pop(small, 0.0)
            merged[name] = {k: (target if v == small else v) for k, v in merged[name].items()}
            merged[name][small] = target
            labels.remove(small)
        shares[name] = {label: round(weight[label] / total, 6) for label in labels} if total else {}
    return {
        "populasi_bulan": sorted({r["month"] for r in records}),
        "bulan_pasien": len(records),
        "marginal": shares,
        "digabung": merged,
    }


def _rule_combinations(records: list[dict[str, Any]], minimum: int) -> dict[str, Any]:
    total_n = len(records)
    total_weight = sum(r["weight"] for r in records)
    counts = Counter(r["combination"] for r in records)
    weights: Counter[str] = Counter()
    for r in records:
        weights[r["combination"]] += r["weight"]
    keys = ["-"] + ["+".join(c) for size in range(1, 5) for c in combinations(RULES, size)]
    ceiling = round(minimum / total_n, 6) if total_n else 1.0
    triggered_weight = sum(r["weight"] for r in records if r["triggered"])
    return {
        "bulan_pasien": total_n,
        "bulan_pasien_berbobot": round(total_weight),
        "indikator": {
            name: round(sum(r["weight"] for r in records if r["indicators"][n]) / total_weight, 6)
            for n, name in enumerate(RULES)
        },
        "terpicu": round(triggered_weight / total_weight, 6),
        "terpicu_per_bulan_nasional": round(triggered_weight / 12),
        "kombinasi": {
            key: (
                {"n": counts[key], "prevalensi": round(weights[key] / total_weight, 6)}
                if counts[key] >= minimum
                else {"prevalensi_maks": ceiling}
            )
            for key in keys
        },
    }


def _benchmark(records: list[dict[str, Any]]) -> dict[str, Any]:
    weight = sum(r["weight"] for r in records)
    by_group: dict[Any, list[bool]] = defaultdict(list)
    for r in records:
        by_group[r["peer_group"]].append(r["triggered"])
    rates = [100 * sum(g) / len(g) for g in by_group.values() if len(g) >= MINIMUM_GROUP_MONTHS]
    sessions = [(r["features"]["sesi"], r["weight"]) for r in records]
    result: dict[str, Any] = {
        "bulan_pasien": len(records),
        "persen_terpicu": round(
            100 * sum(r["weight"] for r in records if r["triggered"]) / weight, 2
        ),
        "sesi_rata": round(sum(v * w for v, w in sessions) / weight, 2),
        "sesi_p90": weighted_percentile(sessions, 0.90),
        "sesi_p95": weighted_percentile(sessions, 0.95),
        "kelompok": len(rates),
    }
    if len(rates) >= MINIMUM_GROUPS_FOR_PERCENTILES:
        result |= {
            "terpicu_p50": round(percentile(rates, 0.50), 1),
            "terpicu_p90": round(percentile(rates, 0.90), 1),
            "terpicu_p95": round(percentile(rates, 0.95), 1),
        }
    return result


def aggregate(
    visits: list[dict[str, Any]],
    *,
    minimum_count: int = MINIMUM_SAFE_CELL_COUNT,
    histogram_months: tuple[str, ...] = HISTOGRAM_MONTHS,
) -> dict[str, Any]:
    """Visits -> the committed reference tables."""

    require_safe_minimum(minimum_count)
    records = patient_months(visits)
    windowed = [r for r in records if r["month"] in histogram_months]
    histogram, suppression = _histogram(windowed, minimum_count)

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_type[r["hospital_type"]].append(r)
    benchmarks = {NATIONAL: _benchmark(records)} if records else {}
    small_types = dominated_types = 0
    for label, rows in sorted(by_type.items()):
        if len(rows) < MINIMUM_TYPE_MONTHS:
            small_types += 1
            continue
        largest = Counter(r["peer_group"] for r in rows).most_common(1)[0][1]
        if largest / len(rows) > MAXIMUM_DOMINANT_GROUP_SHARE:
            dominated_types += 1
            continue
        benchmarks[label] = _benchmark(rows)

    group_sizes = Counter(r["peer_group"] for r in records)
    result = {
        "histogram": histogram,
        "marginal": _marginal(windowed, minimum_count),
        "kombinasi": _rule_combinations(records, minimum_count),
        "pembanding_tipe": benchmarks,
        "suppression": {
            "histogram": suppression,
            "types_omitted_under_100_patient_months": small_types,
            "types_omitted_one_group_over_half": dominated_types,
        },
        "counts": {
            "outpatient_physiotherapy_rows": len(visits),
            "unique_participants": len({v["participant"] for v in visits}),
            "participant_months": len(records),
            "participant_months_weighted": round(sum(r["weight"] for r in records)),
            "histogram_participant_months": len(windowed),
            "peer_groups": len(group_sizes),
            "peer_groups_with_30_patient_months": sum(
                size >= MINIMUM_GROUP_MONTHS for size in group_sizes.values()
            ),
        },
    }
    assert_privacy_safe(result)
    return result


def build_pattern_reference(
    source: Path,
    output_dir: Path,
    *,
    chunk_size: int = 200_000,
    minimum_count: int = MINIMUM_SAFE_CELL_COUNT,
) -> dict[str, Any]:
    source = check_source(source)
    if chunk_size <= 0:
        raise ReferenceDataError("chunk_size must be positive")
    result = aggregate(read_visits(source, chunk_size=chunk_size), minimum_count=minimum_count)
    logger.info("Cohort: {}", result["counts"])
    logger.info(
        "Triggered {} | indicators {}",
        result["kombinasi"]["terpicu"],
        result["kombinasi"]["indikator"],
    )
    logger.info("Histogram suppression: {}", result["suppression"]["histogram"])

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        name: output_dir / name
        for name in ("histogram.csv", "marginal.json", "kombinasi.json", "pembanding_tipe.json")
    }
    write_csv(
        paths["histogram.csv"], ("tingkat", *tools.pola().FITUR, "n", "bobot"), result["histogram"]
    )
    write_json(paths["marginal.json"], result["marginal"])
    write_json(paths["kombinasi.json"], result["kombinasi"])
    write_json(paths["pembanding_tipe.json"], result["pembanding_tipe"])

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generated_on": date.today().isoformat(),
        "source": file_entry(source),
        "parameters": {
            "chunk_size": chunk_size,
            "minimum_category_count": minimum_count,
            "histogram_months": list(HISTOGRAM_MONTHS),
            "minimum_group_patient_months": MINIMUM_GROUP_MONTHS,
            "minimum_groups_for_percentiles": MINIMUM_GROUPS_FOR_PERCENTILES,
            "minimum_type_patient_months": MINIMUM_TYPE_MONTHS,
            "dominant_group_share_limit": MAXIMUM_DOMINANT_GROUP_SHARE,
            "histogram_levels": [
                {name: list(bands) for name, bands in level.items()} for level in COARSE_LEVELS
            ],
            "holiday_list": "none (ahad_libur and I4 count Sundays only in the 2024 data)",
            "peer_group": "FKL06 + FKL07 + FKL08 + FKL09 of most visits in the patient-month",
            "episode_note": (
                "Months before 2024-01 are not in the source, so I3 is undercounted in the "
                "all-month prevalence; the histogram uses 2024-07 to 2024-12 only."
            ),
        },
        "counts": result["counts"],
        "suppression": result["suppression"],
        "outputs": [file_entry(path) for path in paths.values()],
        "privacy": PRIVACY_FLAGS | {"minimum_category_count": minimum_count},
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest
