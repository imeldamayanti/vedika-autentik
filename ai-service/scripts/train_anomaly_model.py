#!/usr/bin/env python3
"""Train anomali-v2 on the regular FKRTL samples and write the model, behaviour aggregates, and report.

Needs the raw samples, so it runs only on the laptop that holds them:

    uv run --group data python scripts/train_anomaly_model.py \\
        --sample <2023 fkrtl.dta> <2023 kepesertaan.dta> <2023 diagnosissekunder.dta> \\
        --sample <2024 fkrtl.dta> <2024 kepesertaan.dta> <2024 diagnosissekunder.dta> \\
        --outside <disease-specific fkrtl.dta> <its kepesertaan.dta>

Writes data-uji-konfirmasi/referensi-pola/model-anomali-v2.json (the scorer is tools/anomali.py),
ai-service/data/reference/anomali/anomali-nyata.json, and data-uji-konfirmasi/referensi-pola/EVALUASI-ANOMALI.md.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path

from vedika_ai.ml import anomaly_evaluation as evaluation
from vedika_ai.ml import anomaly_model, tools
from vedika_ai.ml.cohort import load_sample
from vedika_ai.ml.privacy import assert_privacy_safe, write_json
from vedika_ai.ml.report import number, table, thousands

MODEL = tools.MODEL_DIR / "model-anomali-v2.json"
REAL = tools.REFERENCE_DIR / "anomali" / "anomali-nyata.json"
REPORT = tools.MODEL_DIR / "EVALUASI-ANOMALI.md"

GROUP_NAMES = {
    "flagged_by_model": "Ditandai model",
    "triggered_by_rules": "Dipicu aturan (≥ 2 indikator)",
    "both": "Keduanya",
    "model_only": "Hanya model (tidak terlihat aturan)",
    "rules_only": "Hanya aturan",
    "called": "Ditelepon: aturan ATAU model",
}
FEATURE_NAMES = {
    "sesi": "Sesi sebulan",
    "maks_minggu": "Sesi terbanyak seminggu",
    "ahad_libur": "Sesi hari Minggu",
    "episode": "Bulan berturut-turut",
    "tanpa_rujukan": "Kunjungan tanpa rujukan FKTP",
    "lintas_wilayah": "Dirujuk dari kab/kota lain",
    "pattern": "Hanya gabungannya yang jarang",
}
AGE_ORDER = ["<18", "18-39", "40-59", "60+", "tidak diketahui"]
CONTEXT_NAMES = {
    None: "Nasional (tanpa kelompok)",
    "age_group": "Kelompok umur",
    "condition": "Diagnosis sekunder",
}


def verdict(forward: list[dict], backward: list[dict]) -> str:
    """Held-out gain of each context over national, at its best smoothing, in both directions."""

    def best(comparison: list[dict], context: str | None) -> dict:
        return max(
            (r for r in comparison if r["context"] == context), key=lambda r: r["log_likelihood"]
        )

    sentences = []
    for context in ("age_group", "condition"):
        gains = [
            best(c, context)["log_likelihood"] - best(c, None)["log_likelihood"]
            for c in (forward, backward)
        ]
        alphas = {best(c, context)["alpha"] for c in (forward, backward)}
        sentence = (
            f"{CONTEXT_NAMES[context]}: selisih terhadap nasional {number(gains[0], 4)} (2023 ke 2024) dan "
            f"{number(gains[1], 4)} (2024 ke 2023)."
        )
        if alphas == {max(anomaly_model.ALPHAS)} and max(gains) < 0.005:
            sentence += " Selisih ini hanya muncul pada penghalusan terkuat, saat model hampir sama dengan nasional."
        sentences.append(sentence)
    return "\n".join(f"- {s}" for s in sentences)


def context_section(forward: list[dict], backward: list[dict], model: dict) -> str:
    rows = [
        [
            CONTEXT_NAMES[f["context"]],
            f["groups"] or "–",
            number(f["alpha"], 0),
            number(f["log_likelihood"], 4),
            number(b["log_likelihood"], 4),
        ]
        for f, b in zip(forward, backward, strict=True)
    ]
    return f"""## Memilih kelompok pembanding

Pola dinilai jarang dibanding pasien sekelompok. Kelompok dipilih dengan data tahun lain yang tidak dipakai
melatih: rata-rata log-peluang berbobot (makin tinggi makin baik) dari model yang dilatih satu tahun dan dinilai
pada tahun lainnya. Alfa = kekuatan penghalusan ke pangsa nasional.

{table(["Kelompok", "Jumlah kelompok", "Alfa", "Latih 2023, uji 2024", "Latih 2024, uji 2023"], rows)}

{verdict(forward, backward)}

Model memakai {CONTEXT_NAMES[model["context"]].lower()} dengan alfa {number(model["alpha"], 0)}, alfa dengan
log-peluang tertinggi di kedua arah.
"""


def report(model: dict, real: dict) -> str:
    behaviour = real["behaviour"]
    groups = table(
        ["Kelompok", "Bulan-pasien", "Kunjungan", "Bobot nasional", "Per bulan"],
        [
            [
                GROUP_NAMES[g["group"]],
                thousands(g["patient_months"]),
                thousands(g["visits"]),
                f"{number(g['percent'])}%",
                f"≈{thousands(g['per_month_national'])}",
            ]
            for g in behaviour["groups"]
        ],
    )
    ages = table(
        ["Kelompok umur", "Bulan-pasien", "Ditandai model"],
        [
            [a["age_group"], thousands(a["patient_months"]), f"{number(a['percent_flagged'])}%"]
            for a in sorted(
                behaviour["by_age_group"], key=lambda a: AGE_ORDER.index(a["age_group"])
            )
        ],
    )
    reasons = table(
        ["Alasan pertama", "Bulan-pasien"],
        [
            [FEATURE_NAMES[r["feature"]], thousands(r["patient_months"])]
            for r in behaviour["first_reason_model_only"]
        ],
    )
    patterns = table(
        ["Pola", "Bulan-pasien"],
        [
            [", ".join(p["pattern"]), thousands(p["patient_months"])]
            for p in behaviour["top_patterns_model_only"]
        ],
    )
    data = table(
        ["Berkas", "Tahun", "Bulan-pasien (Juli–Desember)"],
        [
            [f"`{d['file']}`", ", ".join(d["years"]), thousands(d["patient_months"])]
            for d in real["data"]
        ],
    )
    over = real["over_time"]
    train, test = ", ".join(over["train_years"]), ", ".join(over["test_years"])
    over_time = table(
        ["Ukuran", "Hasil"],
        [
            [
                f"Ditandai di {test} oleh model {train}",
                f"{number(over['percent_flagged_by_past_model'])}%",
            ],
            [
                f"Ditandai di {test} oleh model {test}",
                f"{number(over['percent_flagged_by_own_model'])}%",
            ],
            ["Irisan (Jaccard) kedua himpunan yang ditandai", number(over["jaccard"], 3)],
            [
                f"Hanya model (tidak terpicu aturan), model {train}",
                f"{number(over['percent_model_only_by_past_model'])}%",
            ],
            [
                f"Bobot {test} pada pola yang tidak ada di tabel {train}",
                f"{number(over['percent_patterns_unknown_to_past_model'])}%",
            ],
        ],
    )
    outside = (
        "## Uji luar (tidak dipakai melatih)\n\n"
        "Model akhir dipakai pada data sampel kontekstual: peserta yang dipilih karena penyakit tertentu, jadi bukan\n"
        "gambaran semua pasien fisioterapi. Bobotnya mewakili kelompok penyakit itu.\n\n"
        + table(
            ["Sampel", "Tahun", "Bulan-pasien", "Ditandai model", "Dipicu aturan", "Hanya model"],
            [
                [
                    o["sample"],
                    f"{o['years'][0]}–{o['years'][-1]}",
                    thousands(o["patient_months"]),
                    f"{number(o['percent_flagged'])}%",
                    f"{number(o['percent_triggered'])}%",
                    f"{number(o['percent_model_only'])}%",
                ]
                for o in real["outside"]
            ],
        )
        + "\n"
        if real["outside"]
        else ""
    )
    hospitals = real["hospitals"]
    return f"""# Evaluasi model anomali ({model["version"]})

Dibuat oleh `ai-service/scripts/train_anomaly_model.py` pada {
        model["trained_on"]
    }. Jangan disunting manual.

## Apa yang dilakukan model

Model **tanpa label** mengukur seberapa jarang pola satu tagihan bulanan fisioterapi di antara pasien
seusia, dari {
        thousands(model["training"]["patient_months"])
    } bulan-pasien data sampel reguler BPJS {model["years"]}.
Pola = enam fitur yang bisa dikonfirmasi peserta lewat telepon: sesi sebulan, sesi terbanyak seminggu, sesi hari
Minggu, bulan berturut-turut, pangsa kunjungan tanpa rujukan FKTP, dan pangsa yang dirujuk dari kab/kota lain.

Peluang pola p dihitung dari pangsa berbobot pola itu di kelompok umur pasien, dihaluskan ke pangsa nasional
(alfa {number(model["alpha"], 0)}); skor = −ln p. Ditandai bila skor ≥ {
        number(model["threshold"], 4)
    }, yaitu
peluang di bawah {number(100 * math.exp(-model["threshold"]), 3)}%. Ambang dipilih supaya sekitar
{
        number(100 * model["target_share"], 1)
    }% bobot nasional ditandai, setara aturan. Pasien ditelepon bila
**aturan (≥ 2 indikator) ATAU model** menandainya; hasilnya tetap ditentukan jawaban peserta.

{context_section(real["contexts"]["forward"], real["contexts"]["backward"], model)}
## Data

{data}

Hanya Juli–Desember tiap berkas yang dinilai: bulan berturut-turut melihat 6 bulan ke belakang dan tiap berkas
mulai Januari. Berkas tidak digabung per peserta.

## Privasi

- Model menyimpan pangsa pola dan pangsa bin hanya untuk sel dengan minimal {
        model["minimum_cell"]
    } bulan-pasien
  ({
        len(model["patterns"])
    } pola nasional). Tidak ada baris, nomor peserta, atau nilai minimum/maksimum.
- Pola yang lebih jarang dari itu tidak disimpan dan selalu ditandai.
- Batas bin ditetapkan tangan (ambang aturan dan angka bulat), bukan dari data.

## Perilaku di data nyata

"Per bulan" = perkiraan nasional dengan bobot sampel, rata-rata atas {behaviour["months"]} bulan.

{groups}

- Persen ditandai per bulan (tanpa bobot): {number(behaviour["monthly_percent"]["low"])}% sampai {
        number(behaviour["monthly_percent"]["high"])
    }%.

Per kelompok umur:

{ages}

Alasan pertama pada kasus "hanya model":

{reasons}

Pola "hanya model" yang paling sering:

{patterns}

## Validasi antartahun

{over_time}

{outside}
## Tingkat RS (corong)

Untuk tiap kelompok RS sejenis (kab/kota + kepemilikan + jenis + tipe) dengan minimal
{
        hospitals["minimum_patient_months"]
    } bulan-pasien: jumlah bulan-pasien yang dipilih (aturan ATAU model) dibanding
harapan menurut umur pasiennya. Simpangan dilebarkan dengan faktor sebaran antar-RS
{
        number(hospitals["overdispersion"], 2)
    } (penyesuaian overdispersi Spiegelhalter), karena RS memang lebih beragam
dari yang dijelaskan umur saja.

{
        table(
            ["Ukuran", "Hasil"],
            [
                ["Kelompok RS sejenis yang dinilai", hospitals["peer_groups"]],
                ["Di atas batas 95%", hospitals["above_95"]],
                ["Di atas batas 99,8%", hospitals["above_99_8"]],
                [
                    "Pangsa pasien dipilih yang berada di kelompok di atas 99,8%",
                    f"{number(hospitals['percent_selected_in_above_99_8'], 1)}%",
                ],
            ],
        )
    }

Identitas kelompok tidak disimpan.

## Batasan

- Tidak ada label kecurangan, jadi angka di atas adalah perilaku, bukan ketepatan. Ketepatan diukur dari hasil
  panggilan: berapa yang ditandai model berakhir Tidak sesuai.
- Jarang tidak sama dengan curang: pola yang jarang bisa sah.
- Nomor rujukan FKTP kosong bisa berarti kunjungan kontrol dengan surat kontrol RS. Arti sinyal ini perlu
  dipastikan bersama verifikator BPJS.
- Data sampel tidak memuat identitas RS, jadi kelompok RS sejenis hanya mendekati satu RS.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--sample",
        nargs=3,
        action="append",
        required=True,
        type=Path,
        metavar=("FKRTL", "KEPESERTAAN", "DIAGNOSIS_SEKUNDER"),
        help="One regular sample year",
    )
    parser.add_argument(
        "--outside",
        nargs=2,
        action="append",
        default=[],
        type=Path,
        metavar=("FKRTL", "KEPESERTAAN"),
        help="A disease-specific sample, scored only",
    )
    args = parser.parse_args()

    samples = [
        (fkrtl, load_sample(fkrtl, membership=membership, secondary=secondary))
        for fkrtl, membership, secondary in args.sample
    ]
    records = [r for _, rows in samples for r in rows]
    years = sorted({r["month"][:4] for r in records})
    if len(years) < 2:
        parser.error(
            "Two sample years are needed to choose the context and check stability over time."
        )
    by_year = {year: [r for r in records if r["month"][:4] == year] for year in years}
    first, last = by_year[years[0]], by_year[years[-1]]

    forward = anomaly_model.compare_contexts(first, last)
    backward = anomaly_model.compare_contexts(last, first)
    alpha = anomaly_model.best_alpha(forward, backward)
    model = anomaly_model.fit(records, alpha=alpha)
    model["training"] = {
        "patient_months": len(records),
        "months": sorted({r["month"] for r in records}),
    }
    model["trained_on"] = date.today().isoformat()

    outside = [
        evaluation.outside(fkrtl.stem, load_sample(fkrtl, membership=membership), model)
        for fkrtl, membership in args.outside
    ]
    real = {
        "data": [
            {
                "file": fkrtl.name,
                "years": sorted({r["month"][:4] for r in rows}),
                "patient_months": len(rows),
            }
            for fkrtl, rows in samples
        ],
        "contexts": {"forward": forward, "backward": backward},
        "behaviour": evaluation.behaviour(model, records),
        "over_time": evaluation.over_time(first, last, alpha=alpha),
        "outside": [o for o in outside if o],
        "hospitals": evaluation.hospitals(model, records),
        "created_on": model["trained_on"],
    }
    assert_privacy_safe(real)
    write_json(MODEL, model, sort_keys=False)
    write_json(REAL, real, sort_keys=False)
    REPORT.write_text(report(model, real), encoding="utf-8")
    print(json.dumps({"model": str(MODEL), "alpha": alpha, "threshold": model["threshold"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
