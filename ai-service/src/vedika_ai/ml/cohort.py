"""The outpatient physiotherapy cohort from the raw BPJS FKRTL sample, as participant-months.

Participant and visit identifiers are used only to group and join; `patient_months` drops them.
Reading Stata files needs the `data` dependency group.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from vedika_ai.ml import tools
from vedika_ai.ml.privacy import ReferenceDataError

REHABILITATION_CLINICS = frozenset({"FIS", "IRM"})
PHYSIOTHERAPY = re.compile(
    r"(?:physical therap|physiotherap|fisioterap|musculoskeletal exercise|"
    r"heat therapy|diathermy|electrotherap|manual therap)",
    re.IGNORECASE,
)
VISIT_COLUMNS = (
    "PSTV01",
    "PSTV15",
    "FKL02",
    "FKP02",
    "FKL03",
    "FKL06",
    "FKL07",
    "FKL08",
    "FKL09",
    "FKL10",
    "FKL11",
    "FKL18A",
    "FKL26",
    "FKL30",
)
# `episode` looks back 6 months and every sample file starts in January, so only July-December
# participant-months have their full history; January-June is read as history only.
WINDOW_MONTHS = frozenset(f"{month:02d}" for month in range(7, 13))


def is_physiotherapy_text(value: str) -> bool:
    return bool(PHYSIOTHERAPY.search(value))


def stata():
    try:
        import pandas
        import pyreadstat
    except ImportError as error:  # pragma: no cover - CLI environment only
        raise ReferenceDataError("Run with `uv run --group data` to read Stata files.") from error
    return pandas, pyreadstat


def check_source(path: Path) -> Path:
    path = path.resolve()
    if not path.is_file() or path.suffix.casefold() != ".dta":
        raise ReferenceDataError(f"Source must be an existing .dta file: {path.name}")
    return path


def rehabilitation_codes(metadata: Any) -> dict[int, str]:
    """FKL11 codes of the FIS and IRM clinics, resolved from the file's value labels."""

    label_set = metadata.variable_to_label.get("FKL11")
    labels = metadata.value_labels.get(label_set, {}) if label_set else {}
    codes = {
        int(code): str(label).upper()
        for code, label in labels.items()
        if str(label).upper() in REHABILITATION_CLINICS
    }
    if not codes:
        raise ReferenceDataError("FKL11 has no FIS or IRM value labels in this release")
    return codes


def physiotherapy_mask(frame, clinic_codes, pandas):
    """Outpatient rows in a FIS/IRM clinic whose diagnosis or procedure text is physiotherapy."""

    text = frame["FKL18A"].fillna("").astype(str) + " " + frame["FKL30"].fillna("").astype(str)
    clinic = pandas.to_numeric(frame["FKL11"], errors="coerce")
    outpatient = pandas.to_numeric(frame["FKL10"], errors="coerce").eq(1)
    return outpatient & clinic.isin(clinic_codes) & text.str.contains(PHYSIOTHERAPY, regex=True)


def _secondary_diagnoses(path: Path, visit_ids: set[str], chunk_size: int) -> dict[str, list[str]]:
    _, pyreadstat = stata()
    found: dict[str, list[str]] = defaultdict(list)
    chunks = pyreadstat.read_file_in_chunks(
        pyreadstat.read_dta, str(path), chunksize=chunk_size, usecols=["FKL02", "FKL24A"]
    )
    for frame, _ in chunks:
        visits = frame["FKL02"].astype(str).str.strip()
        for visit, code in zip(visits, frame["FKL24A"], strict=True):
            if visit in visit_ids and isinstance(code, str) and code.strip():
                found[visit].append(code.strip().upper())
    return found


def _birth_dates(path: Path, participants: set[int]) -> dict[int, date]:
    pandas, pyreadstat = stata()
    frame, _ = pyreadstat.read_dta(str(path), usecols=["PSTV01", "PSTV03"])
    born = pandas.to_datetime(frame["PSTV03"], errors="coerce")
    return {
        int(participant): day.date()
        for participant, day in zip(frame["PSTV01"], born, strict=True)
        if pandas.notna(participant) and int(participant) in participants and pandas.notna(day)
    }


def read_visits(
    fkrtl: Path,
    *,
    secondary: Path | None = None,
    membership: Path | None = None,
    chunk_size: int = 200_000,
) -> list[dict[str, Any]]:
    """Outpatient physiotherapy visits of one FKRTL sample file.

    `secondary` (the sample's *diagnosissekunder* file) adds `conditions`, the visit's 3-digit
    secondary diagnoses; the primary diagnosis is almost always Z50/Z09 and says nothing about the
    condition. `membership` (*kepesertaan*) adds `born`.
    """

    pandas, pyreadstat = stata()
    fkrtl = check_source(fkrtl)
    _, metadata = pyreadstat.read_dta(str(fkrtl), metadataonly=True)
    missing = sorted(set(VISIT_COLUMNS) - set(metadata.column_names))
    if missing:
        raise ReferenceDataError(f"Source is missing required columns: {', '.join(missing)}")
    clinic_codes = rehabilitation_codes(metadata)

    visits: list[dict[str, Any]] = []
    chunks = pyreadstat.read_file_in_chunks(
        pyreadstat.read_dta, str(fkrtl), chunksize=chunk_size, usecols=list(VISIT_COLUMNS)
    )
    for frame, _ in chunks:
        rows = frame.loc[physiotherapy_mask(frame, clinic_codes, pandas)]
        days = pandas.to_datetime(rows["FKL03"], errors="coerce")
        peer_groups = rows[["FKL06", "FKL07", "FKL08", "FKL09"]].fillna(-1).astype(int)
        referred = rows["FKP02"].fillna("").astype(str).str.strip().ne("")
        other_district = pandas.to_numeric(rows["FKL26"], errors="coerce").ne(
            pandas.to_numeric(rows["FKL06"], errors="coerce")
        )
        for participant, visit, day, weight, peer_group, has_referral, other in zip(
            rows["PSTV01"],
            rows["FKL02"].astype(str).str.strip(),
            days,
            rows["PSTV15"],
            peer_groups.itertuples(index=False, name=None),
            referred,
            other_district,
            strict=True,
        ):
            if pandas.isna(participant) or pandas.isna(day):
                continue
            visits.append(
                {
                    "participant": int(participant),
                    "visit": visit,
                    "date": day.date(),
                    "weight": float(weight),
                    "peer_group": peer_group,
                    "referred": bool(has_referral),
                    "other_district": bool(other),
                }
            )

    if secondary is not None:
        diagnoses = _secondary_diagnoses(
            check_source(secondary), {v["visit"] for v in visits}, chunk_size
        )
        for visit in visits:
            visit["conditions"] = diagnoses.get(visit["visit"], [])
    if membership is not None:
        births = _birth_dates(check_source(membership), {v["participant"] for v in visits})
        for visit in visits:
            visit["born"] = births.get(visit["participant"])
    return visits


def age_on(born: date | None, month: str) -> int | None:
    """Age in years on the first day of a 'YYYY-MM' month."""

    if born is None:
        return None
    year, mon = map(int, month.split("-"))
    return year - born.year - ((mon, 1) < (born.month, born.day))


def _most_common(values: list[str]) -> str | None:
    if not values:
        return None
    counts = Counter(values)
    top = max(counts.values())
    return min(value for value, n in counts.items() if n == top)


def patient_months(visits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One record per participant-month, without identifiers.

    `features` are the visit-pattern features of tools/pola.py, `anomaly_features` add the referral
    features of tools/anomali.py. `condition` and `age_group` are None unless the visits carry
    `conditions` and `born`. There is no holiday list for the sample years, so Sundays only.
    """

    pola, anomali = tools.pola(), tools.anomali()
    by_participant: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for visit in visits:
        by_participant[visit["participant"]].append(visit)

    records = []
    for rows in by_participant.values():
        by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_month[row["date"].strftime("%Y-%m")].append(row)
        active_months = set(by_month)
        for month, month_rows in by_month.items():
            features = pola.month_features(
                [r["date"] for r in month_rows], active_months, month, set()
            )
            indicators = pola.indicators(features)
            peer_group = Counter(r["peer_group"] for r in month_rows).most_common(1)[0][0]
            records.append(
                {
                    "month": month,
                    "features": features,
                    "anomaly_features": anomali.anomaly_features(features, month_rows),
                    "condition": _most_common(
                        [c for r in month_rows for c in r.get("conditions", [])]
                    ),
                    "age_group": anomali.age_group(age_on(month_rows[0].get("born"), month)),
                    "indicators": indicators,
                    "triggered": sum(indicators) >= 2,
                    "weight": float(month_rows[0]["weight"]),
                    "peer_group": peer_group,
                }
            )
    return records


def in_window(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Participant-months whose 6-month look-back lies inside the same sample file."""

    return [r for r in records if r["month"][5:] in WINDOW_MONTHS]


def load_sample(
    fkrtl: Path, *, membership: Path | None = None, secondary: Path | None = None
) -> list[dict[str, Any]]:
    """July-December participant-months of one sample file; files are never joined."""

    return in_window(patient_months(read_visits(fkrtl, secondary=secondary, membership=membership)))
