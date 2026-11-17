"""Descriptive reference of the physiotherapy cohort (rehab-2024): counts, codes, costs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from vedika_ai.ml.cohort import check_source, physiotherapy_mask, rehabilitation_codes, stata
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

SCHEMA_VERSION = "1.0"
GENERATOR_VERSION = "0.1.0"
SOURCE_COLUMNS = ("PSTV01", "FKL03", "FKL10", "FKL11", "FKL18", "FKL18A", "FKL30", "FKL47", "FKL48")
COLUMN_USE = {
    "PSTV01": "Transient unique participant and participant-month counts",
    "FKL03": "Service date and month aggregates",
    "FKL10": "Outpatient filter",
    "FKL11": "FIS/IRM clinic filter resolved from Stata value labels",
    "FKL18": "Aggregate ICD-10 frequency",
    "FKL18A": "Physiotherapy filter and aggregate diagnosis frequency",
    "FKL30": "Physiotherapy filter and aggregate procedure frequency",
    "FKL47": "Aggregate billed-cost statistics",
    "FKL48": "Aggregate verified-cost statistics",
}
TOP_CATEGORY_LIMIT = 100


def visit_frequency_buckets(counts: Counter[tuple[int, str]]) -> dict[str, int]:
    """Visits per participant-month as buckets 1..8, 9-12, 13+."""

    buckets = {str(value): 0 for value in range(1, 9)} | {"9-12": 0, "13+": 0}
    for visits in counts.values():
        if visits <= 0:
            continue
        bucket = str(visits) if visits <= 8 else "9-12" if visits <= 12 else "13+"
        buckets[bucket] += 1
    return buckets


def _common(counter: Counter, minimum: int) -> list[tuple[Any, int]]:
    return [(value, n) for value, n in counter.most_common() if n >= minimum][:TOP_CATEGORY_LIMIT]


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


def build_claim_reference(
    source: Path,
    output_dir: Path,
    *,
    year: int,
    chunk_size: int = 200_000,
    minimum_count: int = MINIMUM_SAFE_CELL_COUNT,
) -> dict[str, Any]:
    import numpy

    pandas, pyreadstat = stata()
    source = check_source(source)
    if chunk_size <= 0:
        raise ReferenceDataError("chunk_size must be positive")
    require_safe_minimum(minimum_count)
    _, metadata = pyreadstat.read_dta(str(source), metadataonly=True)
    missing = sorted(set(SOURCE_COLUMNS) - set(metadata.column_names))
    if missing:
        raise ReferenceDataError(f"Source is missing required columns: {', '.join(missing)}")
    clinic_codes = rehabilitation_codes(metadata)

    rows = Counter()
    participants: set[int] = set()
    participant_months: Counter[tuple[int, str]] = Counter()
    months: Counter[str] = Counter()
    clinics: Counter[str] = Counter()
    diagnoses: Counter[tuple[str, str]] = Counter()
    procedures: Counter[str] = Counter()
    billed: list[float] = []
    verified: list[float] = []
    first_day = last_day = None

    chunks = pyreadstat.read_file_in_chunks(
        pyreadstat.read_dta, str(source), chunksize=chunk_size, usecols=list(SOURCE_COLUMNS)
    )
    for frame, _ in chunks:
        clinic = pandas.to_numeric(frame["FKL11"], errors="coerce")
        outpatient = pandas.to_numeric(frame["FKL10"], errors="coerce").eq(1)
        physiotherapy = physiotherapy_mask(frame, clinic_codes, pandas)
        rows["source"] += len(frame)
        rows["outpatient"] += int(outpatient.sum())
        rows["rehabilitation"] += int((outpatient & clinic.isin(clinic_codes)).sum())
        rows["physiotherapy"] += int(physiotherapy.sum())
        subset = frame.loc[physiotherapy]
        if subset.empty:
            continue

        clinics.update(
            clinic_codes[code] for code in clinic.loc[physiotherapy].dropna().astype(int)
        )
        dates = pandas.to_datetime(subset["FKL03"], errors="coerce")
        valid = dates.dropna()
        if not valid.empty:
            first_day = valid.min() if first_day is None else min(first_day, valid.min())
            last_day = valid.max() if last_day is None else max(last_day, valid.max())

        month_values = dates.dt.to_period("M").astype(str)
        months.update(month_values[month_values != "NaT"].tolist())
        for participant, month in zip(subset["PSTV01"], month_values, strict=True):
            if pandas.notna(participant):
                participants.add(int(participant))
                if month != "NaT":
                    participant_months[(int(participant), month)] += 1

        for code, name in zip(subset["FKL18"], subset["FKL18A"], strict=True):
            code_text = "" if pandas.isna(code) else str(code).strip()
            name_text = "" if pandas.isna(name) else str(name).strip()
            if code_text or name_text:
                diagnoses[(code_text, name_text)] += 1
        procedures.update(v.strip() for v in subset["FKL30"].dropna().astype(str) if v.strip())
        billed.extend(
            pandas.to_numeric(subset["FKL47"], errors="coerce").dropna().astype(float).tolist()
        )
        verified.extend(
            pandas.to_numeric(subset["FKL48"], errors="coerce").dropna().astype(float).tolist()
        )

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
                str(code): label for code, label in sorted(clinic_codes.items())
            },
        },
        "counts": {
            "source_rows": rows["source"],
            "outpatient_rows": rows["outpatient"],
            "outpatient_rehabilitation_rows": rows["rehabilitation"],
            "outpatient_physiotherapy_rows": rows["physiotherapy"],
            "unique_participants": len(participants),
            "participant_months": len(participant_months),
        },
        "date_range": {
            "minimum": first_day.date().isoformat() if first_day is not None else None,
            "maximum": last_day.date().isoformat() if last_day is not None else None,
        },
        "monthly_rows": dict(sorted(months.items())),
        "clinic_rows": dict(sorted(clinics.items())),
        "visits_per_participant_month": visit_frequency_buckets(participant_months),
        "costs": {
            "billed": _cost_summary(billed, numpy),
            "verified": _cost_summary(verified, numpy),
        },
        "privacy": PRIVACY_FLAGS | {"minimum_category_count": minimum_count},
    }
    dictionary = {
        "schema_version": SCHEMA_VERSION,
        "source_table": "FKRTL regular sample",
        "columns": [
            {
                "source": column,
                "description": metadata.column_names_to_labels.get(column, ""),
                "use": COLUMN_USE[column],
                "exported_row_level": False,
            }
            for column in SOURCE_COLUMNS
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [
        output_dir / name
        for name in ("summary.json", "diagnoses.csv", "procedures.csv", "data-dictionary.json")
    ]
    write_json(outputs[0], summary)
    write_csv(
        outputs[1],
        ("icd10", "diagnosis", "count"),
        [
            {"icd10": c, "diagnosis": d, "count": n}
            for (c, d), n in _common(diagnoses, minimum_count)
        ],
    )
    write_csv(
        outputs[2],
        ("procedure", "count"),
        [{"procedure": p, "count": n} for p, n in _common(procedures, minimum_count)],
    )
    write_json(outputs[3], dictionary)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "source": file_entry(source),
        "parameters": {
            "year": year,
            "chunk_size": chunk_size,
            "minimum_category_count": minimum_count,
        },
        "outputs": [file_entry(path) for path in outputs],
        "privacy": summary["privacy"],
    }
    assert_privacy_safe(manifest)
    write_json(output_dir / "manifest.json", manifest)
    return manifest
