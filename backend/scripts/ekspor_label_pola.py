"""Mengekspor hasil panggilan sebagai label untuk melatih ulang skor pola.

Satu baris per panggilan selesai berlabel Sesuai atau Tidak sesuai: fitur yang sudah dibin (tools/pola.py)
dan label (1 = Tidak sesuai). Tanpa nama, nomor, id peserta, id panggilan, atau id RS. Baris diurutkan menurut
nilainya, bukan menurut waktu atau pasien.

Pakai:  .venv/bin/python -m scripts.ekspor_label_pola [--output berkas.json]
Bawaan: backend/uploads/label-panggilan.json (folder uploads tidak di-commit).
Lanjut: cd ai-service && uv run --group data python scripts/train_pattern_model.py --label-panggilan <berkas>
"""
import argparse
import json
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app import config, pola_v3

LABEL = {"Sesuai": 0, "Tidak sesuai": 1}


def susun_label(conn) -> list[dict]:
    """conn memakai baris dict. Fitur dihitung ulang dari klaim_sesi, sama seperti seed."""
    pola = pola_v3.pola()
    libur = {r["tanggal"] for r in conn.execute("select tanggal from libur_nasional")}
    panggilan = conn.execute(
        "select id_peserta, id_rs, bulan_layanan, label from panggilan"
        " where status = 'selesai' and label = any(%s)",
        (list(LABEL),),
    ).fetchall()
    baris = []
    for p in panggilan:
        sesi = [(None, r["tanggal"]) for r in conn.execute(
            "select tanggal from klaim_sesi where id_peserta = %s and id_rs = %s", (p["id_peserta"], p["id_rs"])
        )]
        fitur = pola.fitur_per_pasien(sesi, p["bulan_layanan"], libur)[None]
        baris.append({**pola.bin_fitur(fitur), "label": LABEL[p["label"]]})
    return sorted(baris, key=lambda b: [pola.BIN[f].index(b[f]) for f in pola.FITUR] + [b["label"]])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=config.upload_dir() / "label-panggilan.json")
    arg = ap.parse_args()
    url = config.database_url()
    if not url:
        print("DATABASE_URL kosong. Isi backend/.env dulu.")
        return 1
    with psycopg.connect(url, prepare_threshold=None, connect_timeout=10, row_factory=dict_row) as conn:
        baris = susun_label(conn)
    arg.output.parent.mkdir(parents=True, exist_ok=True)
    isi = {"keterangan": "Label hasil panggilan untuk skor pola: fitur dibin, 1 = Tidak sesuai. Tanpa identitas.",
           "fitur": list(pola_v3.pola().FITUR), "baris": baris}
    arg.output.write_text(json.dumps(isi, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(baris)} label ditulis ke {arg.output} ({sum(b['label'] for b in baris)} Tidak sesuai)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
