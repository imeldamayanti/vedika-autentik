import csv
import json
from collections import Counter
from pathlib import Path

import pytest

from vedika_ai.claim_reference import (
    MINIMUM_SAFE_CELL_COUNT,
    ClaimReferenceError,
    assert_privacy_safe_aggregate,
    is_physiotherapy_text,
    sha256_file,
    visit_frequency_buckets,
)

REFERENCE_DIR = Path(__file__).parents[1] / "data" / "reference" / "rehab-2024"


@pytest.mark.parametrize(
    "text",
    [
        "Other physical therapy",
        "9335 - Other heat therapy;9339 - Other physical therapy",
        "9312 - Other active musculoskeletal exercise",
        "Pelayanan fisioterapi rawat jalan",
    ],
)
def test_physiotherapy_text_matches_supported_descriptions(text):
    assert is_physiotherapy_text(text)


@pytest.mark.parametrize(
    "text",
    [
        "Speech therapy",
        "Occupational therapy",
        "General examination",
        "",
    ],
)
def test_physiotherapy_text_excludes_other_rehabilitation_disciplines(text):
    assert not is_physiotherapy_text(text)


def test_visit_frequency_is_exported_only_as_buckets():
    counts = Counter({(10000001, "2024-01"): 1, (10000002, "2024-01"): 9})

    result = visit_frequency_buckets(counts)

    assert result["1"] == 1
    assert result["9-12"] == 1
    assert "10000001" not in str(result)
    assert "10000002" not in str(result)


def test_privacy_guard_rejects_identifier_collections():
    with pytest.raises(ClaimReferenceError, match="participant_ids"):
        assert_privacy_safe_aggregate({"participant_ids": [10000001]})


def test_privacy_guard_accepts_aggregate_counts():
    assert_privacy_safe_aggregate(
        {
            "counts": {"unique_participants": 42, "participant_months": 73},
            "privacy": {"participant_identifiers_exported": False},
        }
    )


def test_committed_reference_contains_only_safe_aggregates():
    summary = json.loads((REFERENCE_DIR / "summary.json").read_text(encoding="utf-8"))

    assert_privacy_safe_aggregate(summary)
    assert summary["privacy"] == {
        "minimum_category_count": MINIMUM_SAFE_CELL_COUNT,
        "participant_identifiers_exported": False,
        "row_level_records_exported": False,
        "visit_identifiers_exported": False,
    }
    assert summary["counts"]["outpatient_physiotherapy_rows"] <= summary["counts"][
        "outpatient_rehabilitation_rows"
    ]


@pytest.mark.parametrize(
    ("filename", "expected_fields"),
    [
        ("diagnoses.csv", {"icd10", "diagnosis", "count"}),
        ("procedures.csv", {"procedure", "count"}),
    ],
)
def test_reference_category_tables_are_suppressed(filename, expected_fields):
    with (REFERENCE_DIR / filename).open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))

    assert rows
    assert set(rows[0]) == expected_fields
    assert all(int(row["count"]) >= MINIMUM_SAFE_CELL_COUNT for row in rows)


def test_reference_manifest_matches_committed_outputs():
    manifest = json.loads((REFERENCE_DIR / "manifest.json").read_text(encoding="utf-8"))

    assert_privacy_safe_aggregate(manifest)
    for output in manifest["outputs"]:
        path = REFERENCE_DIR / output["filename"]
        assert path.stat().st_size == output["size_bytes"]
        assert sha256_file(path) == output["sha256"]
