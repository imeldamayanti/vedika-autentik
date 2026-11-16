#!/usr/bin/env python3
"""Train the pola-v1 queue score by knowledge-guided weak supervision.

Normal class: patient-months drawn from the committed national histogram. Violation class: the same draws
after rule-like manipulations. Reads committed aggregates only, never raw data.

    uv run --group data python scripts/train_pattern_model.py [--label-panggilan <file>]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter
from datetime import date
from pathlib import Path

from loguru import logger

from vedika_ai.ml import tools
from vedika_ai.ml.pattern_reference import histogram_levels, weighted_percentile
from vedika_ai.ml.report import fixed, thousands

REFERENCE = tools.REFERENCE_DIR / "pola-2024"
DEMO_DATA = tools.ROOT / "data-uji-konfirmasi"
OUTPUT = tools.MODEL_DIR
DEMO_MONTH = "2026-08"
HONEST_HOSPITALS = ("RS02", "RS03", "RS04", "RS05")
# Patients made unusual on purpose so that only the anomaly model picks them; not a sample of the population.
MODEL_ONLY_PATIENTS = ("P-M1", "P-M2")
SEED = 2026
SAMPLES_PER_CLASS = 50_000
HIGH_PERCENTILE = 0.985
LABEL_WEIGHT = 5.0
FEATURE_MISMATCH_LIMIT = 3.0
HOSPITAL_TYPES = {
    "Pemerintah kelas B": "RS Kelas B",
    "Pemerintah kelas C": "RS Kelas C",
    "Swasta setara kelas B": "RS Swasta Setara Type B",
    "Swasta setara kelas C": "RS Swasta Setara Type C",
}
NATIONAL = "Nasional"
MODEL_KEYS = (
    "versi",
    "fitur",
    "bin",
    "intersep",
    "koefisien",
    "ambang_tinggi",
    "dilatih_dari",
    "tanggal",
)
pola = tools.pola()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def split_cell(row: dict, levels: list[dict], marginal: dict) -> list[dict]:
    """One histogram cell as fine-bin cells. A coarse cell (level > 0) is split by the national marginals
    inside its range, assuming the features are independent within the cell. The top bin uses its lower bound."""
    choices = []
    for feature in pola.FITUR:
        members = levels[int(row["tingkat"])][feature][row[feature]]
        share = {b: marginal[feature].get(b, 0.0) for b in members}
        total = sum(share.values())
        choices.append(
            [(b, share[b] / total) for b in members if share[b] > 0]
            if total
            else [(members[0], 1.0)]
        )
    cells = [({}, float(row["bobot"]))]
    for feature, options in zip(pola.FITUR, choices, strict=True):
        cells = [
            ({**values, feature: int(b.rstrip("+"))}, weight * part)
            for values, weight in cells
            for b, part in options
        ]
    return [{**values, "bobot": weight} for values, weight in cells]


def read_histogram(marginal: dict) -> list[dict]:
    levels = histogram_levels()
    return [
        cell
        for row in read_csv(REFERENCE / "histogram.csv")
        for cell in split_cell(row, levels, marginal)
    ]


def manipulate(features: dict, rng: random.Random) -> dict:
    """1-2 random manipulations that mimic tools/generate.py and rules I1-I4."""
    f = dict(features)

    def add_sessions():
        f["sesi"] += rng.randint(2, 6)
        f["maks_minggu"] = max(f["maks_minggu"], math.ceil(f["sesi"] / 4) + rng.randint(0, 1))

    def holiday_sessions():
        f["ahad_libur"] += rng.randint(1, 2)
        f["sesi"] += 1

    def compress_week():
        f["maks_minggu"] = max(f["maks_minggu"], rng.randint(3, 5))
        f["sesi"] = max(f["sesi"], f["maks_minggu"])

    def extend_episode():
        f["episode"] = min(pola.EPISODE_MAKS, f["episode"] + rng.randint(3, 6))

    # Extending the episode only ever comes together with another manipulation.
    chosen = (
        rng.sample([add_sessions, holiday_sessions, compress_week, extend_episode], 2)
        if rng.randint(1, 2) == 2
        else [rng.choice([add_sessions, holiday_sessions, compress_week])]
    )
    for change in chosen:
        change()
    return f


def training_samples(histogram: list[dict]) -> tuple[list[dict], list[int]]:
    rng = random.Random(SEED)
    weights = [r["bobot"] for r in histogram]
    normal = [
        {f: r[f] for f in pola.FITUR} for r in rng.choices(histogram, weights, k=SAMPLES_PER_CLASS)
    ]
    origins = rng.choices(histogram, weights, k=SAMPLES_PER_CLASS)
    violations = [manipulate({f: r[f] for f in pola.FITUR}, rng) for r in origins]
    return normal + violations, [0] * SAMPLES_PER_CLASS + [1] * SAMPLES_PER_CLASS


def columns(features: list[str]) -> list[tuple[str, str]]:
    return [(f, b) for f in features for b in pola.BIN[f]]


def one_hot(binned: list[dict], features: list[str]):
    import numpy

    index = {key: n for n, key in enumerate(columns(features))}
    x = numpy.zeros((len(binned), len(index)), dtype="float64")
    for n, row in enumerate(binned):
        for f in features:
            x[n, index[(f, row[f])]] = 1.0
    return x


def train(binned: list[dict], y: list[int], features: list[str], weights=None):
    from sklearn.linear_model import LogisticRegression

    model = LogisticRegression(C=1.0, max_iter=1000, random_state=SEED)
    model.fit(one_hot(binned, features), y, sample_weight=weights)
    return model


def held_out_auc(binned: list[dict], y: list[int], features: list[str]) -> float:
    """AUC on the 20% of samples not used for training."""
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split

    train_rows, test_rows = train_test_split(
        list(range(len(y))), test_size=0.2, random_state=SEED, stratify=y
    )
    model = train([binned[i] for i in train_rows], [y[i] for i in train_rows], features)
    probability = model.predict_proba(one_hot([binned[i] for i in test_rows], features))[:, 1]
    return float(roc_auc_score([y[i] for i in test_rows], probability))


def model_json(model, features: list[str], version: str) -> dict:
    coefficients = dict(zip(columns(features), model.coef_[0], strict=True))
    return {
        "versi": version,
        "fitur": features,
        "bin": {f: pola.BIN[f] for f in features},
        "intersep": round(float(model.intercept_[0]), 4),
        "koefisien": {
            f: {b: round(float(coefficients[(f, b)]), 4) for b in pola.BIN[f]} for f in features
        },
        "dilatih_dari": "ai-service/data/reference/pola-2024",
        "tanggal": date.today().isoformat(),
    }


def demo_features() -> dict[tuple[str, str], dict]:
    """(participant id, hospital id) -> raw features of August 2026 from klaim_sesi.csv."""
    holidays = {
        date.fromisoformat(r["tanggal"]) for r in read_csv(DEMO_DATA / "libur_nasional_2026.csv")
    }
    sessions = [
        ((r["id_peserta"], r["id_rs"]), date.fromisoformat(r["tanggal"]))
        for r in read_csv(DEMO_DATA / "klaim_sesi.csv")
    ]
    return pola.fitur_per_pasien(sessions, DEMO_MONTH, holidays)


def feature_fit(demo: dict, marginal: dict) -> list[dict]:
    """Top bin of each feature: share among honest demo patients (RS02-RS05) against the national share."""
    honest = [
        f
        for (participant, hospital), f in demo.items()
        if hospital in HONEST_HOSPITALS and participant not in MODEL_ONLY_PATIENTS
    ]
    result = []
    for f in pola.FITUR:
        top = [b for b in pola.BIN[f] if b in marginal[f]][-1]
        cutoff = pola.BIN[f].index(top)
        demo_share = sum(
            pola.BIN[f].index(pola.bin_nilai(f, x[f])) >= cutoff for x in honest
        ) / len(honest)
        national_share = marginal[f][top]
        result.append(
            {
                "fitur": f,
                "bin": top,
                "demo": demo_share,
                "nasional": national_share,
                "dibuang": demo_share > FEATURE_MISMATCH_LIMIT * national_share,
            }
        )
    return result


def threshold_and_rate(model: dict, histogram: list[dict]) -> tuple[float, float]:
    scored = [(pola.skor(model, r), r["bobot"]) for r in histogram]
    threshold = weighted_percentile(scored, HIGH_PERCENTILE)
    total = sum(w for _, w in scored)
    return threshold, sum(w for s, w in scored if s >= threshold) / total


def evaluate_demo(model: dict, demo: dict) -> dict:
    """Tier B: scores against kunci_kebenaran (read only here; the backend and seed never read it)."""
    from sklearn.metrics import roc_auc_score

    inflated = {
        (r["id_peserta"], r["id_rs"]): int(r["sesi_ditagih"]) - int(r["sesi_sebenarnya"]) > 2
        for r in read_csv(DEMO_DATA / f"kunci_kebenaran_{DEMO_MONTH}.csv")
    }
    keys = sorted(demo)
    y = [int(inflated[k]) for k in keys]
    scores = [pola.skor(model, demo[k]) for k in keys]
    indicator_counts = [sum(pola.indikator(demo[k])) for k in keys]
    triggered = [n >= 2 for n in indicator_counts]
    high = [s >= model["ambang_tinggi"] for s in scores]
    n_triggered = sum(triggered)
    top = sorted(range(len(keys)), key=lambda i: (-scores[i], keys[i]))[:n_triggered]

    def both(a, b):
        return sum(x and z for x, z in zip(a, b, strict=True))

    return {
        "bulan_pasien": len(keys),
        "digelembungkan": sum(y),
        "auc_skor": float(roc_auc_score(y, scores)),
        "auc_jumlah_indikator": float(roc_auc_score(y, indicator_counts)),
        "dipicu": n_triggered,
        "presisi_aturan": both(triggered, y) / n_triggered,
        "recall_aturan": both(triggered, y) / sum(y),
        "presisi_at_n": sum(y[i] for i in top) / n_triggered,
        "tinggi": sum(high),
        "tinggi_digelembungkan": both(high, y),
        "lolos_aturan": sum(b and not a for a, b in zip(triggered, y, strict=True)),
        "lolos_aturan_tapi_tinggi": sum(
            b and not a and h for a, b, h in zip(triggered, y, high, strict=True)
        ),
    }


def mean_score_per_combination(
    model: dict, histogram: list[dict]
) -> list[tuple[str, float, float]]:
    """Tier A: weighted mean score per rule combination, over histogram cells that are not suppressed."""
    total_score, weight = Counter(), Counter()
    for r in histogram:
        key = pola.kombinasi(*pola.indikator(r))
        total_score[key] += pola.skor(model, r) * r["bobot"]
        weight[key] += r["bobot"]
    total = sum(weight.values())
    return [(k, total_score[k] / weight[k], weight[k] / total) for k in sorted(weight)]


def demo_scores(model: dict, reference: dict, demo: dict) -> list[dict]:
    rows = []
    for (participant, hospital), f in sorted(demo.items()):
        value = pola.skor(model, f)
        rows.append(
            {
                "id_peserta": participant,
                "id_rs": hospital,
                "bulan": DEMO_MONTH,
                "fitur": f,
                "skor": value,
                "logit": pola.logit(model, f),
                "tinggi": value >= model["ambang_tinggi"],
                "alasan": pola.alasan(model, reference, f),
            }
        )
    return rows


def real_data_section(model: dict) -> list[str]:
    """Tier A: behaviour on every real 2024 patient-month (perilaku-nyata.json, from check_pattern_real_data.py)."""
    path = REFERENCE / "perilaku-nyata.json"
    if not path.exists():
        return []
    d = read_json(path)
    if (d["versi_model"], d["ambang_tinggi"]) != (model["versi"], model["ambang_tinggi"]):
        return [
            "### Perilaku pada data nyata",
            "",
            "`perilaku-nyata.json` dihitung untuk model lain. Jalankan ulang `scripts/check_pattern_real_data.py`.",
            "",
        ]
    cross = d["silang"]

    def cell(key):
        return (
            f"{thousands(cross[key]['n'])} ({fixed(cross[key]['persen'], 2)}%)"
            if key in cross
            else "kurang dari 10"
        )

    untriggered = ", ".join(
        f"{k} saja {thousands(v['n'])}" for k, v in d["tinggi_tidak_terpicu_per_kombinasi"].items()
    )
    monthly = [v["persen_tinggi"] for v in d["per_bulan"].values()]
    shown_as_one = d["terpicu_tampil_satu"].get("n", "kurang dari 10")
    groups = d["kelompok"]
    return [
        "### Perilaku pada data nyata",
        "",
        f"Model diterapkan ke semua {thousands(d['n'])} bulan-pasien nyata 2024 di laptop (data mentah tidak di-commit; "
        "hanya agregat di `ai-service/data/reference/pola-2024/perilaku-nyata.json`). Ini perilaku, bukan akurasi: "
        "data sampel tidak punya label kecurangan, dan kelas normal model berasal dari data yang sama.",
        "",
        f"- Pola tidak biasa: **{fixed(d['persen_tinggi'], 2)}%** bulan-pasien (berbobot); pemicu aturan {fixed(d['persen_terpicu'], 2)}%.",
        f"- Per bulan (tak berbobot): {fixed(min(monthly), 1)}% sampai {fixed(max(monthly), 1)}%.",
        f"- Terpicu aturan dan pola tidak biasa: {cell('tinggi_terpicu')}. Terpicu tetapi skor di bawah ambang: {cell('biasa_terpicu')}.",
        f"- Pola tidak biasa tanpa pemicu aturan: {cell('tinggi_tidak_terpicu')}, yaitu {untriggered}.",
        f"- Dari {thousands(d['terpicu']['n'])} bulan-pasien terpicu, {shown_as_one} tampil dengan skor 1,00.",
        f"- {thousands(groups['n'])} kelompok RS sejenis (≥ 30 bulan-pasien): {thousands(groups['tanpa_tinggi'])} tanpa satu pun pola tidak biasa; "
        f"10% kelompok teratas memuat {groups['persen_tinggi_di_10_persen_teratas']}% bulan-pasien berpola tidak biasa.",
        "",
    ]


def evaluation_report(
    model, fit, synthetic_auc, rate, per_combination, demo_eval, manifest, sunday_share
) -> str:
    dropped = [k["fitur"] for k in fit if k["dibuang"]]
    suppressed = manifest["suppression"]["histogram"]["weight_share_suppressed"]
    lines = [
        "# Evaluasi skor pola (`pola-v1`)",
        "",
        f"Dibuat otomatis oleh `ai-service/scripts/train_pattern_model.py` pada {model['tanggal']}. "
        "Jangan disunting tangan.",
        "",
        "Angka di bawah dilaporkan per tingkat bukti dan tidak digabung. Tier A = agregat data sampel "
        "BPJS 2024 (nyata). Tier B = data sintetis (metode dan demo), bukan bukti kinerja di lapangan.",
        "",
        "## Cek kecocokan fitur (sebelum melatih)",
        "",
        "Pangsa bulan-pasien di bin teratas: RS demo jujur (RS02 sampai RS05, Agustus 2026, Tier B) dibanding "
        f"nasional 2024 (Tier A). Fitur dibuang bila pangsa demo lebih dari {FEATURE_MISMATCH_LIMIT:g} kali nasional.",
        "",
        "| Fitur | Bin teratas | Demo jujur | Nasional | Keputusan |",
        "|---|---|---|---|---|",
        *[
            f"| `{k['fitur']}` | {k['bin']} | {fixed(100 * k['demo'], 2)}% | "
            f"{fixed(100 * k['nasional'], 2)}% | {'dibuang' if k['dibuang'] else 'dipakai'} |"
            for k in fit
        ],
        "",
        f"Fitur yang dibuang: {', '.join(dropped) if dropped else 'tidak ada'}. "
        f"Fitur model: {', '.join(model['fitur'])}.",
        "",
        "## Tier B (sintetis, hanya uji kewajaran metode)",
        "",
        f"- AUC normal vs pelanggaran buatan pada 20% data tahan: **{fixed(synthetic_auc)}** "
        f"({thousands(SAMPLES_PER_CLASS)} + {thousands(SAMPLES_PER_CLASS)} sampel).",
        "- Kelas pelanggaran dibuat dari aturan yang sama dengan yang diuji, jadi angka ini hanya "
        "menunjukkan model mempelajari manipulasi tersebut. Ini bukan akurasi deteksi.",
        "",
        "## Tier A (agregat nasional 2024)",
        "",
        f"- Ambang `ambang_tinggi` = **{fixed(model['ambang_tinggi'])}** (persentil berbobot "
        f"{fixed(100 * HIGH_PERCENTILE, 1)} skor atas histogram nasional).",
        f"- Pangsa bulan-pasien nasional dengan skor ≥ ambang: **{fixed(100 * rate, 2)}%**.",
        f"- Histogram bertingkat: sel di bawah 10 baris digabung ke rentang yang lebih kasar (batas rentang tepat di "
        f"ambang aturan), dan hanya sisa yang tetap di bawah 10 baris di tingkat terkasar yang disembunyikan "
        f"({fixed(100 * suppressed, 2)}% bobot). Bulan-pasien dengan sesi hari Minggu ({fixed(100 * sunday_share, 2)}% "
        f"nasional) ikut masuk kelas normal lewat sel kasar. Pangsa nasional sebenarnya di antara kira-kira "
        f"{fixed(100 * rate * (1 - suppressed), 1)}% dan {fixed(100 * (rate * (1 - suppressed) + suppressed), 1)}%.",
        "",
        "Rata-rata skor per kombinasi aturan (sel histogram yang tidak tersembunyi):",
        "",
        "| Kombinasi | Rata-rata skor | Pangsa bobot |",
        "|---|---|---|",
        *[f"| {k} | {fixed(s)} | {fixed(100 * p, 2)}% |" for k, s, p in per_combination],
        "",
        *real_data_section(model),
        "## Tier B (data demo vs `kunci_kebenaran_2026-08.csv`)",
        "",
        f"{demo_eval['bulan_pasien']} bulan-pasien Agustus 2026, {demo_eval['digelembungkan']} di antaranya "
        "digelembungkan (selisih ditagih dan sebenarnya lebih dari 2). Kunci kebenaran hanya dibaca di evaluasi offline ini.",
        "",
        f"- AUC skor pola: **{fixed(demo_eval['auc_skor'])}**.",
        f"- AUC `jumlah_indikator` (pembanding): **{fixed(demo_eval['auc_jumlah_indikator'])}**.",
        f"- Pemicu aturan (≥ 2 indikator, {demo_eval['dipicu']} bulan-pasien): presisi "
        f"**{fixed(demo_eval['presisi_aturan'])}**, recall **{fixed(demo_eval['recall_aturan'])}**.",
        f"- Presisi@{demo_eval['dipicu']} skor pola: **{fixed(demo_eval['presisi_at_n'])}**.",
        f"- Skor ≥ ambang: {demo_eval['tinggi']} bulan-pasien, {demo_eval['tinggi_digelembungkan']} di "
        "antaranya digelembungkan.",
        f"- Digelembungkan tetapi tidak terpicu aturan: {demo_eval['lolos_aturan']}; di antaranya "
        f"**{demo_eval['lolos_aturan_tapi_tinggi']}** berskor ≥ ambang (tampil sebagai informasi, tidak ditelepon).",
        "",
        "## Koefisien",
        "",
        f"Intersep: {fixed(model['intersep'], 4)}. Skor = logistik(intersep + jumlah koefisien bin yang aktif).",
        "",
        "| Fitur | Bin | Koefisien |",
        "|---|---|---|",
        *[
            f"| `{f}` | {b} | {fixed(k, 4)} |"
            for f in model["fitur"]
            for b, k in model["koefisien"][f].items()
        ],
        "",
        "## Batasan",
        "",
        '- Skor berarti "mirip pola manipulasi yang dikenal, dibanding pola nasional 2024". '
        "Skor bukan peluang kecurangan dan bukan putusan.",
        "- Kelas normal adalah data nyata apa adanya, jadi bisa memuat manipulasi yang tidak terdeteksi.",
        "- Di data nyata 2024 tidak ada daftar libur, jadi `ahad_libur` dan I4 hanya menghitung hari Minggu.",
        "- Sel kasar dipecah ke bin halus memakai marginal nasional, dengan anggapan fitur saling bebas di "
        "dalam sel itu. Sesi hari Minggu di data nyata hanya muncul di sel kasar dengan paling banyak 2 sesi "
        "seminggu; Minggu bersama 3 sesi atau lebih seminggu tetap tersembunyi.",
        "- Data sampel tidak memuat identitas RS dan tidak memuat bulan sebelum Januari 2024.",
        "- Skor hanya mengurutkan antrean. Pemicu panggilan, label, saran, dan status RS tetap dari aturan.",
        "",
    ]
    return "\n".join(lines)


def label_section(
    model_v2: dict, n: int, n_mismatch: int, auc_v1: float, auc_v2: float, demo_eval: dict
) -> str:
    return "\n".join(
        [
            "## Dengan label panggilan (`pola-v2`)",
            "",
            f"Dilatih ulang pada {model_v2['tanggal']} dengan {n} hasil panggilan ({n_mismatch} Tidak sesuai) "
            f"sebagai sampel berlabel berbobot {LABEL_WEIGHT:g}, di atas sampel sintetis yang sama. "
            "Di demo, label ini berasal dari panggilan sintetis, jadi bagian ini hanya menunjukkan alurnya (Tier B).",
            "",
            f"- AUC pada label panggilan: `pola-v1` {fixed(auc_v1)}, `pola-v2` {fixed(auc_v2)} "
            "(dinilai pada data yang sama dengan yang dipakai melatih v2, jadi bukan ukuran kinerja)."
            if not math.isnan(auc_v1)
            else "- AUC pada label panggilan tidak dihitung: label hanya berisi satu kelas.",
            f"- AUC `pola-v2` terhadap kunci kebenaran demo: {fixed(demo_eval['auc_skor'])}.",
            f"- Ambang `pola-v2`: {fixed(model_v2['ambang_tinggi'])}.",
            "- `pola-v1` tetap bawaan. Backend memakai versi yang tertulis di `pengaturan.versi_pola`.",
            "",
        ]
    )


def train_with_labels(path: Path, binned, y, features, histogram, demo, model_v1) -> None:
    from sklearn.metrics import roc_auc_score

    labels = read_json(path)["baris"]
    if not labels:
        raise SystemExit("Berkas label tidak berisi panggilan Sesuai atau Tidak sesuai.")
    label_bins = [{f: r[f] for f in pola.FITUR} for r in labels]
    label_y = [int(r["label"]) for r in labels]
    weights = [1.0] * len(y) + [LABEL_WEIGHT] * len(label_y)
    model_v2 = model_json(
        train(binned + label_bins, y + label_y, features, weights), features, "pola-v2"
    )
    model_v2["ambang_tinggi"], _ = threshold_and_rate(model_v2, histogram)
    model_v2["label_panggilan"] = len(labels)
    write_json(OUTPUT / "model-pola-v2.json", model_v2)

    raw = [{f: int(b[f].rstrip("+")) for f in pola.FITUR} for b in label_bins]
    one_class = len(set(label_y)) < 2
    auc_v1 = (
        math.nan
        if one_class
        else float(roc_auc_score(label_y, [pola.skor(model_v1, r) for r in raw]))
    )
    auc_v2 = (
        math.nan
        if one_class
        else float(roc_auc_score(label_y, [pola.skor(model_v2, r) for r in raw]))
    )
    report = OUTPUT / "EVALUASI.md"
    previous = report.read_text(encoding="utf-8").split("## Dengan label panggilan")[0].rstrip("\n")
    section = label_section(
        model_v2, len(labels), sum(label_y), auc_v1, auc_v2, evaluate_demo(model_v2, demo)
    )
    report.write_text(f"{previous}\n\n{section}", encoding="utf-8")
    logger.info(
        "model-pola-v2.json written from {} call labels ({} Tidak sesuai)",
        len(labels),
        sum(label_y),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--label-panggilan",
        type=Path,
        help="label-panggilan.json from backend/scripts/ekspor_label_pola.py",
    )
    args = parser.parse_args()

    marginal = read_json(REFERENCE / "marginal.json")
    histogram = read_histogram(marginal["marginal"])
    combinations = read_json(REFERENCE / "kombinasi.json")
    benchmarks = read_json(REFERENCE / "pembanding_tipe.json")
    manifest = read_json(REFERENCE / "manifest.json")
    demo = demo_features()

    fit = feature_fit(demo, marginal["marginal"])
    features = [k["fitur"] for k in fit if not k["dibuang"]]
    for k in fit:
        logger.info(
            "Feature fit {}: demo {:.4f} vs national {:.4f}{}",
            k["fitur"],
            k["demo"],
            k["nasional"],
            " -> DROPPED" if k["dibuang"] else "",
        )

    raw, y = training_samples(histogram)
    binned = [pola.bin_fitur(f) for f in raw]
    synthetic_auc = held_out_auc(binned, y, features)
    model = model_json(train(binned, y, features), features, "pola-v1")
    model["ambang_tinggi"], rate = threshold_and_rate(model, histogram)
    model = {k: model[k] for k in MODEL_KEYS}

    reference = {
        "sumber": "Data Sampel BPJS Kesehatan 2024 (FKRTL reguler, fisioterapi rawat jalan), agregat",
        "tahun": 2024,
        "marginal": marginal["marginal"],
        "digabung": marginal["digabung"],
        "kombinasi": combinations["kombinasi"],
        "pembanding_tipe": {t: benchmarks[t] for t in [NATIONAL, *HOSPITAL_TYPES.values()]},
        "peta_tipe": HOSPITAL_TYPES,
    }
    demo_eval = evaluate_demo(model, demo)

    OUTPUT.mkdir(exist_ok=True)
    write_json(OUTPUT / "model-pola-v1.json", model)
    write_json(OUTPUT / "referensi.json", reference)
    write_json(OUTPUT / "skor_demo.json", demo_scores(model, reference, demo))
    sunday_share = 1 - marginal["marginal"]["ahad_libur"]["0"]
    (OUTPUT / "EVALUASI.md").write_text(
        evaluation_report(
            model,
            fit,
            synthetic_auc,
            rate,
            mean_score_per_combination(model, histogram),
            demo_eval,
            manifest,
            sunday_share,
        ),
        encoding="utf-8",
    )
    logger.info(
        "Synthetic AUC {:.3f} | threshold {} | national rate {:.2%}",
        synthetic_auc,
        model["ambang_tinggi"],
        rate,
    )
    logger.info("Demo: {}", demo_eval)

    if args.label_panggilan:
        train_with_labels(args.label_panggilan, binned, y, features, histogram, demo, model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
