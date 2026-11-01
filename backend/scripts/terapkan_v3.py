"""Menerapkan skema v3 (db/schema_v3.sql) ke database, lalu mengisinya lewat scripts.seed_v3.

Skema dijalankan dalam satu transaksi dan idempoten, jadi aman diulang. Tabel v2 tidak disentuh.

Pakai:  .venv/bin/python -m scripts.terapkan_v3 [--reset] [--skema-saja] [--dry-run]
  --reset       kosongkan tabel v3 sebelum seed (keadaan awal demo: 4 Selesai, 26 Antre)
  --skema-saja  terapkan skema tanpa seed
  --dry-run     hitung data seed saja, tanpa menulis ke database
Syarat: DATABASE_URL di backend/.env terisi.
"""
import argparse
import sys
from pathlib import Path

import psycopg

from scripts import seed_v3

SKEMA = Path(__file__).resolve().parents[1] / "db" / "schema_v3.sql"


def terapkan_skema(url):
    """Jalankan schema_v3.sql dalam satu transaksi; gagal di tengah berarti tidak ada yang berubah."""
    with psycopg.connect(url, prepare_threshold=None, connect_timeout=10) as conn:
        conn.execute(SKEMA.read_text(encoding="utf-8"))
        conn.commit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="kosongkan tabel v3 sebelum seed")
    ap.add_argument("--skema-saja", action="store_true", help="terapkan skema tanpa seed")
    ap.add_argument("--dry-run", action="store_true", help="hitung data seed saja, tanpa menulis ke database")
    arg = ap.parse_args()

    if arg.dry_run:
        d = seed_v3.muat_data()
        print(f"Dry-run: skema {SKEMA.name} tidak diterapkan. Seed: antre baru {len(d['antre'])}, riwayat {len(d['riwayat'])}.")
        return 0

    from app.config import database_url

    url = database_url()
    if not url:
        print("DATABASE_URL kosong. Isi backend/.env dulu.")
        return 1
    try:
        terapkan_skema(url)
        print(f"Skema {SKEMA.name} diterapkan.")
        if not arg.skema_saja:
            seed_v3.isi_database(url, seed_v3.muat_data(), reset=arg.reset)
            print("Seed v3 selesai." + (" (dengan reset)" if arg.reset else ""))
    except psycopg.OperationalError:
        print(seed_v3.PESAN_KONEKSI)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
