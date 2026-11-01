"""Read the official S1-S6/S8 transcripts with Gemini and write uji.py input."""

import argparse
import json
import time
from pathlib import Path

from vedika_ai import config
from vedika_ai.answer_reader import AnswerReader
from vedika_ai.gemini import GeminiTransport
from vedika_ai.official_voice import read_official_answers

ROOT = Path(__file__).resolve().parents[2] / "data-uji-konfirmasi"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--interval-seconds", type=float, default=0)
    args = parser.parse_args()
    api_key = config.gemini_api_key()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is required")
    reader = AnswerReader(
        GeminiTransport(api_key, config.gemini_text_model(), timeout=config.READER_TIMEOUT_SECONDS)
    )
    rows = read_official_answers(
        ROOT, reader, between_cases=lambda: time.sleep(args.interval_seconds)
    )
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
