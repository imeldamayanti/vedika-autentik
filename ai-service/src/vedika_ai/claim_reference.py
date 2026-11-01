"""Offline, privacy-safe rehabilitation reference builder.

This module deliberately keeps Stata dependencies behind the build function so the
production API does not need them. Outputs contain aggregates and code descriptions only;
participant and visit identifiers are used transiently for counting and are never written.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0"
SOURCE_COLUMNS = (
    "PSTV01",
    "FKL03",
    "FKL10",
    "FKL11",
    "FKL18",
    "FKL18A",
    "FKL30",
    "FKL47",
    "FKL48",
)
REHABILITATION_CLINIC_LABELS = frozenset({"FIS", "IRM"})
MINIMUM_SAFE_CELL_COUNT = 10
TOP_CATEGORY_LIMIT = 100

_PHYSIOTHERAPY_PATTERN = re.compile(
    r"(?:physical therap|physiotherap|fisioterap|musculoskeletal exercise|"
    r"heat therapy|diathermy|electrotherap|manual therap)",
    re.IGNORECASE,
)
_FORBIDDEN_AGGREGATE_KEYS = frozenset(
    {
        "participant_id",
        "participant_ids",
        "patient_id",
        "patient_ids",
        "visit_id",
        "visit_ids",
        "pstv01",
        "pstv02",
        "fkl02",
        "raw_record",
        "raw_records",
    }
)


class ClaimReferenceError(ValueError):
    """Raised when a source or generated aggregate violates the reference contract."""


def is_physiotherapy_text(value: str) -> bool:
    """Return whether a diagnosis/procedure description is physiotherapy-specific."""

    return bool(_PHYSIOTHERAPY_PATTERN.search(value))


def visit_frequency_buckets(counts: Counter[tuple[int, str]]) -> dict[str, int]:
    """Aggregate participant-month counts without exposing participant identifiers."""

    buckets = {str(value): 0 for value in range(1, 9)}
    buckets.update({"9-12": 0, "13+": 0})
    for visits in counts.values():
        if visits <= 0:
            continue
        if visits <= 8:
            buckets[str(visits)] += 1
        elif visits <= 12:
            buckets["9-12"] += 1
        else:
            buckets["13+"] += 1
    return buckets


def assert_privacy_safe_aggregate(value: Any) -> None:
    """Reject identifier-bearing keys from an aggregate payload."""

    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in _FORBIDDEN_AGGREGATE_KEYS:
                raise ClaimReferenceError(f"Identifier-bearing output key is forbidden: {key}")
            assert_privacy_safe_aggregate(child)
    elif isinstance(value, list):
        for child in value:
            assert_privacy_safe_aggregate(child)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _safe_categories(
    counter: Counter[Any],
    *,
    minimum_count: int,
    limit: int,
) -> list[tuple[Any, int]]:
    return [
        (value, count)
        for value, count in counter.most_common()
        if count >= minimum_count
    ][:limit]


def _cost_summary(values: list[float], numpy: Any) -> dict[str, int | float | None]:
    if not values:
        return {"count": 0, "median": None, "p95": None, "sum": 0}
    array = numpy.asarray(values, dtype="float64")
    return {
        "count": int(array.size),
        "median": round(float(numpy.quantile(array, 0.5)), 2),
        "p95": round(float(numpy.quantile(array, 0.95)), 2),
        "sum": round(float(array.sum()), 2),
    }


def _rehabilitation_codes(metadata: Any) -> dict[int, str]:
    label_set = metadata.variable_to_label.get("FKL11")
    labels = metadata.value_labels.get(label_set, {}) if label_set else {}
    matches = {
        int(code): str(label).upper()
        for code, label in labels.items()
        if str(label).upper() in REHABILITATION_CLINIC_LABELS
    }
    if not matches:
        raise ClaimReferenceError("FKL11 has no FIS or IRM value labels in this release")
    return matches


def build_claim_reference(
    source: Path,
    output_dir: Path,
    *,
    year: int,
    chunk_size: int = 200_000,
    minimum_count: int = MINIMUM_SAFE_CELL_COUNT,
) -> dict[str, Any]:
    """Build aggregate rehabilitation reference files from one regular FKRTL Stata file."""

    try:
        import numpy
        import pandas
        import pyreadstat
    except ImportError as error:  # pragma: no cover - exercised through CLI environment
        raise ClaimReferenceError(
            "Data dependencies are missing; run with `uv run --group data`."
        ) from error

    source = source.resolve()
    if not source.is_file() or source.suffix.casefold() != ".dta":
        raise ClaimReferenceError("Source must be an existing .dta file")
    if chunk_size <= 0:
        raise ClaimReferenceError("chunk_size must be positive")
    if minimum_count < MINIMUM_SAFE_CELL_COUNT:
        raise ClaimReferenceError(
            f"minimum_count must be at least {MINIMUM_SAFE_CELL_COUNT}"
        )

    _, metadata = pyreadstat.read_dta(str(source), metadataonly=True)
    missing = sorted(set(SOURCE_COLUMNS) - set(metadata.column_names))
    if missing:
        raise ClaimReferenceError(f"Source is missing required columns: {', '.join(missing)}")
    rehabilitation_codes = _rehabilitation_codes(metadata)

    total_rows = 0
    outpatient_rows = 0
    rehabilitation_rows = 0
    physiotherapy_rows = 0
    participants: set[int] = set()
    participant_months: Counter[tuple[int, str]] = Counter()
    months: Counter[str] = Counter()
    clinics: Counter[str] = Counter()
    diagnoses: Counter[tuple[str, str]] = Counter()
    procedures: Counter[str] = Counter()
    billed_costs: list[float] = []
    verified_costs: list[float] = []
    date_min = None
    date_max = None

    chunks = pyreadstat.read_file_in_chunks(
        pyreadstat.read_dta,
        str(source),
        chunksize=chunk_size,
        usecols=list(SOURCE_COLUMNS),
    )
    for frame, _ in chunks:
        total_rows += len(frame)
        service_level = pandas.to_numeric(frame["FKL10"], errors="coerce")
        clinic_code = pandas.to_numeric(frame["FKL11"], errors="coerce")
        is_outpatient = service_level.eq(1)
        is_rehabilitation = is_outpatient & clinic_code.isin(rehabilitation_codes)
        outpatient_rows += int(is_outpatient.sum())
        rehabilitation_rows += int(is_rehabilitation.sum())

        descriptions = (
            frame["FKL18A"].fillna("").astype(str)
            + " "
            + frame["FKL30"].fillna("").astype(str)
        )
        is_physiotherapy = is_rehabilitation & descriptions.str.contains(
            _PHYSIOTHERAPY_PATTERN,
            regex=True,
        )
        physiotherapy_rows += int(is_physiotherapy.sum())
        subset = frame.loc[is_physiotherapy]
        if subset.empty:
            continue

        subset_codes = clinic_code.loc[is_physiotherapy].dropna().astype(int)
        clinics.update(rehabilitation_codes[code] for code in subset_codes)

        dates = pandas.to_datetime(subset["FKL03"], errors="coerce")
        valid_dates = dates.dropna()
        if not valid_dates.empty:
            chunk_min = valid_dates.min()
            chunk_max = valid_dates.max()
            date_min = chunk_min if date_min is None or chunk_min < date_min else date_min
            date_max = chunk_max if date_max is None or chunk_max > date_max else date_max

        month_values = dates.dt.to_period("M").astype(str)
        months.update(month_values[month_values != "NaT"].tolist())
        for participant, month in zip(subset["PSTV01"], month_values, strict=True):
            if pandas.notna(participant):
                participant_int = int(participant)
                participants.add(participant_int)
                if month != "NaT":
                    participant_months[(participant_int, month)] += 1

        for code, name in zip(subset["FKL18"], subset["FKL18A"], strict=True):
            code_text = "" if pandas.isna(code) else str(code).strip()
            name_text = "" if pandas.isna(name) else str(name).strip()
            if code_text or name_text:
                diagnoses[(code_text, name_text)] += 1
        procedures.update(
            value.strip()
            for value in subset["FKL30"].dropna().astype(str)
            if value.strip()
        )

        billed_costs.extend(
            pandas.to_numeric(subset["FKL47"], errors="coerce").dropna().astype(float).tolist()
        )
        verified_costs.extend(
            pandas.to_numeric(subset["FKL48"], errors="coerce").dropna().astype(float).tolist()
        )

    diagnosis_rows = [
        {"icd10": code, "diagnosis": name, "count": count}
        for (code, name), count in _safe_categories(
            diagnoses,
            minimum_count=minimum_count,
            limit=TOP_CATEGORY_LIMIT,
        )
    ]
    procedure_rows = [
        {"procedure": value, "count": count}
        for value, count in _safe_categories(
            procedures,
            minimum_count=minimum_count,
            limit=TOP_CATEGORY_LIMIT,
        )
    ]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "cohort": {
            "name": "outpatient_physiotherapy_reference",
            "year": year,
            "definition": (
                "Outpatient FKRTL rows in FIS/IRM clinics with physiotherapy-specific "
                "diagnosis or procedure descriptions."
            ),
            "clinic_value_labels": {
                str(code): label for code, label in sorted(rehabilitation_codes.items())
            },
        },
        "counts": {
            "source_rows": total_rows,
            "outpatient_rows": outpatient_rows,
            "outpatient_rehabilitation_rows": rehabilitation_rows,
            "outpatient_physiotherapy_rows": physiotherapy_rows,
            "unique_participants": len(participants),
            "participant_months": len(participant_months),
        },
        "date_range": {
            "minimum": date_min.date().isoformat() if date_min is not None else None,
            "maximum": date_max.date().isoformat() if date_max is not None else None,
        },
        "monthly_rows": dict(sorted(months.items())),
        "clinic_rows": dict(sorted(clinics.items())),
        "visits_per_participant_month": visit_frequency_buckets(participant_months),
        "costs": {
            "billed": _cost_summary(billed_costs, numpy),
            "verified": _cost_summary(verified_costs, numpy),
        },
        "privacy": {
            "minimum_category_count": minimum_count,
            "participant_identifiers_exported": False,
            "visit_identifiers_exported": False,
            "row_level_records_exported": False,
        },
    }
    assert_privacy_safe_aggregate(summary)

    data_dictionary = {
        "schema_version": SCHEMA_VERSION,
        "source_table": "FKRTL regular sample",
        "columns": [
            {
                "source": column,
                "description": metadata.column_names_to_labels.get(column, ""),
                "use": {
                    "PSTV01": "Transient unique participant and participant-month counts",
                    "FKL03": "Service date and month aggregates",
                    "FKL10": "Outpatient filter",
                    "FKL11": "FIS/IRM clinic filter resolved from Stata value labels",
                    "FKL18": "Aggregate ICD-10 frequency",
                    "FKL18A": "Physiotherapy filter and aggregate diagnosis frequency",
                    "FKL30": "Physiotherapy filter and aggregate procedure frequency",
                    "FKL47": "Aggregate billed-cost statistics",
                    "FKL48": "Aggregate verified-cost statistics",
                }[column],
                "exported_row_level": False,
            }
            for column in SOURCE_COLUMNS
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    diagnosis_path = output_dir / "diagnoses.csv"
    procedure_path = output_dir / "procedures.csv"
    dictionary_path = output_dir / "data-dictionary.json"
    _write_json(summary_path, summary)
    _write_csv(diagnosis_path, ("icd10", "diagnosis", "count"), diagnosis_rows)
    _write_csv(procedure_path, ("procedure", "count"), procedure_rows)
    _write_json(dictionary_path, data_dictionary)

    outputs = [summary_path, diagnosis_path, procedure_path, dictionary_path]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "source": {
            "filename": source.name,
            "sha256": sha256_file(source),
            "size_bytes": source.stat().st_size,
        },
        "parameters": {
            "year": year,
            "chunk_size": chunk_size,
            "minimum_category_count": minimum_count,
        },
        "outputs": [
            {
                "filename": path.name,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in outputs
        ],
        "privacy": summary["privacy"],
    }
    assert_privacy_safe_aggregate(manifest)
    _write_json(output_dir / "manifest.json", manifest)
    return manifest
