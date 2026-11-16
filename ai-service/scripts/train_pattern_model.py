#!/usr/bin/env python3
"""Train the pattern score ("Skor pola") by knowledge-guided weak supervision.

Normal class: patient-months drawn from the committed national histogram. Violation class:
the same draws after rule-guided manipulations. Reads committed aggregates only, never raw data.
Run with `uv run --group data python scripts/train_pattern_model.py`.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from loguru import logger

from vedika_ai.pola_reference import histogram_levels, load_pola, weighted_percentile

AKAR = Path(__file__).resolve().parents[2]
REFERENSI = AKAR / "ai-service" / "data" / "reference" / "pola-2024"
DATA_UJI = AKAR / "data-uji-konfirmasi"
KELUAR = DATA_UJI / "referensi-pola"
BULAN_DEMO = "2026-08"
RS_JUJUR = ("RS02", "RS03", "RS04", "RS05")
BENIH = 2026
N_KELAS = 50_000
PERSENTIL_TINGGI = 0.985
BOBOT_LABEL = 5.0
BATAS_BEDA_FITUR = 3.0
PETA_TIPE = {
    "Pemerintah kelas B": "RS Kelas B",
    "Pemerintah kelas C": "RS Kelas C",
    "Swasta setara kelas B": "RS Swasta Setara Type B",
    "Swasta setara kelas C": "RS Swasta Setara Type C",
}
NASIONAL = "Nasional"
pola = load_pola()


def baca_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def tulis_json(path: Path, nilai) -> None:
    path.write_text(json.dumps(nilai, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def baca_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def angka(x: float, desimal: int = 3) -> str:
    return f"{x:.{desimal}f}".replace(".", ",")


def ribuan(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def pecah_sel(r: dict, tingkat: list[dict], marginal: dict) -> list[dict]:
    """Satu sel histogram menjadi sel bin halus. Sel kasar (tingkat > 0) dibagi menurut marginal nasional
    di dalam rentangnya, dengan anggapan fitur saling bebas di dalam sel itu. Bin teratas memakai batas bawahnya."""
    pilihan = []
    for f in pola.FITUR:
        anggota = tingkat[int(r["tingkat"])][f][r[f]]
        p = {b: marginal[f].get(b, 0.0) for b in anggota}
        total = sum(p.values())
        pilihan.append([(b, p[b] / total) for b in anggota if p[b] > 0] if total else [(anggota[0], 1.0)])
    hasil = [({}, float(r["bobot"]))]
    for f, opsi in zip(pola.FITUR, pilihan, strict=True):
        hasil = [({**fitur, f: int(b.rstrip("+"))}, w * bagian) for fitur, w in hasil for b, bagian in opsi]
    return [{**fitur, "tingkat": int(r["tingkat"]), "bobot": w} for fitur, w in hasil]


def baca_histogram(marginal: dict) -> list[dict]:
    """Histogram nasional sebagai sel fitur mentah berbobot; sel kasar dipecah ke bin halus."""
    tingkat = histogram_levels()
    return [x for r in baca_csv(REFERENSI / "histogram.csv") for x in pecah_sel(r, tingkat, marginal)]


def manipulasi(fitur: dict, rng: random.Random) -> dict:
    """1-2 manipulasi acak yang meniru penyisipan di tools/generate.py dan aturan I1-I4."""
    f = dict(fitur)

    def v1():
        f["sesi"] += rng.randint(2, 6)
        f["maks_minggu"] = max(f["maks_minggu"], math.ceil(f["sesi"] / 4) + rng.randint(0, 1))

    def v2():
        f["ahad_libur"] += rng.randint(1, 2)
        f["sesi"] += 1

    def v3():
        f["maks_minggu"] = max(f["maks_minggu"], rng.randint(3, 5))
        f["sesi"] = max(f["sesi"], f["maks_minggu"])

    def v4():
        f["episode"] = min(pola.EPISODE_MAKS, f["episode"] + rng.randint(3, 6))

    # V4 (perpanjangan episode) hanya muncul bersama manipulasi lain
    pilihan = rng.sample([v1, v2, v3, v4], 2) if rng.randint(1, 2) == 2 else [rng.choice([v1, v2, v3])]
    for ubah in pilihan:
        ubah()
    return f


def sampel_latih(histogram: list[dict]) -> tuple[list[dict], list[int]]:
    rng = random.Random(BENIH)
    bobot = [r["bobot"] for r in histogram]
    normal = [{f: r[f] for f in pola.FITUR} for r in rng.choices(histogram, bobot, k=N_KELAS)]
    asal = rng.choices(histogram, bobot, k=N_KELAS)
    pelanggaran = [manipulasi({f: r[f] for f in pola.FITUR}, rng) for r in asal]
    return normal + pelanggaran, [0] * N_KELAS + [1] * N_KELAS


def kolom(fitur_model: list[str]) -> list[tuple[str, str]]:
    return [(f, b) for f in fitur_model for b in pola.BIN[f]]


def satu_panas(baris_bin: list[dict], fitur_model: list[str]):
    import numpy

    indeks = {k: n for n, k in enumerate(kolom(fitur_model))}
    x = numpy.zeros((len(baris_bin), len(indeks)), dtype="float64")
    for n, b in enumerate(baris_bin):
        for f in fitur_model:
            x[n, indeks[(f, b[f])]] = 1.0
    return x


def latih(baris_bin: list[dict], y: list[int], fitur_model: list[str], bobot=None):
    from sklearn.linear_model import LogisticRegression

    model = LogisticRegression(C=1.0, max_iter=1000, random_state=BENIH)
    model.fit(satu_panas(baris_bin, fitur_model), y, sample_weight=bobot)
    return model


def auc_tahan(baris_bin: list[dict], y: list[int], fitur_model: list[str], bobot=None) -> float:
    """AUC pada 20% data yang tidak dipakai melatih."""
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split

    idx_latih, idx_uji = train_test_split(
        list(range(len(y))), test_size=0.2, random_state=BENIH, stratify=y
    )
    model = latih(
        [baris_bin[i] for i in idx_latih], [y[i] for i in idx_latih], fitur_model,
        None if bobot is None else [bobot[i] for i in idx_latih],
    )
    peluang = model.predict_proba(satu_panas([baris_bin[i] for i in idx_uji], fitur_model))[:, 1]
    return float(roc_auc_score([y[i] for i in idx_uji], peluang))


def model_json(model, fitur_model: list[str], versi: str) -> dict:
    koef = dict(zip(kolom(fitur_model), model.coef_[0], strict=True))
    return {
        "versi": versi,
        "fitur": fitur_model,
        "bin": {f: pola.BIN[f] for f in fitur_model},
        "intersep": round(float(model.intercept_[0]), 4),
        "koefisien": {
            f: {b: round(float(koef[(f, b)]), 4) for b in pola.BIN[f]} for f in fitur_model
        },
        "dilatih_dari": "ai-service/data/reference/pola-2024",
        "tanggal": date.today().isoformat(),
    }


def fitur_demo() -> dict[tuple[str, str], dict]:
    """(id_peserta, id_rs) -> fitur mentah Agustus 2026 dari klaim_sesi.csv."""
    libur = {date.fromisoformat(r["tanggal"]) for r in baca_csv(DATA_UJI / "libur_nasional_2026.csv")}
    tanggal = defaultdict(list)
    for r in baca_csv(DATA_UJI / "klaim_sesi.csv"):
        tanggal[(r["id_peserta"], r["id_rs"])].append(date.fromisoformat(r["tanggal"]))
    hasil = {}
    for kunci, tgl in sorted(tanggal.items()):
        bulan_ini = [t for t in tgl if t.strftime("%Y-%m") == BULAN_DEMO]
        if bulan_ini:
            aktif = {t.strftime("%Y-%m") for t in tgl}
            hasil[kunci] = pola.fitur_bulan(bulan_ini, aktif, BULAN_DEMO, libur)
    return hasil


def cek_kecocokan_fitur(demo: dict, marginal: dict) -> list[dict]:
    """Bin teratas tiap fitur: pangsa pasien demo jujur (RS02-RS05) dibanding pangsa nasional."""
    jujur = [f for (_, rs), f in demo.items() if rs in RS_JUJUR]
    hasil = []
    for f in pola.FITUR:
        teratas = [b for b in pola.BIN[f] if b in marginal[f]][-1]
        batas = pola.BIN[f].index(teratas)
        n_demo = sum(pola.BIN[f].index(pola.bin_nilai(f, x[f])) >= batas for x in jujur)
        pangsa_demo = n_demo / len(jujur)
        pangsa_nasional = marginal[f][teratas]
        hasil.append({
            "fitur": f, "bin": teratas, "demo": pangsa_demo, "nasional": pangsa_nasional,
            "dibuang": pangsa_demo > BATAS_BEDA_FITUR * pangsa_nasional,
        })
    return hasil


def ambang_dan_tingkat(model: dict, histogram: list[dict]) -> tuple[float, float]:
    skor_sel = [(pola.skor(model, r), r["bobot"]) for r in histogram]
    ambang = weighted_percentile(skor_sel, PERSENTIL_TINGGI)
    total = sum(w for _, w in skor_sel)
    return ambang, sum(w for s, w in skor_sel if s >= ambang) / total


def evaluasi_demo(model: dict, demo: dict) -> dict:
    """Tier B: skor terhadap kunci_kebenaran (hanya di sini; backend dan seed tidak pernah membacanya)."""
    from sklearn.metrics import roc_auc_score

    kunci = {
        (r["id_peserta"], r["id_rs"]): int(r["sesi_ditagih"]) - int(r["sesi_sebenarnya"]) > 2
        for r in baca_csv(DATA_UJI / f"kunci_kebenaran_{BULAN_DEMO}.csv")
    }
    baris = sorted(demo)
    y = [int(kunci[k]) for k in baris]
    skor = [pola.skor(model, demo[k]) for k in baris]
    jumlah = [sum(pola.indikator(demo[k])) for k in baris]
    dipicu = [j >= 2 for j in jumlah]
    tinggi = [s >= model["ambang_tinggi"] for s in skor]
    n_dipicu = sum(dipicu)
    teratas = sorted(range(len(baris)), key=lambda i: (-skor[i], baris[i]))[:n_dipicu]
    return {
        "bulan_pasien": len(baris),
        "digelembungkan": sum(y),
        "auc_skor": float(roc_auc_score(y, skor)),
        "auc_jumlah_indikator": float(roc_auc_score(y, jumlah)),
        "dipicu": n_dipicu,
        "presisi_aturan": sum(a and b for a, b in zip(dipicu, y, strict=True)) / n_dipicu,
        "recall_aturan": sum(a and b for a, b in zip(dipicu, y, strict=True)) / sum(y),
        "presisi_at_n": sum(y[i] for i in teratas) / n_dipicu,
        "tinggi": sum(tinggi),
        "tinggi_digelembungkan": sum(a and b for a, b in zip(tinggi, y, strict=True)),
        "lolos_aturan": sum(b and not a for a, b in zip(dipicu, y, strict=True)),
        "lolos_aturan_tapi_tinggi": sum(
            b and not a and t for a, b, t in zip(dipicu, y, tinggi, strict=True)
        ),
    }


def skor_per_kombinasi(model: dict, histogram: list[dict]) -> list[tuple[str, float, float]]:
    """Tier A: rata-rata skor berbobot per kombinasi aturan, atas sel histogram yang tidak tersembunyi."""
    jumlah, bobot = Counter(), Counter()
    for r in histogram:
        kunci = pola.kombinasi(*pola.indikator(r))
        jumlah[kunci] += pola.skor(model, r) * r["bobot"]
        bobot[kunci] += r["bobot"]
    total = sum(bobot.values())
    return [(k, jumlah[k] / bobot[k], bobot[k] / total) for k in sorted(bobot)]


def skor_demo(model: dict, referensi: dict, demo: dict) -> list[dict]:
    hasil = []
    for (id_peserta, id_rs), f in sorted(demo.items()):
        s = pola.skor(model, f)
        hasil.append({
            "id_peserta": id_peserta, "id_rs": id_rs, "bulan": BULAN_DEMO, "fitur": f, "skor": s,
            "tinggi": s >= model["ambang_tinggi"], "alasan": pola.alasan(model, referensi, f),
        })
    return hasil


def tulis_evaluasi(model, kecocokan, auc_sintetis, tingkat, per_kombinasi, demo_ev, manifest, punya_minggu) -> str:
    buang = [k["fitur"] for k in kecocokan if k["dibuang"]]
    tersembunyi = manifest["suppression"]["histogram"]["weight_share_suppressed"]
    baris = [
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
        f"nasional 2024 (Tier A). Fitur dibuang bila pangsa demo lebih dari {BATAS_BEDA_FITUR:g} kali nasional.",
        "",
        "| Fitur | Bin teratas | Demo jujur | Nasional | Keputusan |",
        "|---|---|---|---|---|",
        *[
            f"| `{k['fitur']}` | {k['bin']} | {angka(100 * k['demo'], 2)}% | "
            f"{angka(100 * k['nasional'], 2)}% | {'dibuang' if k['dibuang'] else 'dipakai'} |"
            for k in kecocokan
        ],
        "",
        f"Fitur yang dibuang: {', '.join(buang) if buang else 'tidak ada'}. "
        f"Fitur model: {', '.join(model['fitur'])}.",
        "",
        "## Tier B (sintetis, hanya uji kewajaran metode)",
        "",
        f"- AUC normal vs pelanggaran buatan pada 20% data tahan: **{angka(auc_sintetis)}** "
        f"({ribuan(N_KELAS)} + {ribuan(N_KELAS)} sampel).",
        "- Kelas pelanggaran dibuat dari aturan yang sama dengan yang diuji, jadi angka ini hanya "
        "menunjukkan model mempelajari manipulasi tersebut. Ini bukan akurasi deteksi.",
        "",
        "## Tier A (agregat nasional 2024)",
        "",
        f"- Ambang `ambang_tinggi` = **{angka(model['ambang_tinggi'])}** (persentil berbobot "
        f"{angka(100 * PERSENTIL_TINGGI, 1)} skor atas histogram nasional).",
        f"- Pangsa bulan-pasien nasional dengan skor ≥ ambang: **{angka(100 * tingkat, 2)}%**.",
        f"- Histogram bertingkat: sel di bawah 10 baris digabung ke rentang yang lebih kasar (batas rentang tepat di "
        f"ambang aturan), dan hanya sisa yang tetap di bawah 10 baris di tingkat terkasar yang disembunyikan "
        f"({angka(100 * tersembunyi, 2)}% bobot). Bulan-pasien dengan sesi hari Minggu ({angka(100 * punya_minggu, 2)}% "
        f"nasional) ikut masuk kelas normal lewat sel kasar. Pangsa nasional sebenarnya di antara kira-kira "
        f"{angka(100 * tingkat * (1 - tersembunyi), 1)}% dan {angka(100 * (tingkat * (1 - tersembunyi) + tersembunyi), 1)}%.",
        "",
        "Rata-rata skor per kombinasi aturan (sel histogram yang tidak tersembunyi):",
        "",
        "| Kombinasi | Rata-rata skor | Pangsa bobot |",
        "|---|---|---|",
        *[f"| {k} | {angka(s)} | {angka(100 * p, 2)}% |" for k, s, p in per_kombinasi],
        "",
        "## Tier B (data demo vs `kunci_kebenaran_2026-08.csv`)",
        "",
        f"{demo_ev['bulan_pasien']} bulan-pasien Agustus 2026, {demo_ev['digelembungkan']} di antaranya "
        "digelembungkan (selisih ditagih dan sebenarnya lebih dari 2). Kunci kebenaran hanya dibaca di evaluasi offline ini.",
        "",
        f"- AUC skor pola: **{angka(demo_ev['auc_skor'])}**.",
        f"- AUC `jumlah_indikator` (pembanding): **{angka(demo_ev['auc_jumlah_indikator'])}**.",
        f"- Pemicu aturan (≥ 2 indikator, {demo_ev['dipicu']} bulan-pasien): presisi "
        f"**{angka(demo_ev['presisi_aturan'])}**, recall **{angka(demo_ev['recall_aturan'])}**.",
        f"- Presisi@{demo_ev['dipicu']} skor pola: **{angka(demo_ev['presisi_at_n'])}**.",
        f"- Skor ≥ ambang: {demo_ev['tinggi']} bulan-pasien, {demo_ev['tinggi_digelembungkan']} di "
        "antaranya digelembungkan.",
        f"- Digelembungkan tetapi tidak terpicu aturan: {demo_ev['lolos_aturan']}; di antaranya "
        f"**{demo_ev['lolos_aturan_tapi_tinggi']}** berskor ≥ ambang (tampil sebagai informasi, tidak ditelepon).",
        "",
        "## Koefisien",
        "",
        f"Intersep: {angka(model['intersep'], 4)}. Skor = logistik(intersep + jumlah koefisien bin yang aktif).",
        "",
        "| Fitur | Bin | Koefisien |",
        "|---|---|---|",
        *[
            f"| `{f}` | {b} | {angka(k, 4)} |"
            for f in model["fitur"] for b, k in model["koefisien"][f].items()
        ],
        "",
        "## Batasan",
        "",
        "- Skor berarti \"mirip pola manipulasi yang dikenal, dibanding pola nasional 2024\". "
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
    return "\n".join(baris)


def bagian_label(model_v2: dict, n: int, n_tidak_sesuai: int, auc_v1: float, auc_v2: float, demo_ev: dict) -> str:
    return "\n".join([
        "## Dengan label panggilan (`pola-v2`)",
        "",
        f"Dilatih ulang pada {model_v2['tanggal']} dengan {n} hasil panggilan ({n_tidak_sesuai} Tidak sesuai) "
        f"sebagai sampel berlabel berbobot {BOBOT_LABEL:g}, di atas sampel sintetis yang sama. "
        "Di demo, label ini berasal dari panggilan sintetis, jadi bagian ini hanya menunjukkan alurnya (Tier B).",
        "",
        f"- AUC pada label panggilan: `pola-v1` {angka(auc_v1)}, `pola-v2` {angka(auc_v2)} "
        "(dinilai pada data yang sama dengan yang dipakai melatih v2, jadi bukan ukuran kinerja)."
        if not math.isnan(auc_v1) else
        "- AUC pada label panggilan tidak dihitung: label hanya berisi satu kelas.",
        f"- AUC `pola-v2` terhadap kunci kebenaran demo: {angka(demo_ev['auc_skor'])}.",
        f"- Ambang `pola-v2`: {angka(model_v2['ambang_tinggi'])}.",
        "- `pola-v1` tetap bawaan. Backend memakai versi yang tertulis di `pengaturan.versi_pola`.",
        "",
    ])


def latih_dengan_label(path: Path, baris_bin, y, fitur_model, histogram, demo, model_v1) -> None:
    from sklearn.metrics import roc_auc_score

    label = baca_json(path)["baris"]
    if not label:
        raise SystemExit("Berkas label tidak berisi panggilan Sesuai atau Tidak sesuai.")
    bin_label = [{f: r[f] for f in pola.FITUR} for r in label]
    y_label = [int(r["label"]) for r in label]
    bobot = [1.0] * len(y) + [BOBOT_LABEL] * len(y_label)
    model = latih(baris_bin + bin_label, y + y_label, fitur_model, bobot)
    v2 = model_json(model, fitur_model, "pola-v2")
    v2["ambang_tinggi"], _ = ambang_dan_tingkat(v2, histogram)
    v2["label_panggilan"] = len(label)
    tulis_json(KELUAR / "model-pola-v2.json", v2)

    mentah = [{f: int(b[f].rstrip("+")) for f in pola.FITUR} for b in bin_label]
    satu_kelas = len(set(y_label)) < 2
    auc_v1 = math.nan if satu_kelas else float(roc_auc_score(y_label, [pola.skor(model_v1, m) for m in mentah]))
    auc_v2 = math.nan if satu_kelas else float(roc_auc_score(y_label, [pola.skor(v2, m) for m in mentah]))
    evaluasi = KELUAR / "EVALUASI.md"
    lama = evaluasi.read_text(encoding="utf-8").split("## Dengan label panggilan")[0].rstrip("\n")
    bagian = bagian_label(v2, len(label), sum(y_label), auc_v1, auc_v2, evaluasi_demo(v2, demo))
    evaluasi.write_text(f"{lama}\n\n{bagian}", encoding="utf-8")
    logger.info("model-pola-v2.json ditulis dari {} label panggilan ({} Tidak sesuai)", len(label), sum(y_label))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--label-panggilan", type=Path, help="label-panggilan.json dari backend/scripts/ekspor_label_pola.py")
    arg = ap.parse_args()

    marginal = baca_json(REFERENSI / "marginal.json")
    histogram = baca_histogram(marginal["marginal"])
    kombinasi = baca_json(REFERENSI / "kombinasi.json")
    pembanding = baca_json(REFERENSI / "pembanding_tipe.json")
    manifest = baca_json(REFERENSI / "manifest.json")
    demo = fitur_demo()

    kecocokan = cek_kecocokan_fitur(demo, marginal["marginal"])
    fitur_model = [k["fitur"] for k in kecocokan if not k["dibuang"]]
    for k in kecocokan:
        logger.info("Kecocokan fitur {}: demo {:.4f} vs nasional {:.4f}{}", k["fitur"], k["demo"], k["nasional"],
                    " -> DIBUANG" if k["dibuang"] else "")

    mentah, y = sampel_latih(histogram)
    baris_bin = [pola.bin_fitur(f) for f in mentah]
    auc_sintetis = auc_tahan(baris_bin, y, fitur_model)
    model = model_json(latih(baris_bin, y, fitur_model), fitur_model, "pola-v1")
    model["ambang_tinggi"], tingkat = ambang_dan_tingkat(model, histogram)
    # urutan kunci mengikuti spesifikasi: ambang sebelum asal data
    model = {k: model[k] for k in ("versi", "fitur", "bin", "intersep", "koefisien", "ambang_tinggi", "dilatih_dari", "tanggal")}

    tipe_dipakai = [NASIONAL, *PETA_TIPE.values()]
    referensi = {
        "sumber": "Data Sampel BPJS Kesehatan 2024 (FKRTL reguler, fisioterapi rawat jalan), agregat",
        "tahun": 2024,
        "marginal": marginal["marginal"],
        "digabung": marginal["digabung"],
        "kombinasi": kombinasi["kombinasi"],
        "pembanding_tipe": {t: pembanding[t] for t in tipe_dipakai},
        "peta_tipe": PETA_TIPE,
    }
    demo_ev = evaluasi_demo(model, demo)

    KELUAR.mkdir(exist_ok=True)
    tulis_json(KELUAR / "model-pola-v1.json", model)
    tulis_json(KELUAR / "referensi.json", referensi)
    tulis_json(KELUAR / "skor_demo.json", skor_demo(model, referensi, demo))
    (KELUAR / "EVALUASI.md").write_text(
        tulis_evaluasi(model, kecocokan, auc_sintetis, tingkat, skor_per_kombinasi(model, histogram), demo_ev, manifest,
                       1 - marginal["marginal"]["ahad_libur"]["0"]),
        encoding="utf-8",
    )
    logger.info("AUC sintetis {:.3f} | ambang {} | tingkat nasional {:.2%}", auc_sintetis, model["ambang_tinggi"], tingkat)
    logger.info("Demo: {}", demo_ev)

    if arg.label_panggilan:
        latih_dengan_label(arg.label_panggilan, baris_bin, y, fitur_model, histogram, demo, model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
