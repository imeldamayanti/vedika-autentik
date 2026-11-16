#!/usr/bin/env python3
"""Build the privacy-safe rehabilitation reference (rehab-2024) from a regular FKRTL Stata file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vedika_ai.ml.claim_reference import build_claim_reference
from vedika_ai.ml.privacy import MINIMUM_SAFE_CELL_COUNT, ReferenceDataError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Regular FKRTL .dta file")
    parser.add_argument("--output", type=Path, required=True, help="Aggregate output directory")
    parser.add_argument("--year", type=int, required=True, help="Claim service year")
    parser.add_argument("--chunk-size", type=int, default=200_000)
    parser.add_argument("--minimum-count", type=int, default=MINIMUM_SAFE_CELL_COUNT)
    args = parser.parse_args()
    try:
        manifest = build_claim_reference(
            args.source,
            args.output,
            year=args.year,
            chunk_size=args.chunk_size,
            minimum_count=args.minimum_count,
        )
    except ReferenceDataError as error:
        raise SystemExit(str(error)) from error
    print(
        json.dumps(
            {
                "output": str(args.output),
                "source_sha256": manifest["source"]["sha256"],
                "status": "ok",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
