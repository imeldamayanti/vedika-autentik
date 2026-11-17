"""anomali-v2 results for the demo data, copied into data-v3.js.

Visit features and referral per visit come from klaim_sesi.csv (`rujukan_fktp`, `perujuk_luar_wilayah`), age from
peserta.csv. Field names in the output are the ones data-v3.js and app-v3.js already read.

    python3 data-uji-konfirmasi/tools/anomali_demo.py  ->  referensi-pola/anomali_demo.json
"""
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import anomali
import pola

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "referensi-pola"
MONTH = "2026-08"


def read_json(name):
    return json.loads((MODELS / name).read_text(encoding="utf-8"))


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def august_claims():
    """(participant, hospital) -> August pattern features, and -> August visits as {referred, other_district}."""
    claims = read_csv("klaim_sesi.csv")
    holidays = {date.fromisoformat(r["tanggal"]) for r in read_csv("libur_nasional_2026.csv")}
    features = pola.features_per_patient(
        [((r["id_peserta"], r["id_rs"]), date.fromisoformat(r["tanggal"])) for r in claims], MONTH, holidays
    )
    visits = defaultdict(list)
    for row in claims:
        if row["tanggal"].startswith(MONTH):
            visits[(row["id_peserta"], row["id_rs"])].append(
                {"referred": row["rujukan_fktp"] == "ya", "other_district": row["perujuk_luar_wilayah"] == "ya"}
            )
    return features, visits


def selection(model, pattern_features, visits, age):
    features = anomali.anomaly_features(pattern_features, visits)
    group = anomali.age_group(age)
    result = anomali.score(model, features, group)
    why = anomali.reasons(model, features, group)
    triggered = sum(pola.indicators(pattern_features)) >= 2
    chosen_by = (
        "keduanya" if triggered and result["flagged"]
        else "aturan" if triggered
        else "model" if result["flagged"]
        else None
    )
    return {
        "dipilih": chosen_by,
        "rujukan": {k: features[k] for k in ("tanpa_rujukan", "lintas_wilayah")},
        "skor": result["score"],
        "ditandai": result["flagged"],
        "langka": result["rare"],
        "alasan": [r["text"] for r in why["rare_bins"]],
        "gabungan": why["pattern"],
    }


def main():
    model = read_json("model-anomali-v2.json")
    ages = {row["id_peserta"]: int(row["umur"]) for row in read_csv("peserta.csv")}
    features, visits = august_claims()
    patients, hospital_rows = {}, defaultdict(list)
    for (participant, hospital), pattern in features.items():
        age = ages[participant]
        patients[participant] = selection(model, pattern, visits[(participant, hospital)], age)
        hospital_rows[hospital].append((anomali.age_group(age), patients[participant]["dipilih"] is not None))

    output = {
        "versi": model["version"],
        "ringkas": {k: sum(p["dipilih"] == k for p in patients.values()) for k in ("keduanya", "aturan", "model")},
        "rs": {rs: anomali.hospital_funnel(model, rows) for rs, rows in sorted(hospital_rows.items())},
        "pasien": patients,
    }
    (MODELS / "anomali_demo.json").write_text(json.dumps(output, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(output["ringkas"], {rs: (f["selected"], f["expected"], f["z"], f["position"]) for rs, f in output["rs"].items()})


if __name__ == "__main__":
    main()
