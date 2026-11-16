#!/usr/bin/env python3
"""Score every real July-December participant-month with the committed pola-v1 model.

Writes aggregates only, every count at least 10, to data/reference/pola-2024/perilaku-nyata.json;
train_pattern_model.py renders them into EVALUASI.md. Behaviour on real data, not accuracy: the
sample has no fraud labels.

    uv run --group data python scripts/check_pattern_real_data.py --source <file.dta>
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from vedika_ai.ml import tools
from vedika_ai.ml.cohort import patient_months, read_visits
from vedika_ai.ml.pattern_reference import HISTOGRAM_MONTHS, MINIMUM_GROUP_MONTHS, percentile
from vedika_ai.ml.privacy import MINIMUM_SAFE_CELL_COUNT, write_json

MODEL = tools.MODEL_DIR / "model-pola-v1.json"
OUTPUT = tools.REFERENCE_DIR / "pola-2024" / "perilaku-nyata.json"


def percent(rows: list[dict], total_weight: float) -> float:
    return round(100 * sum(r["weight"] for r in rows) / total_weight, 2)


def cell(rows: list[dict], total_weight: float) -> dict | None:
    if len(rows) < MINIMUM_SAFE_CELL_COUNT:
        return None
    return {"n": len(rows), "persen": percent(rows, total_weight)}


def summarise(records: list[dict], model: dict) -> dict:
    pola = tools.pola()
    threshold = model["ambang_tinggi"]
    scores = [pola.skor(model, r["features"]) for r in records]
    high = [s >= threshold for s in scores]
    total_weight = sum(r["weight"] for r in records)

    cross = {
        f"{'tinggi' if is_high else 'biasa'}_{'' if is_triggered else 'tidak_'}terpicu": cell(
            [
                r
                for r, h in zip(records, high, strict=True)
                if h == is_high and r["triggered"] == is_triggered
            ],
            total_weight,
        )
        for is_high in (True, False)
        for is_triggered in (True, False)
    }
    high_untriggered = Counter(
        r["combination"] for r, h in zip(records, high, strict=True) if h and not r["triggered"]
    )
    triggered = [r for r in records if r["triggered"]]
    shown_as_one = sum(s >= 0.9995 for r, s in zip(records, scores, strict=True) if r["triggered"])

    by_month: dict[str, list[tuple[dict, bool]]] = defaultdict(list)
    by_peer: dict = defaultdict(list)
    for r, h in zip(records, high, strict=True):
        by_month[r["month"]].append((r, h))
        by_peer[r["peer_group"]].append(h)
    per_month = {
        month: {
            "n": len(rows),
            "persen_tinggi": round(100 * sum(h for _, h in rows) / len(rows), 1),
            "persen_terpicu": round(100 * sum(r["triggered"] for r, _ in rows) / len(rows), 1),
        }
        for month, rows in sorted(by_month.items())
        if len(rows) >= MINIMUM_SAFE_CELL_COUNT
    }
    large = [flags for flags in by_peer.values() if len(flags) >= MINIMUM_GROUP_MONTHS]
    rates = [100 * sum(flags) / len(flags) for flags in large]
    high_per_group = sorted((sum(flags) for flags in large), reverse=True)
    high_in_large = sum(high_per_group)
    top_decile = high_per_group[: max(1, len(large) // 10)]

    return {
        "versi_model": model["versi"],
        "ambang_tinggi": threshold,
        "n": len(records),
        "persen_tinggi": percent(
            [r for r, h in zip(records, high, strict=True) if h], total_weight
        ),
        "persen_terpicu": percent(triggered, total_weight),
        "silang": {key: value for key, value in cross.items() if value},
        "tinggi_tidak_terpicu_per_kombinasi": {
            key: {"n": n}
            for key, n in high_untriggered.most_common()
            if n >= MINIMUM_SAFE_CELL_COUNT
        },
        "terpicu_tampil_satu": (
            {"n": shown_as_one} if shown_as_one >= MINIMUM_SAFE_CELL_COUNT else {"kurang_dari": 10}
        ),
        "terpicu": {"n": len(triggered)},
        "per_bulan": per_month,
        "kelompok": {
            "n": len(large),
            "tanpa_tinggi": sum(rate == 0 for rate in rates),
            "laju_tinggi_p50": round(percentile(rates, 0.5), 1),
            "laju_tinggi_p90": round(percentile(rates, 0.9), 1),
            "persen_tinggi_di_10_persen_teratas": round(100 * sum(top_decile) / high_in_large)
            if high_in_large
            else 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source", type=Path, required=True, help="Regular FKRTL .dta file")
    args = parser.parse_args()
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    records = [
        r for r in patient_months(read_visits(args.source)) if r["month"] in HISTOGRAM_MONTHS
    ]
    result = summarise(records, model)
    write_json(OUTPUT, result, sort_keys=False)
    print(json.dumps({"output": str(OUTPUT), "persen_tinggi": result["persen_tinggi"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
