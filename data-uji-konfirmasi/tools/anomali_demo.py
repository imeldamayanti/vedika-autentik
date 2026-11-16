"""Hasil model anomali untuk data demo, disalin ke data-v3.js (seperti skor_demo.json untuk skor pola).

Data demo tidak punya kolom rujukan. Pasien demo yang ada dianggap berujukan FKTP dari kab/kota yang sama.
Dua pasien tambahan (P-M1, P-M2) dibuat khusus untuk simulasi: tidak terpicu aturan, tetapi semua kunjungannya
tanpa rujukan FKTP dan dirujuk dari kab/kota lain, sehingga hanya model yang menandainya. Keduanya hanya ada di
simulasi web, tidak di database demo.

Pakai: python3 data-uji-konfirmasi/tools/anomali_demo.py  → referensi-pola/anomali_demo.json
"""
import json
from pathlib import Path

import anomali
import pola

REF = Path(__file__).resolve().parents[1] / "referensi-pola"
NORMAL = {"tanpa_rujukan": 0.0, "lintas_wilayah": 0.0}
JANGGAL = {"tanpa_rujukan": 1.0, "lintas_wilayah": 1.0}
TAMBAHAN = {
    "P-M1": {"sesi": 6, "maks_minggu": 2, "ahad_libur": 0, "episode": 7},
    "P-M2": {"sesi": 6, "maks_minggu": 3, "ahad_libur": 0, "episode": 2},
}


def hasil(model, fitur_pola, rujukan):
    f = dict(fitur_pola, **rujukan)
    n = anomali.nilai(model, f)
    a = anomali.alasan(model, f)
    dipicu = sum(pola.indikator(fitur_pola)) >= 2
    dipilih = "keduanya" if dipicu and n["ditandai"] else "aturan" if dipicu else "model" if n["ditandai"] else None
    return {
        "dipilih": dipilih,
        "rujukan": rujukan,
        "anomali": {
            "skor": n["skor"], "ditandai": n["ditandai"], "langka": n["langka"],
            "alasan": [x["teks"] for x in a["alasan"]], "gabungan": a["gabungan"],
        },
    }


def main():
    model = json.loads((REF / "model-anomali-v1.json").read_text(encoding="utf-8"))
    demo = json.loads((REF / "skor_demo.json").read_text(encoding="utf-8"))
    pasien = {d["id_peserta"]: hasil(model, d["fitur"], NORMAL) for d in demo}
    pasien.update({pid: hasil(model, f, JANGGAL) | {"fitur": f} for pid, f in TAMBAHAN.items()})
    ringkas = {
        k: sum(1 for p in pasien.values() if p["dipilih"] == k) for k in ("keduanya", "aturan", "model")
    }
    keluar = {
        "versi": model["versi"],
        "asumsi": "Pasien demo dianggap berujukan FKTP dari kab/kota yang sama; P-M1 dan P-M2 tanpa rujukan dan lintas kab/kota.",
        "ringkas": ringkas,
        "pasien": pasien,
    }
    (REF / "anomali_demo.json").write_text(json.dumps(keluar, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(ringkas)


if __name__ == "__main__":
    main()
