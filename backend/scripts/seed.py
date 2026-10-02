"""Mengisi antrean demo lewat API (jalur yang sama dengan unggahan nyata).

12 berkas awal diunggah urut supaya berkas asal masuk sebelum kembarannya. Lima berkas demo
(VA-ASL-01, KMB-01, DST-01, AI-01, BRM-01) sengaja tidak ikut: juri yang mengunggahnya.

Pakai:  .venv/bin/python -m scripts.seed [--api http://localhost:8000]
Syarat: API, worker, dan mesin sudah berjalan.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx

AKAR = Path(__file__).resolve().parents[2]
URUTAN = [
    "VA-KMB-00", "VA-ASL-02", "VA-ASL-03", "VA-ASL-04", "VA-KMB-03", "VA-DST-02",
    "VA-DST-03", "VA-AI-02", "VA-AI-03", "VA-BRM-02", "VA-BRM-03", "VA-KMB-02",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--tunggu", type=float, default=60.0, help="detik maksimal menunggu tiap berkas")
    arg = ap.parse_args()

    manifest = {b["id"]: b for b in json.loads((AKAR / "dataset" / "manifest.json").read_text())}
    klien = httpx.Client(base_url=arg.api, timeout=30)
    gagal = 0
    for id_ in URUTAN:
        b = manifest[id_]
        pdf = AKAR / "dataset" / b["folder"] / b["berkas"]["pdf"]
        r = klien.post(
            "/api/v1/berkas",
            files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")},
            data={"kode_faskes": b["klaim"]["kode_faskes"]},
        )
        if r.status_code != 202:
            print(f"{id_}: unggah gagal {r.status_code} {r.text}")
            gagal += 1
            continue
        berkas_id = r.json()["id"]
        batas = time.time() + arg.tunggu
        d = {"status": "diproses"}
        while d["status"] == "diproses" and time.time() < batas:
            time.sleep(0.5)
            d = klien.get(f"/api/v1/berkas/{berkas_id}").json()
        harapan = b["label_diharapkan"]
        nama = {"prioritas": "Prioritas", "cek": "Perlu dicek", "ulang": "Scan ulang", "lolos": "Lolos"}.get(d.get("label"), d["status"])
        cocok = "OK " if nama == harapan else "BEDA"
        gagal += nama != harapan
        print(f"{cocok} {id_:10} {berkas_id}  hasil={nama:12} harapan={harapan}")
    print(f"selesai, {gagal} berkas tidak sesuai harapan")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
