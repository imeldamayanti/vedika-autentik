#!/usr/bin/env python3
"""Build privacy-safe rehabilitation reference aggregates from an FKRTL Stata file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vedika_ai.claim_reference import (
    MINIMUM_SAFE_CELL_COUNT,
    ClaimReferenceError,
    build_claim_reference,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Regular FKRTL .dta file")
    parser.add_argument("--output", type=Path, required=True, help="Aggregate output directory")
    parser.add_argument("--year", type=int, required=True, help="Claim service year")
    parser.add_argument("--chunk-size", type=int, default=200_000)
    parser.add_argument("--minimum-count", type=int, default=MINIMUM_SAFE_CELL_COUNT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_claim_reference(
            args.source,
            args.output,
            year=args.year,
            chunk_size=args.chunk_size,
            minimum_count=args.minimum_count,
        )
    except ClaimReferenceError as error:
        raise SystemExit(str(error)) from error

    print(
        json.dumps(
            {
                "output": str(args.output),
                "source_sha256": manifest["source"]["sha256"],
                "status": "ok",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
