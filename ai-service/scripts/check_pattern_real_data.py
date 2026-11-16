#!/usr/bin/env python3
"""Score every real participant-month of the FKRTL sample with the committed pattern model.

Writes aggregates only (every count >= 10, smaller cells omitted) to
data/reference/pola-2024/perilaku-nyata.json; train_pattern_model.py renders them into EVALUASI.md.
This measures behaviour on real data (Tier A), not accuracy: the sample has no fraud labels.
Run with `uv run --group data python scripts/check_pattern_real_data.py --source <file.dta>`.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from vedika_ai.claim_reference import MINIMUM_SAFE_CELL_COUNT, assert_privacy_safe_aggregate
from vedika_ai.pola_reference import (
    HISTOGRAM_MONTHS,
    MINIMUM_GROUP_MONTHS,
    load_pola,
    patient_months,
    percentile,
    read_visits,
)

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "data-uji-konfirmasi" / "referensi-pola" / "model-pola-v1.json"
OUTPUT = ROOT / "ai-service" / "data" / "reference" / "pola-2024" / "perilaku-nyata.json"


def share(rows: list[dict], total_weight: float) -> float:
    return round(100 * sum(r["bobot"] for r in rows) / total_weight, 2)


def cell(rows: list[dict], total_weight: float) -> dict | None:
    if len(rows) < MINIMUM_SAFE_CELL_COUNT:
        return None
    return {"n": len(rows), "persen": share(rows, total_weight)}


def summarise(records: list[dict], model: dict) -> dict:
    pola = load_pola()
    threshold = model["ambang_tinggi"]
    for record in records:
        record["skor"] = pola.skor(model, record["fitur"])
        record["tinggi"] = record["skor"] >= threshold
    weight = sum(r["bobot"] for r in records)

    cross = {
        f"{'tinggi' if high else 'biasa'}_{'terpicu' if trig else 'tidak_terpicu'}": cell(
            [r for r in records if r["tinggi"] == high and r["dipicu"] == trig], weight
        )
        for high in (True, False)
        for trig in (True, False)
    }
    flagged_only = Counter(r["kombinasi"] for r in records if r["tinggi"] and not r["dipicu"])
    triggered = [r for r in records if r["dipicu"]]
    shown_one = sum(r["skor"] >= 0.9995 for r in triggered)

    months: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        months[record["bulan"]].append(record)
    per_month = {
        month: {
            "n": len(rows),
            "persen_tinggi": round(100 * sum(r["tinggi"] for r in rows) / len(rows), 1),
            "persen_terpicu": round(100 * sum(r["dipicu"] for r in rows) / len(rows), 1),
        }
        for month, rows in sorted(months.items())
        if len(rows) >= MINIMUM_SAFE_CELL_COUNT
    }

    groups: dict = defaultdict(list)
    for record in records:
        groups[record["kelompok"]].append(record)
    large = [rows for rows in groups.values() if len(rows) >= MINIMUM_GROUP_MONTHS]
    rates = [100 * sum(r["tinggi"] for r in rows) / len(rows) for rows in large]
    flagged_in_large = sum(r["tinggi"] for rows in large for r in rows)
    flagged_per_group = sorted((sum(r["tinggi"] for r in rows) for rows in large), reverse=True)
    top = flagged_per_group[: max(1, len(large) // 10)]

    result = {
        "versi_model": model["versi"],
        "ambang_tinggi": threshold,
        "n": len(records),
        "persen_tinggi": share([r for r in records if r["tinggi"]], weight),
        "persen_terpicu": share(triggered, weight),
        "silang": {key: value for key, value in cross.items() if value},
        "tinggi_tidak_terpicu_per_kombinasi": {
            key: {"n": count}
            for key, count in flagged_only.most_common()
            if count >= MINIMUM_SAFE_CELL_COUNT
        },
        "terpicu_tampil_satu": (
            {"n": shown_one} if shown_one >= MINIMUM_SAFE_CELL_COUNT else {"kurang_dari": 10}
        ),
        "terpicu": {"n": len(triggered)},
        "per_bulan": per_month,
        "kelompok": {
            "n": len(large),
            "tanpa_tinggi": sum(rate == 0 for rate in rates),
            "laju_tinggi_p50": round(percentile(rates, 0.5), 1),
            "laju_tinggi_p90": round(percentile(rates, 0.9), 1),
            "persen_tinggi_di_10_persen_teratas": (
                round(100 * sum(top) / flagged_in_large) if flagged_in_large else 0
            ),
        },
    }
    assert_privacy_safe_aggregate(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Regular FKRTL .dta file")
    parser.add_argument("--chunk-size", type=int, default=200_000)
    args = parser.parse_args()
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    records = patient_months(read_visits(args.source.resolve(), args.chunk_size))
    # July-December only: `episode` (rule I3) looks back 6 months and the file starts in January.
    result = summarise([r for r in records if r["bulan"] in HISTOGRAM_MONTHS], model)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "persen_tinggi": result["persen_tinggi"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
