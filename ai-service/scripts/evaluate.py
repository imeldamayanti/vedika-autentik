"""Run the reproducible synthetic-fixture regression and print a JSON report."""

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

from vedika_ai import config
from vedika_ai.comparison import THRESHOLD_VERSION
from vedika_ai.ocr import EmptyOcr
from vedika_ai.pipeline import AnalysisPipeline
from vedika_ai.provenance import PROVENANCE_RULE_VERSION
from vedika_ai.schemas import ClaimContext

IMPLEMENTED_CHECKS = {"kecocokan_klaim", "copy_paste", "suntingan", "tanda_ai"}
POSITIVE_PAIRS = [
    ("VA-KMB-00", "VA-KMB-01"),
    ("VA-KMB-00", "VA-KMB-02"),
    ("VA-ASL-02", "VA-KMB-03"),
]
NEGATIVE_PAIRS = [
    ("VA-ASL-01", "VA-ASL-02"),
    ("VA-KMB-00", "VA-ASL-01"),
    ("VA-KMB-00", "VA-ASL-02"),
]


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 3) if denominator else None


def _percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def _confusion(per_file: list[dict], check: str) -> dict:
    true_positive = sum(
        check in row["expected_checks"] and check in row["observed_checks"] for row in per_file
    )
    false_positive = sum(
        check not in row["expected_checks"] and check in row["observed_checks"] for row in per_file
    )
    false_negative = sum(
        check in row["expected_checks"] and check not in row["observed_checks"] for row in per_file
    )
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": _ratio(true_positive, true_positive + false_positive),
        "recall": _ratio(true_positive, true_positive + false_negative),
    }


def _nullable_field_metrics(rows: list[dict], field: str) -> dict:
    observed_key = f"{field}_observed"
    expected_key = f"{field}_expected"
    returned = [row for row in rows if row[observed_key] is not None]
    return {
        "coverage": _ratio(len(returned), len(rows)),
        "accuracy_when_returned": _ratio(
            sum(row[expected_key] == row[observed_key] for row in returned),
            len(returned),
        ),
    }


def evaluate(dataset: Path, skip_ocr: bool) -> dict:
    json_files = sorted(dataset.glob("*/*.json"))
    if not json_files:
        raise SystemExit(f"Dataset tidak ditemukan di {dataset}")

    pipeline = AnalysisPipeline(ocr=EmptyOcr()) if skip_ocr else AnalysisPipeline()
    by_id: dict[str, tuple[Path, dict]] = {}
    per_file: list[dict] = []
    latencies: list[int] = []

    for json_path in json_files:
        truth = json.loads(json_path.read_text(encoding="utf-8"))
        document_id = truth["id"]
        pdf_path = json_path.with_suffix(".pdf")
        by_id[document_id] = (pdf_path, truth)
        started = time.perf_counter()
        result = pipeline.analyze(
            pdf_path.read_bytes(),
            pdf_path.name,
            ClaimContext.model_validate(truth.get("klaim") or {}),
        )
        wall_ms = round((time.perf_counter() - started) * 1000)
        latencies.append(wall_ms)
        expected_checks = sorted(
            {item["cek"] for item in truth.get("temuan", [])} & IMPLEMENTED_CHECKS
        )
        observed_checks = sorted({item.cek for item in result.temuan} & IMPLEMENTED_CHECKS)
        expected_rows = truth.get("isi_lembar", {}).get("baris_terisi")
        observed_rows = result.isi_lembar.baris_terisi
        expected_dates = truth.get("isi_lembar", {}).get("tanggal_sesi", [])
        observed_dates = result.isi_lembar.tanggal_sesi
        expected_total = truth.get("isi_lembar", {}).get("jumlah_kunjungan_tertulis")
        observed_total = result.isi_lembar.jumlah_kunjungan_tertulis
        expected_content = truth.get("isi_lembar", {})
        per_file.append(
            {
                "id": document_id,
                "quality_expected": truth["kualitas_scan"]["status"],
                "quality_observed": result.kualitas_scan.status,
                "rows_expected": expected_rows,
                "rows_observed": observed_rows,
                "dates_expected": expected_dates,
                "dates_observed": observed_dates,
                "written_total_expected": expected_total,
                "written_total_observed": observed_total,
                "name_expected": expected_content.get("nama"),
                "name_observed": result.isi_lembar.nama,
                "card_expected": expected_content.get("no_kartu"),
                "card_observed": result.isi_lembar.no_kartu,
                "sep_expected": expected_content.get("no_sep"),
                "sep_observed": result.isi_lembar.no_sep,
                "period_expected": expected_content.get("periode"),
                "period_observed": result.isi_lembar.periode,
                "expected_checks": expected_checks,
                "observed_checks": observed_checks,
                "latency_ms": wall_ms,
            }
        )

    pair_rows: list[dict] = []
    for expected_same, pairs in ((True, POSITIVE_PAIRS), (False, NEGATIVE_PAIRS)):
        for first_id, second_id in pairs:
            first_path = by_id[first_id][0]
            second_path = by_id[second_id][0]
            result = pipeline.compare(
                first_path.read_bytes(),
                first_path.name,
                second_path.read_bytes(),
                second_path.name,
            )
            pair_rows.append(
                {
                    "a": first_id,
                    "b": second_id,
                    "expected_same": expected_same,
                    "observed_same": result.sama,
                    "similarity": result.kemiripan,
                    "pasted_regions": len(result.tempelan),
                }
            )

    good_rows = [row for row in per_file if row["quality_expected"] == "baik"]
    revision = hashlib.sha256(b"".join(path.read_bytes() for path in json_files)).hexdigest()[:16]
    return {
        "dataset_revision": revision,
        "engine_version": config.ENGINE_VERSION,
        "threshold_version": f"{THRESHOLD_VERSION}+{PROVENANCE_RULE_VERSION}",
        "ocr_models": pipeline.models,
        "ocr_skipped": skip_ocr,
        "documents": len(per_file),
        "metrics": {
            "quality_accuracy": _ratio(
                sum(row["quality_expected"] == row["quality_observed"] for row in per_file),
                len(per_file),
            ),
            "session_count_accuracy_good_scans": _ratio(
                sum(row["rows_expected"] == row["rows_observed"] for row in good_rows),
                len(good_rows),
            ),
            "date_sequence_coverage_good_scans": _ratio(
                sum(bool(row["dates_observed"]) for row in good_rows),
                len(good_rows),
            ),
            "date_sequence_exact_good_scans": _ratio(
                sum(row["dates_expected"] == row["dates_observed"] for row in good_rows),
                len(good_rows),
            ),
            "date_sequence_exact_when_returned": _ratio(
                sum(
                    row["dates_expected"] == row["dates_observed"]
                    for row in good_rows
                    if row["dates_observed"]
                ),
                sum(bool(row["dates_observed"]) for row in good_rows),
            ),
            "written_total_coverage_good_scans": _ratio(
                sum(row["written_total_observed"] is not None for row in good_rows),
                len(good_rows),
            ),
            "written_total_accuracy_when_returned": _ratio(
                sum(
                    row["written_total_expected"] == row["written_total_observed"]
                    for row in good_rows
                    if row["written_total_observed"] is not None
                ),
                sum(row["written_total_observed"] is not None for row in good_rows),
            ),
            "structured_fields_good_scans": {
                field: _nullable_field_metrics(good_rows, field)
                for field in ("name", "card", "sep", "period")
            },
            "duplicate_pair_accuracy": _ratio(
                sum(row["expected_same"] == row["observed_same"] for row in pair_rows),
                len(pair_rows),
            ),
            "checks": {check: _confusion(per_file, check) for check in sorted(IMPLEMENTED_CHECKS)},
            "latency_ms": {
                "median": _percentile(latencies, 0.5),
                "p95": _percentile(latencies, 0.95),
                "max": max(latencies),
            },
        },
        "files": per_file,
        "pairs": pair_rows,
    }


def regression_failures(report: dict) -> list[str]:
    metrics = report["metrics"]
    failures: list[str] = []
    exact_targets = {
        "quality_accuracy": 1.0,
        "session_count_accuracy_good_scans": 1.0,
        "duplicate_pair_accuracy": 1.0,
        "date_sequence_exact_when_returned": 1.0,
        "written_total_accuracy_when_returned": 1.0,
    }
    for metric, target in exact_targets.items():
        if metrics[metric] != target:
            failures.append(f"{metric}={metrics[metric]} (target {target})")
    if metrics["date_sequence_coverage_good_scans"] < 0.4:
        failures.append("date_sequence_coverage_good_scans below 0.4")
    if metrics["latency_ms"]["p95"] >= 10_000:
        failures.append("latency p95 is not below 10000 ms")
    for field, values in metrics["structured_fields_good_scans"].items():
        if values["coverage"] and values["accuracy_when_returned"] != 1.0:
            failures.append(f"{field} accuracy_when_returned is not 1.0")
    minimum_recall = {
        "copy_paste": 1.0,
        "kecocokan_klaim": 1.0,
        "suntingan": 0.4,
        "tanda_ai": 1.0,
    }
    for check, recall in minimum_recall.items():
        values = metrics["checks"][check]
        if values["precision"] != 1.0 or values["recall"] < recall:
            failures.append(f"{check} precision/recall regressed")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path(__file__).parents[2] / "dataset")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-ocr", action="store_true")
    parser.add_argument("--check", action="store_true", help="Fail when baseline gates regress")
    args = parser.parse_args()
    report = evaluate(args.dataset, args.skip_ocr)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    if args.check:
        failures = regression_failures(report)
        if failures:
            raise SystemExit("Regression gate failed: " + "; ".join(failures))


if __name__ == "__main__":
    main()
