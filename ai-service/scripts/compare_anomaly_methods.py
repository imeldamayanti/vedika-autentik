#!/usr/bin/env python3
"""Benchmark four unsupervised methods on the same real data and write aggregates only.

Methods: Isolation Forest, Local Outlier Factor, One-Class SVM, and plain combination rarity (baseline).
All see the same six binned features of July-December participant-months and flag about 1.5% of the
national weight. Reports agreement, overlap with the rules, a 2023 -> 2024 test, and a synthetic
injection test (Tier B). Writes ai-service/data/reference/pola-2024/banding-metode.json and
data-uji-konfirmasi/referensi-pola/BANDING-METODE.md.
Run with `uv run --group data python scripts/compare_anomaly_methods.py --source <2023.dta> --source <2024.dta>`.
"""

from __future__ import annotations

import argparse
import json
import math
import warnings
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM

from vedika_ai.anomali_reference import SEEDS, SUBSAMPLE, TARGET_SHARE, TREES, in_window
from vedika_ai.claim_reference import assert_privacy_safe_aggregate
from vedika_ai.pola_reference import load_anomali, load_pola, patient_months, read_visits

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "ai-service" / "data" / "reference" / "pola-2024" / "banding-metode.json"
REPORT = ROOT / "data-uji-konfirmasi" / "referensi-pola" / "BANDING-METODE.md"

METHODS = ("Isolation Forest", "Local Outlier Factor", "One-Class SVM", "Kelangkaan gabungan")
VOTERS = ("Isolation Forest", "Local Outlier Factor", "Kelangkaan gabungan")
INJECTIONS = ("pemadatan seminggu", "rujukan janggal", "sesi hari Minggu", "tagihan digelembungkan")
INJECTED = 2000
LOF_NEIGHBOURS = 50
SVM_SAMPLE = 8000


def scorer(method: str, x: np.ndarray, weight: np.ndarray, centre: np.ndarray, spread: np.ndarray):
    """Train one method on x; return a function giving higher scores to more unusual rows."""

    def z(a):
        return (a - centre) / spread

    if method == "Isolation Forest":
        model = IsolationForest(
            n_estimators=TREES, max_samples=SUBSAMPLE, random_state=SEEDS[0]
        ).fit(x)
        return lambda a: -model.score_samples(a)
    if method == "Local Outlier Factor":
        model = LocalOutlierFactor(n_neighbors=LOF_NEIGHBOURS, novelty=True).fit(z(x))
        return lambda a: -model.score_samples(z(a))
    if method == "One-Class SVM":
        rows = np.random.RandomState(SEEDS[0]).choice(
            len(x), min(SVM_SAMPLE, len(x)), replace=False
        )
        model = OneClassSVM(nu=TARGET_SHARE, gamma="scale").fit(z(x[rows]))
        return lambda a: -model.decision_function(z(a))
    share = Counter()
    for row, w in zip(map(tuple, x), weight, strict=True):
        share[row] += w
    total = weight.sum()
    return lambda a: np.array([-math.log(share.get(tuple(r), 0) / total + 1e-9) for r in a])


def threshold(scores: np.ndarray, weight: np.ndarray) -> float:
    """Every row in a combination shares its score; take whole combinations until TARGET_SHARE is reached."""

    by_score = defaultdict(float)
    for s, w in zip(scores, weight, strict=True):
        by_score[s] += w
    cumulative, total = 0.0, weight.sum()
    for s in sorted(by_score, reverse=True):
        cumulative += by_score[s]
        if cumulative >= TARGET_SHARE * total:
            return s
    return min(by_score)


def fit(method, x, weight, centre, spread):
    f = scorer(method, x, weight, centre, spread)
    return f, threshold(np.round(f(x), 6), weight)


def flags(f, cut, x) -> np.ndarray:
    return np.round(f(x), 6) >= cut


def pct(mask: np.ndarray, weight: np.ndarray) -> float:
    return round(100 * float(weight[mask].sum() / weight.sum()), 2)


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    return round(float((a & b).sum() / (a | b).sum()), 2)


def inject(features: dict, kind: str) -> dict:
    f = dict(features)
    if kind == "pemadatan seminggu":
        f["maks_minggu"] += 2
        f["sesi"] += 2
    elif kind == "rujukan janggal":
        f.update(
            tanpa_rujukan=1.0,
            lintas_wilayah=1.0,
            episode=max(f["episode"], 6),
            sesi=max(f["sesi"], 5),
        )
    elif kind == "sesi hari Minggu":
        f["ahad_libur"] += 1
        f["sesi"] += 1
    else:
        f["sesi"] += 5
    return f


def compare(records: list[dict]) -> dict:
    anomali, pola = load_anomali(), load_pola()
    x = np.array([anomali.bin_fitur(r["fitur_anomali"]) for r in records], float)
    weight = np.array([r["bobot"] for r in records])
    triggered = np.array([r["dipicu"] for r in records])
    year = np.array([r["bulan"][:4] for r in records])
    centre, spread = x.mean(0), x.std(0)

    fitted = {m: fit(m, x, weight, centre, spread) for m in METHODS}
    flagged = {m: flags(*fitted[m], x) for m in METHODS}
    votes = sum(flagged[m].astype(int) for m in VOTERS)
    combos = {"Suara ≥ 2 dari 3": votes >= 2, "Salah satu dari 3 (ATAU)": votes >= 1}

    def row(mask):
        return {
            "persen_ditandai": pct(mask, weight),
            "persen_hanya_model": pct(mask & ~triggered, weight),
            "persen_aturan_atau_model": pct(mask | triggered, weight),
        }

    results = {m: row(flagged[m]) for m in METHODS} | {c: row(m) for c, m in combos.items()}

    earlier, later = year == min(year), year == max(year)
    for m in METHODS:
        past = flags(*fit(m, x[earlier], weight[earlier], centre, spread), x[later])
        present = flags(*fit(m, x[later], weight[later], centre, spread), x[later])
        results[m]["antartahun"] = {
            "persen_model_tahun_lalu": pct(past, weight[later]),
            "persen_model_tahun_ini": pct(present, weight[later]),
            "jaccard": jaccard(past, present),
        }

    rng = np.random.RandomState(SEEDS[1])
    ordinary = np.where(later & ~triggered & ~np.logical_or.reduce(list(flagged.values())))[0]
    chosen = rng.choice(ordinary, INJECTED, replace=False)
    injection = {}
    for kind in INJECTIONS:
        changed = [inject(records[i]["fitur_anomali"], kind) for i in chosen]
        xi = np.array([anomali.bin_fitur(f) for f in changed], float)
        caught = {m: flags(*fitted[m], xi) for m in METHODS}
        vote = sum(caught[m].astype(int) for m in VOTERS)
        rules = np.array([sum(pola.indikator({k: f[k] for k in pola.FITUR})) >= 2 for f in changed])
        injection[kind] = {
            "Aturan": round(100 * float(rules.mean()), 1),
            **{m: round(100 * float(caught[m].mean()), 1) for m in METHODS},
            "Suara ≥ 2 dari 3": round(100 * float((vote >= 2).mean()), 1),
            "Salah satu dari 3 (ATAU)": round(100 * float((vote >= 1).mean()), 1),
        }

    return {
        "bulan_pasien": len(records),
        "tahun": sorted(set(year)),
        "target_pangsa": TARGET_SHARE,
        "hasil": results,
        "jaccard_antarmetode": {
            a: {b: jaccard(flagged[a], flagged[b]) for b in METHODS} for a in METHODS
        },
        "persen_ditandai_keempatnya": pct(np.logical_and.reduce(list(flagged.values())), weight),
        "sisipan": {"jumlah": INJECTED, "hasil": injection},
    }


def angka(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def report(r: dict) -> str:
    hasil = r["hasil"]
    head = "| Metode | Ditandai | Hanya model | Aturan ATAU model | Antartahun: ditandai 2024 oleh model 2023 / 2024 | Antartahun: Jaccard |\n|---|---|---|---|---|---|\n"
    rows = "\n".join(
        f"| {m} | {angka(h['persen_ditandai'])}% | {angka(h['persen_hanya_model'])}% | {angka(h['persen_aturan_atau_model'])}% | "
        + (
            f"{angka(h['antartahun']['persen_model_tahun_lalu'])}% / {angka(h['antartahun']['persen_model_tahun_ini'])}% | {angka(h['antartahun']['jaccard'])} |"
            if "antartahun" in h
            else "– | – |"
        )
        for m, h in hasil.items()
    )
    jac = r["jaccard_antarmetode"]
    jac_rows = "\n".join(
        f"| {a} | " + " | ".join(angka(jac[a][b]) for b in METHODS) + " |" for a in METHODS
    )
    cols = ["Aturan", *METHODS, "Suara ≥ 2 dari 3", "Salah satu dari 3 (ATAU)"]
    inj = "\n".join(
        f"| {k} | " + " | ".join(f"{angka(v[c])}%" for c in cols) + " |"
        for k, v in r["sisipan"]["hasil"].items()
    )
    return f"""# Perbandingan metode deteksi anomali tanpa label

Dibuat oleh `ai-service/scripts/compare_anomaly_methods.py` pada {r["dibuat"]}. Jangan disunting manual.

Empat metode tanpa label dibandingkan pada data yang sama: {str(format(r["bulan_pasien"], ",")).replace(",", ".")} bulan-pasien fisioterapi nyata
(Juli–Desember {", ".join(r["tahun"])}, data sampel reguler BPJS), enam fitur yang sama dengan `anomali-v1`, dan
volume yang sama (sekitar {angka(100 * r["target_pangsa"])}% bobot nasional ditandai per metode).

- **Isolation Forest**: mengisolasi titik jarang dengan belahan acak (model `anomali-v1`).
- **Local Outlier Factor**: membandingkan kerapatan satu titik dengan {LOF_NEIGHBOURS} tetangganya.
- **One-Class SVM**: mempelajari batas di sekeliling tagihan normal (kernel RBF, dilatih pada {str(format(SVM_SAMPLE, ",")).replace(",", ".")} sampel).
- **Kelangkaan gabungan**: pembanding paling sederhana, seberapa jarang gabungan bin itu secara nasional.

Semua metode dinilai langsung dari skornya. Model `anomali-v1` yang disimpan memakai tabel, dan gabungan yang muncul
kurang dari 10 kali selalu ditandai; karena itu angka Isolation Forest di sini sedikit berbeda dari `EVALUASI-ANOMALI.md`.

## Hasil di data nyata

{head}{rows}

## Seberapa sering metode sepakat (Jaccard himpunan yang ditandai)

| | {" | ".join(METHODS)} |
|---|{"---|" * len(METHODS)}
{jac_rows}

Ditandai keempat metode sekaligus: {angka(r["persen_ditandai_keempatnya"])}% bobot.

## Uji sisipan (Tingkat B, sintetis)

{str(format(r["sisipan"]["jumlah"], ",")).replace(",", ".")} bulan-pasien biasa 2024 (tidak terpicu aturan, tidak ditandai metode mana pun) diubah dengan satu
manipulasi, lalu dinilai. Persen = bagian yang tertangkap. Manipulasinya kami rancang sendiri, jadi ini menguji
apa yang bisa dilihat tiap metode, bukan kinerja di lapangan. "Rujukan janggal" meniru pola temuan utama
Isolation Forest, jadi angka 100% di sana sebagian melingkar.

| Manipulasi | {" | ".join(cols)} |
|---|{"---|" * len(cols)}
{inj}

## Cara membaca

- Volume sama, orangnya berbeda: metode hanya sebagian sepakat. Local Outlier Factor dan Kelangkaan gabungan
  paling mirip karena keduanya pada dasarnya mengukur kerapatan.
- Tiap metode melihat hal yang berbeda: Isolation Forest satu-satunya yang menangkap gabungan rujukan janggal,
  tetapi lemah pada sesi hari Minggu; Local Outlier Factor dan Kelangkaan gabungan sebaliknya.
- One-Class SVM tidak cocok untuk enam fitur berbin kasar: di uji antartahun skornya mendatar untuk banyak
  gabungan sekaligus, sehingga ambang 1,5% tidak bisa dipasang.
- Tanpa label, tidak ada cara objektif memilih metode terbaik. Ukuran yang menentukan adalah hasil panggilan:
  berapa bagian yang ditandai tiap metode berakhir Tidak sesuai. Panggilan konfirmasi Vedika menghasilkan ukuran itu,
  dan ukuran yang sama bisa dipakai untuk mesin deteksi lain, termasuk milik BPJS.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        action="append",
        required=True,
        help="Regular FKRTL .dta, one per year",
    )
    parser.add_argument("--chunk-size", type=int, default=200_000)
    args = parser.parse_args()
    warnings.filterwarnings("ignore", category=UserWarning)
    records = [
        r
        for s in args.source
        for r in in_window(patient_months(read_visits(s.resolve(), args.chunk_size)))
    ]
    result = compare(records) | {"dibuat": date.today().isoformat()}
    assert_privacy_safe_aggregate(result)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(report(result), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "report": str(REPORT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
