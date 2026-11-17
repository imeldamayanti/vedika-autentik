"""Export rules for anything derived from the raw sample: aggregates only, no identifiers."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

MINIMUM_SAFE_CELL_COUNT = 10
FORBIDDEN_KEYS = frozenset(
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
        "peserta",
        "raw_record",
        "raw_records",
    }
)
PRIVACY_FLAGS = {
    "minimum_category_count": MINIMUM_SAFE_CELL_COUNT,
    "participant_identifiers_exported": False,
    "visit_identifiers_exported": False,
    "row_level_records_exported": False,
}


class ReferenceDataError(ValueError):
    """A source file or a generated aggregate breaks the reference contract."""


def assert_privacy_safe(value: Any) -> None:
    """Reject identifier-bearing keys anywhere in a payload."""

    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_KEYS:
                raise ReferenceDataError(f"Identifier-bearing output key is forbidden: {key}")
            assert_privacy_safe(child)
    elif isinstance(value, list):
        for child in value:
            assert_privacy_safe(child)


def require_safe_minimum(minimum: int) -> None:
    if minimum < MINIMUM_SAFE_CELL_COUNT:
        raise ReferenceDataError(f"minimum_count must be at least {MINIMUM_SAFE_CELL_COUNT}")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def file_entry(path: Path) -> dict[str, Any]:
    return {"filename": path.name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def write_json(path: Path, value: Any, *, sort_keys: bool = True) -> None:
    assert_privacy_safe(value)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=sort_keys)
    path.write_text(text + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
