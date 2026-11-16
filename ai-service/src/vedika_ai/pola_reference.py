"""Offline, privacy-safe pattern reference builder for the "Skor pola" queue score.

Reads the regular FKRTL sample on the laptop and writes aggregates only: a binned feature
histogram, national marginals, rule-combination prevalence and per-hospital-type benchmarks.
Participant identifiers are used transiently for grouping and are never written. Feature
definitions come from data-uji-konfirmasi/tools/pola.py, the single shared definition.
"""

from __future__ import annotations

import importlib.util
import math
from collections import Counter, defaultdict
from datetime import date
from functools import lru_cache
from itertools import combinations
from pathlib import Path
from typing import Any

from loguru import logger

from vedika_ai.claim_reference import (
    _PHYSIOTHERAPY_PATTERN,
    MINIMUM_SAFE_CELL_COUNT,
    ClaimReferenceError,
    _rehabilitation_codes,
    _write_csv,
    _write_json,
    assert_privacy_safe_aggregate,
    sha256_file,
)

GENERATOR_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0"
SOURCE_COLUMNS = (
    "PSTV01",
    "PSTV15",
    "FKL03",
    "FKL06",
    "FKL07",
    "FKL08",
    "FKL09",
    "FKL10",
    "FKL11",
    "FKL18A",
    "FKL30",
)
HISTOGRAM_MONTHS = tuple(f"2024-{month:02d}" for month in range(7, 13))
MINIMUM_GROUP_MONTHS = 30
MINIMUM_GROUPS_FOR_PERCENTILES = 20
MINIMUM_TYPE_MONTHS = 100
NATIONAL = "Nasional"
POLA_PATH = Path(__file__).resolve().parents[3] / "data-uji-konfirmasi" / "tools" / "pola.py"


@lru_cache
def load_pola(path: Path = POLA_PATH) -> Any:
    """Load the shared stdlib-only feature module by path."""

    spec = importlib.util.spec_from_file_location("pola", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolation percentile (same definition as numpy's default)."""

    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
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


def patient_months(visits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One record per participant-month: shared features, rule indicators, weight, peer group.

    visits: dicts with peserta, tanggal (date), bobot, kelompok (hashable), tipe (label).
    There is no 2024 holiday list, so `ahad_libur` counts Sundays only.
    """

    pola = load_pola()
    per_participant: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for visit in visits:
        per_participant[visit["peserta"]].append(visit)

    records = []
    for rows in per_participant.values():
        per_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            per_month[row["tanggal"].strftime("%Y-%m")].append(row)
        active = set(per_month)
        for month, month_rows in per_month.items():
            features = pola.fitur_bulan([r["tanggal"] for r in month_rows], active, month, set())
            flags = pola.indikator(features)
            group, _ = Counter((r["kelompok"], r["tipe"]) for r in month_rows).most_common(1)[0]
            records.append(
                {
                    "bulan": month,
                    "fitur": features,
                    "bin": pola.bin_fitur(features),
                    "kombinasi": pola.kombinasi(*flags),
                    "indikator": flags,
                    "dipicu": sum(flags) >= 2,
                    "bobot": float(month_rows[0]["bobot"]),
                    "kelompok": group[0],
                    "tipe": group[1],
                }
            )
    return records


def _bands(*groups: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    """Band label -> fine bins; a single bin keeps its own label."""

    def label(group: tuple[str, ...]) -> str:
        if len(group) == 1:
            return group[0]
        if group[-1].endswith("+"):
            return f"{group[0]}+"
        return f"{group[0]}-{group[-1]}"

    return {label(group): group for group in groups}


# Coarser levels for histogram cells that stay under the minimum. Band edges sit on the rule
# thresholds (I1 sesi > 8, I2 maks_minggu >= 3, I3 episode >= 6, I4 ahad_libur > 0), so the
# indicators of every exported cell stay exact. Level 0 is pola.BIN itself.
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

    pola = load_pola()
    fine = {name: {label: (label,) for label in pola.BIN[name]} for name in pola.FITUR}
    return [fine, *COARSE_LEVELS]


def _band_of(level: dict[str, dict[str, tuple[str, ...]]], name: str, fine_label: str) -> str:
    return next(band for band, members in level[name].items() if fine_label in members)


def _histogram(records: list[dict[str, Any]], minimum: int) -> tuple[list[dict[str, Any]], dict]:
    """Multi-level histogram: each record is counted once, in the finest cell with >= minimum rows.

    Records in a fine cell under the minimum move to the next coarser level; whatever is still
    under the minimum at the coarsest level is suppressed.
    """

    pola = load_pola()
    levels = histogram_levels()
    remaining = [tuple(record["bin"][name] for name in pola.FITUR) for record in records]
    weights_in = [record["bobot"] for record in records]
    pending = list(range(len(records)))
    rows: list[dict[str, Any]] = []
    per_level = []
    for depth, level in enumerate(levels):
        cells: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for index in pending:
            key = tuple(
                _band_of(level, name, remaining[index][n]) for n, name in enumerate(pola.FITUR)
            )
            cells[key].append(index)
        kept = sorted(
            (key for key, members in cells.items() if len(members) >= minimum),
            key=lambda key: [list(level[name]).index(key[n]) for n, name in enumerate(pola.FITUR)],
        )
        for key in kept:
            rows.append(
                {
                    "tingkat": depth,
                    **dict(zip(pola.FITUR, key, strict=True)),
                    "n": len(cells[key]),
                    "bobot": round(sum(weights_in[i] for i in cells[key]), 2),
                }
            )
        per_level.append(len(kept))
        kept_set = set(kept)
        pending = [i for key, members in cells.items() if key not in kept_set for i in members]

    total_n = len(records)
    total_weight = sum(weights_in)
    suppression = {
        "cells_per_level": per_level,
        "rows_suppressed": len(pending),
        "row_share_suppressed": round(len(pending) / total_n, 4) if total_n else 0.0,
        "weight_share_suppressed": (
            round(sum(weights_in[i] for i in pending) / total_weight, 4) if total_weight else 0.0
        ),
    }
    return rows, suppression


def _marginal(records: list[dict[str, Any]], minimum: int) -> dict[str, Any]:
    """Weighted share per bin; bins under the minimum are merged into the neighbouring bin."""

    pola = load_pola()
    total = sum(record["bobot"] for record in records)
    shares: dict[str, dict[str, float]] = {}
    merged: dict[str, dict[str, str]] = {}
    for name in pola.FITUR:
        labels = list(pola.BIN[name])
        count = Counter(record["bin"][name] for record in records)
        weight: Counter[str] = Counter()
        for record in records:
            weight[record["bin"][name]] += record["bobot"]
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
        "populasi_bulan": sorted({record["bulan"] for record in records}),
        "bulan_pasien": len(records),
        "marginal": shares,
        "digabung": merged,
    }


def _combinations(records: list[dict[str, Any]], minimum: int) -> dict[str, Any]:
    total_n = len(records)
    total_weight = sum(record["bobot"] for record in records)
    counts = Counter(record["kombinasi"] for record in records)
    weights: Counter[str] = Counter()
    for record in records:
        weights[record["kombinasi"]] += record["bobot"]
    names = ["I1", "I2", "I3", "I4"]
    keys = ["-"] + ["+".join(c) for size in range(1, 5) for c in combinations(names, size)]
    ceiling = round(minimum / total_n, 6) if total_n else 1.0
    table = {
        key: (
            {"n": counts[key], "prevalensi": round(weights[key] / total_weight, 6)}
            if counts[key] >= minimum
            else {"prevalensi_maks": ceiling}
        )
        for key in keys
    }
    indicator = {
        name: round(sum(r["bobot"] for r in records if r["indikator"][n]) / total_weight, 6)
        for n, name in enumerate(names)
    }
    triggered = [r for r in records if r["dipicu"]]
    return {
        "bulan_pasien": total_n,
        "bulan_pasien_berbobot": round(total_weight),
        "indikator": indicator,
        "terpicu": round(sum(r["bobot"] for r in triggered) / total_weight, 6),
        "terpicu_per_bulan_nasional": round(sum(r["bobot"] for r in triggered) / 12),
        "kombinasi": table,
    }


def _benchmark(records: list[dict[str, Any]], minimum: int) -> dict[str, Any]:
    weight = sum(r["bobot"] for r in records)
    groups: dict[Any, list[bool]] = defaultdict(list)
    for record in records:
        groups[record["kelompok"]].append(record["dipicu"])
    rates = [100 * sum(g) / len(g) for g in groups.values() if len(g) >= MINIMUM_GROUP_MONTHS]
    sessions = [(r["fitur"]["sesi"], r["bobot"]) for r in records]
    result: dict[str, Any] = {
        "bulan_pasien": len(records),
        "persen_terpicu": round(100 * sum(r["bobot"] for r in records if r["dipicu"]) / weight, 2),
        "sesi_rata": round(sum(v * w for v, w in sessions) / weight, 2),
        "sesi_p90": weighted_percentile(sessions, 0.90),
        "sesi_p95": weighted_percentile(sessions, 0.95),
        "kelompok": len(rates),
    }
    if len(rates) >= MINIMUM_GROUPS_FOR_PERCENTILES:
        result.update(
            terpicu_p50=round(percentile(rates, 0.50), 1),
            terpicu_p90=round(percentile(rates, 0.90), 1),
            terpicu_p95=round(percentile(rates, 0.95), 1),
        )
    return result


def aggregate(
    visits: list[dict[str, Any]],
    *,
    minimum_count: int = MINIMUM_SAFE_CELL_COUNT,
    histogram_months: tuple[str, ...] = HISTOGRAM_MONTHS,
) -> dict[str, Any]:
    """Pure aggregation from visit records to the committed reference tables."""

    if minimum_count < MINIMUM_SAFE_CELL_COUNT:
        raise ClaimReferenceError(f"minimum_count must be at least {MINIMUM_SAFE_CELL_COUNT}")
    records = patient_months(visits)
    in_window = [r for r in records if r["bulan"] in histogram_months]
    histogram, suppression = _histogram(in_window, minimum_count)

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_type[record["tipe"]].append(record)
    benchmark = {NATIONAL: _benchmark(records, minimum_count)} if records else {}
    omitted = 0
    for label, rows in sorted(by_type.items()):
        if len(rows) < MINIMUM_TYPE_MONTHS:
            omitted += 1
            continue
        benchmark[label] = _benchmark(rows, minimum_count)

    group_sizes = Counter(record["kelompok"] for record in records)
    result = {
        "histogram": histogram,
        "marginal": _marginal(in_window, minimum_count),
        "kombinasi": _combinations(records, minimum_count),
        "pembanding_tipe": benchmark,
        "suppression": {
            "histogram": suppression,
            "types_omitted_under_100_patient_months": omitted,
        },
        "counts": {
            "outpatient_physiotherapy_rows": len(visits),
            "unique_participants": len({visit["peserta"] for visit in visits}),
            "participant_months": len(records),
            "participant_months_weighted": round(sum(r["bobot"] for r in records)),
            "histogram_participant_months": len(in_window),
            "peer_groups": len(group_sizes),
            "peer_groups_with_30_patient_months": sum(
                size >= MINIMUM_GROUP_MONTHS for size in group_sizes.values()
            ),
        },
    }
    assert_privacy_safe_aggregate(result)
    return result


def read_visits(source: Path, chunk_size: int) -> list[dict[str, Any]]:
    """Read the physiotherapy cohort from one regular FKRTL Stata file (needs the data group)."""

    try:
        import pandas
        import pyreadstat
    except ImportError as error:  # pragma: no cover - exercised through CLI environment
        raise ClaimReferenceError(
            "Data dependencies are missing; run with `uv run --group data`."
        ) from error

    _, metadata = pyreadstat.read_dta(str(source), metadataonly=True)
    missing = sorted(set(SOURCE_COLUMNS) - set(metadata.column_names))
    if missing:
        raise ClaimReferenceError(f"Source is missing required columns: {', '.join(missing)}")
    rehabilitation_codes = _rehabilitation_codes(metadata)
    type_labels = metadata.value_labels.get(metadata.variable_to_label.get("FKL09"), {})

    visits: list[dict[str, Any]] = []
    chunks = pyreadstat.read_file_in_chunks(
        pyreadstat.read_dta, str(source), chunksize=chunk_size, usecols=list(SOURCE_COLUMNS)
    )
    for frame, _ in chunks:
        is_outpatient = pandas.to_numeric(frame["FKL10"], errors="coerce").eq(1)
        clinic_code = pandas.to_numeric(frame["FKL11"], errors="coerce")
        descriptions = (
            frame["FKL18A"].fillna("").astype(str) + " " + frame["FKL30"].fillna("").astype(str)
        )
        is_physiotherapy = (
            is_outpatient
            & clinic_code.isin(rehabilitation_codes)
            & descriptions.str.contains(_PHYSIOTHERAPY_PATTERN, regex=True)
        )
        subset = frame.loc[is_physiotherapy]
        dates = pandas.to_datetime(subset["FKL03"], errors="coerce")
        codes = subset[["FKL06", "FKL07", "FKL08", "FKL09"]].fillna(-1).astype(int)
        for participant, day, weight, group in zip(
            subset["PSTV01"],
            dates,
            subset["PSTV15"],
            codes.itertuples(index=False, name=None),
            strict=True,
        ):
            if pandas.isna(participant) or pandas.isna(day):
                continue
            visits.append(
                {
                    "peserta": int(participant),
                    "tanggal": date(day.year, day.month, day.day),
                    "bobot": float(weight),
                    "kelompok": group,
                    "tipe": str(type_labels.get(group[3], f"Tipe {group[3]}")),
                }
            )
    return visits


def build_pattern_reference(
    source: Path,
    output_dir: Path,
    *,
    chunk_size: int = 200_000,
    minimum_count: int = MINIMUM_SAFE_CELL_COUNT,
) -> dict[str, Any]:
    """Build the aggregate pattern reference from one regular FKRTL Stata file."""

    source = source.resolve()
    if not source.is_file() or source.suffix.casefold() != ".dta":
        raise ClaimReferenceError("Source must be an existing .dta file")
    if chunk_size <= 0:
        raise ClaimReferenceError("chunk_size must be positive")

    visits = read_visits(source, chunk_size)
    result = aggregate(visits, minimum_count=minimum_count)
    logger.info("Cohort: {}", result["counts"])
    logger.info(
        "Indicator prevalence {} | triggered {}",
        result["kombinasi"]["indikator"],
        result["kombinasi"]["terpicu"],
    )
    logger.info("Histogram suppression: {}", result["suppression"]["histogram"])
    logger.info("National benchmark: {}", result["pembanding_tipe"][NATIONAL])

    pola = load_pola()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        name: output_dir / name
        for name in ("histogram.csv", "marginal.json", "kombinasi.json", "pembanding_tipe.json")
    }
    _write_csv(
        paths["histogram.csv"], ("tingkat", *pola.FITUR, "n", "bobot"), result["histogram"]
    )
    _write_json(paths["marginal.json"], result["marginal"])
    _write_json(paths["kombinasi.json"], result["kombinasi"])
    _write_json(paths["pembanding_tipe.json"], result["pembanding_tipe"])

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generated_on": date.today().isoformat(),
        "source": {
            "filename": source.name,
            "sha256": sha256_file(source),
            "size_bytes": source.stat().st_size,
        },
        "parameters": {
            "chunk_size": chunk_size,
            "minimum_category_count": minimum_count,
            "histogram_months": list(HISTOGRAM_MONTHS),
            "minimum_group_patient_months": MINIMUM_GROUP_MONTHS,
            "minimum_groups_for_percentiles": MINIMUM_GROUPS_FOR_PERCENTILES,
            "minimum_type_patient_months": MINIMUM_TYPE_MONTHS,
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
        "outputs": [
            {"filename": path.name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
            for path in paths.values()
        ],
        "privacy": {
            "minimum_category_count": minimum_count,
            "participant_identifiers_exported": False,
            "visit_identifiers_exported": False,
            "row_level_records_exported": False,
        },
    }
    assert_privacy_safe_aggregate(manifest)
    _write_json(output_dir / "manifest.json", manifest)
    return manifest
