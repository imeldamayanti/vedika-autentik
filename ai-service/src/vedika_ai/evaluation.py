"""Field-level voice answer evaluation without transcript disclosure in reports."""

import argparse
import json
import sys
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import TextIO

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import config
from .answer_reader import AnswerReader, ReadAnswerRequest, ReadContext, TranscriptTurn
from .answers import classify_answer
from .errors import ServiceError
from .gemini import GeminiTransport


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    sesi_ditagih: int = Field(ge=0)
    tanggal_libur: list[date] = Field(default_factory=list)
    transkrip: list[TranscriptTurn]
    expected: dict


def _score(expected, actual) -> tuple[int, int]:
    if isinstance(expected, dict):
        correct = 0
        total = 0
        actual_dict = actual if isinstance(actual, dict) else {}
        for key, value in expected.items():
            child_correct, child_total = _score(value, actual_dict.get(key))
            correct += child_correct
            total += child_total
        return correct, total
    return (int(expected == actual), 1)


def evaluate_cases(
    cases: list[EvaluationCase],
    reader: AnswerReader,
    *,
    interval_seconds: float = 0,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict:
    rows = []
    correct_fields = 0
    total_fields = 0
    correct_labels = 0
    total_labels = 0
    provider_errors = 0
    for index, case in enumerate(cases):
        request = ReadAnswerRequest(
            transkrip=case.transkrip,
            konteks=ReadContext(sesi_ditagih=case.sesi_ditagih, tanggal_libur=case.tanggal_libur),
        )
        try:
            answer = reader.read(request)
        except ServiceError as error:
            # Malformed model output is a scored miss; anything else means no measurement.
            if not isinstance(error.__cause__, ValidationError):
                provider_errors += 1
                rows.append({"id": case.id, "error": error.code})
                break
            answer = None
        result = answer.model_dump(mode="json") if answer else None
        label = classify_answer(answer, case.sesi_ditagih).label if answer else "Tidak yakin"
        correct, total = _score(case.expected.get("hasil", {}), result)
        correct_fields += correct
        total_fields += total
        row = {"id": case.id, "correct": correct, "total": total}
        if "label" in case.expected:
            label_correct = label == case.expected["label"]
            correct_labels += int(label_correct)
            total_labels += 1
            row["label_correct"] = label_correct
        rows.append(row)
        if interval_seconds and index < len(cases) - 1:
            sleeper(interval_seconds)
    accuracy = None if provider_errors else (correct_fields / total_fields if total_fields else 0.0)
    label_accuracy = (
        None if provider_errors else (correct_labels / total_labels if total_labels else None)
    )
    return {
        "cases_evaluated": len(rows),
        "correct_fields": correct_fields,
        "total_fields": total_fields,
        "accuracy": round(accuracy, 6) if accuracy is not None else None,
        "correct_labels": correct_labels,
        "total_labels": total_labels,
        "label_accuracy": round(label_accuracy, 6) if label_accuracy is not None else None,
        "provider_errors": provider_errors,
        "cases": rows,
    }


def _default_reader(interval_seconds: float = 0) -> AnswerReader:
    api_key = config.gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for live evaluation")
    retry_base = max(2, interval_seconds)
    return AnswerReader(
        GeminiTransport(
            api_key,
            config.gemini_text_model(),
            retry_delays=(retry_base, retry_base * 2, retry_base * 4),
        )
    )


def main(
    argv: list[str] | None = None,
    *,
    reader: AnswerReader | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> int:
    parser = argparse.ArgumentParser(description="Evaluate structured voice-answer fields.")
    parser.add_argument("source", type=Path, help="JSON array of transcript cases")
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--interval-seconds", type=float, default=0)
    args = parser.parse_args(argv)
    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1")
    if args.interval_seconds < 0:
        parser.error("--interval-seconds must be non-negative")

    try:
        raw_cases = json.loads(args.source.read_text(encoding="utf-8"))
        if not isinstance(raw_cases, list):
            raise TypeError("fixture root must be an array")
        cases = [EvaluationCase.model_validate(item) for item in raw_cases]
    except (OSError, json.JSONDecodeError, TypeError, ValidationError):
        print(
            json.dumps({"error": "fixture_tidak_valid"}),
            file=stderr or sys.stderr,
        )
        return 2
    try:
        selected_reader = reader or _default_reader(args.interval_seconds)
    except RuntimeError:
        print(
            json.dumps({"error": "gemini_tidak_dikonfigurasi"}),
            file=stderr or sys.stderr,
        )
        return 2
    report = evaluate_cases(
        cases,
        selected_reader,
        interval_seconds=args.interval_seconds,
        sleeper=sleeper,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2), file=stdout or sys.stdout)
    if report["provider_errors"]:
        return 2
    return 0 if report["accuracy"] >= args.threshold else 1

