#!/usr/bin/env python3
"""Compare anomali-v1, plain national rarity, and anomali-v2 on the same real data; write aggregates only.

anomali-v1 is the frozen Isolation Forest table (model-anomali-v1.json, code in commit d646541); it cannot be
refitted here, so it has no year-to-year row. Same arguments as train_anomaly_model.py. Writes
ai-service/data/reference/anomali/banding-metode.json and data-uji-konfirmasi/referensi-pola/BANDING-METODE.md.
"""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Callable
from datetime import date
from pathlib import Path

from vedika_ai.ml import anomaly_evaluation as evaluation
from vedika_ai.ml import anomaly_model, tools
from vedika_ai.ml.cohort import load_sample
from vedika_ai.ml.privacy import assert_privacy_safe, write_json
from vedika_ai.ml.report import number, table, thousands

V1 = tools.MODEL_DIR / "model-anomali-v1.json"
V2 = tools.MODEL_DIR / "model-anomali-v2.json"
OUTPUT = tools.REFERENCE_DIR / "anomali" / "banding-metode.json"
REPORT = tools.MODEL_DIR / "BANDING-METODE.md"
METHODS = ("anomali-v1 (Isolation Forest)", "Kelangkaan nasional", "anomali-v2 (umur)")
INJECTED = 2000
SEED = 11


def inject(features: dict, kind: str) -> dict:
    f = dict(features)
    if kind == "pemadatan seminggu":
        f |= {"maks_minggu": f["maks_minggu"] + 2, "sesi": f["sesi"] + 2}
    elif kind == "sesi hari Minggu":
        f |= {"ahad_libur": f["ahad_libur"] + 1, "sesi": f["sesi"] + 1}
    elif kind == "tagihan digelembungkan":
        f |= {"sesi": f["sesi"] + 5}
    elif kind == "sebagian tanpa rujukan":
        f |= {"tanpa_rujukan": 0.5}
    elif kind == "rujukan janggal":
        f |= {
            "tanpa_rujukan": 1.0,
            "lintas_wilayah": 1.0,
            "episode": max(f["episode"], 6),
            "sesi": max(f["sesi"], 5),
        }
    return f


INJECTIONS = (
    "pemadatan seminggu",
    "sesi hari Minggu",
    "tagihan digelembungkan",
    "sebagian tanpa rujukan",
    "rujukan janggal",
)


def flaggers(v1: dict, national: dict, v2: dict) -> dict[str, Callable[[dict], bool]]:
    anomali = tools.anomali()

    def v1_flags(record: dict) -> bool:
        stored = v1["sel"].get(anomaly_model.cell(record))
        return stored is None or stored["skor"] >= v1["ambang"]

    return {
        METHODS[0]: v1_flags,
        METHODS[1]: lambda r: anomali.score(national, r["anomaly_features"], None)["flagged"],
        METHODS[2]: lambda r: anomaly_model.score(v2, r)["flagged"],
    }


def compare(
    records: list[dict],
    first: list[dict],
    last: list[dict],
    outside: list[tuple[str, list[dict]]],
    alpha: float,
) -> dict:
    pola = tools.pola()
    v1 = json.loads(V1.read_text(encoding="utf-8"))
    national = anomaly_model.fit(records, context=None)
    v2 = anomaly_model.fit(records, alpha=alpha)
    flag = flaggers(v1, national, v2)
    total = anomaly_model.total_weight(records)
    flagged = {m: {i for i, r in enumerate(records) if flag[m](r)} for m in METHODS}

    results = {}
    for method, chosen in flagged.items():
        results[method] = {
            "percent_flagged": evaluation.percent([records[i] for i in chosen], total),
            "percent_model_only": evaluation.percent(
                [records[i] for i in chosen if not records[i]["triggered"]], total
            ),
            "percent_rules_or_model": evaluation.percent(
                [r for i, r in enumerate(records) if i in chosen or r["triggered"]], total
            ),
        }
    for method, kwargs in ((METHODS[1], {"context": None}), (METHODS[2], {"alpha": alpha})):
        results[method]["over_time"] = evaluation.over_time(first, last, **kwargs)

    rng = random.Random(SEED)
    ordinary = [r for r in last if not r["triggered"] and not any(flag[m](r) for m in METHODS)]
    chosen = rng.sample(ordinary, INJECTED)
    injection = {}
    for kind in INJECTIONS:
        changed = [r | {"anomaly_features": inject(r["anomaly_features"], kind)} for r in chosen]
        rules = sum(
            sum(pola.indicators({k: c["anomaly_features"][k] for k in pola.FEATURES})) >= 2
            for c in changed
        )
        injection[kind] = {"Aturan": round(100 * rules / INJECTED, 1)} | {
            m: round(100 * sum(flag[m](c) for c in changed) / INJECTED, 1) for m in METHODS
        }

    outside_rows = []
    for name, rows in outside:
        weight = anomaly_model.total_weight(rows)
        outside_rows.append(
            {"sample": name, "patient_months": len(rows)}
            | {m: evaluation.percent([r for r in rows if flag[m](r)], weight) for m in METHODS}
        )

    return {
        "patient_months": len(records),
        "years": sorted({r["month"][:4] for r in records}),
        "results": results,
        "jaccard": {
            a: {b: evaluation.jaccard(flagged[a], flagged[b]) for b in METHODS} for a in METHODS
        },
        "injection": {"count": INJECTED, "results": injection},
        "outside": outside_rows,
    }


def report(r: dict) -> str:
    res = r["results"]

    def over(method: str) -> str:
        o = res[method].get("over_time")
        if not o:
            return "–"
        return f"{number(o['percent_flagged_by_past_model'])}% / {number(o['percent_flagged_by_own_model'])}%, Jaccard {number(o['jaccard'], 3)}"

    main = table(
        [
            "Metode",
            "Ditandai",
            "Hanya model",
            "Aturan ATAU model",
            "Antartahun: 2024 oleh model 2023 / 2024",
        ],
        [
            [
                m,
                f"{number(res[m]['percent_flagged'])}%",
                f"{number(res[m]['percent_model_only'])}%",
                f"{number(res[m]['percent_rules_or_model'])}%",
                over(m),
            ]
            for m in METHODS
        ],
    )
    agreement = table(
        ["", *METHODS], [[a, *(number(r["jaccard"][a][b], 3) for b in METHODS)] for a in METHODS]
    )
    columns = ["Aturan", *METHODS]
    injected = table(
        ["Manipulasi", *columns],
        [
            [k, *(f"{number(v[c], 1)}%" for c in columns)]
            for k, v in r["injection"]["results"].items()
        ],
    )
    outside = (
        "## Uji luar\n\nPersen bobot yang ditandai pada data sampel kontekstual (tidak dipakai melatih).\n\n"
        + table(
            ["Sampel", "Bulan-pasien", *METHODS],
            [
                [
                    o["sample"],
                    thousands(o["patient_months"]),
                    *(f"{number(o[m])}%" for m in METHODS),
                ]
                for o in r["outside"]
            ],
        )
        + "\n"
        if r["outside"]
        else ""
    )
    return f"""# Perbandingan model anomali

Dibuat oleh `ai-service/scripts/compare_anomaly_models.py` pada {r["created_on"]}. Jangan disunting manual.

Tiga cara menandai tagihan bulanan pada data yang sama: {thousands(r["patient_months"])} bulan-pasien fisioterapi
(Juli–Desember {", ".join(r["years"])}, data sampel reguler BPJS), enam fitur yang sama, sekitar 1,5% bobot ditandai.

- **anomali-v1 (Isolation Forest)**: tabel skor Isolation Forest yang dibekukan (`model-anomali-v1.json`).
- **Kelangkaan nasional**: peluang pola secara nasional, tanpa kelompok.
- **anomali-v2 (umur)**: peluang pola di kelompok umur pasien, dihaluskan ke nasional (model yang dipakai).

## Hasil di data nyata

{main}

anomali-v1 tidak bisa dilatih ulang di sini, jadi tidak punya baris antartahun.

## Seberapa sering metode sepakat (Jaccard himpunan yang ditandai)

{agreement}

## Uji sisipan (sintetis)

{thousands(r["injection"]["count"])} bulan-pasien biasa 2024 (tidak terpicu aturan, tidak ditandai metode mana pun) diubah dengan
satu manipulasi, lalu dinilai. Persen = bagian yang tertangkap. Manipulasinya kami rancang sendiri, jadi ini
menunjukkan apa yang bisa dilihat tiap metode, bukan kinerja di lapangan. "Sebagian tanpa rujukan" adalah nilai
tengah sebuah fitur; "rujukan janggal" meniru temuan utama anomali-v1.

{injected}

{outside}
## Batasan

Tanpa label, tidak ada cara objektif memilih metode terbaik dari angka di atas. Yang menentukan adalah hasil
panggilan: berapa bagian yang ditandai tiap metode berakhir Tidak sesuai.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample",
        nargs=3,
        action="append",
        required=True,
        type=Path,
        metavar=("FKRTL", "KEPESERTAAN", "DIAGNOSIS_SEKUNDER"),
    )
    parser.add_argument(
        "--outside",
        nargs=2,
        action="append",
        default=[],
        type=Path,
        metavar=("FKRTL", "KEPESERTAAN"),
    )
    args = parser.parse_args()

    records = [
        r for fkrtl, membership, _ in args.sample for r in load_sample(fkrtl, membership=membership)
    ]
    years = sorted({r["month"][:4] for r in records})
    first = [r for r in records if r["month"][:4] == years[0]]
    last = [r for r in records if r["month"][:4] == years[-1]]
    outside = [
        (fkrtl.stem, load_sample(fkrtl, membership=membership))
        for fkrtl, membership in args.outside
    ]
    alpha = json.loads(V2.read_text(encoding="utf-8"))["alpha"]

    result = compare(records, first, last, outside, alpha) | {
        "created_on": date.today().isoformat()
    }
    assert_privacy_safe(result)
    write_json(OUTPUT, result, sort_keys=False)
    REPORT.write_text(report(result), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "report": str(REPORT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
