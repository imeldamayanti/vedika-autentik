"""Memeriksa isi database v3 setelah scripts.terapkan_v3 --reset. Hanya membaca, tidak menulis.

Pakai:  .venv/bin/python -m scripts.cek_v3
Keluaran: LULUS atau GAGAL per butir. Kode keluar 1 jika ada yang GAGAL.
"""
import json
import sys

import psycopg
from psycopg.rows import dict_row

from scripts.seed_v3 import BULAN, DATA, PESAN_KONEKSI, muat_aturan

TIDAK_DITELEPON = {"S7"}  # I3 saja, tidak terpicu


def hitung(conn, sql, *param):
    return conn.execute(sql, param).fetchone()["n"]


def periksa_jumlah(conn):
    harapan = [
        ("5 rumah sakit", hitung(conn, "select count(*) as n from rumah_sakit"), 5),
        ("408 peserta", hitung(conn, "select count(*) as n from peserta"), 408),
        ("4.913 klaim sesi", hitung(conn, "select count(*) as n from klaim_sesi"), 4913),
        ("300 indikator Agustus", hitung(conn, "select count(*) as n from indikator_bulanan where bulan = %s", BULAN), 300),
        ("30 pasien dipicu", hitung(conn, "select count(*) as n from indikator_bulanan where bulan = %s and dipicu", BULAN), 30),
        ("30 baris panggilan", hitung(conn, "select count(*) as n from panggilan"), 30),
        ("4 panggilan selesai", hitung(conn, "select count(*) as n from panggilan where status = 'selesai'"), 4),
        ("26 panggilan antre", hitung(conn, "select count(*) as n from panggilan where status = 'antre'"), 26),
    ]
    return [(nama, ada == mau, f"ada {ada}") for nama, ada, mau in harapan]


def periksa_skenario(conn):
    """S7 tidak ditelepon; S1-S6 dan S8 berstatus antre dengan penerima sesuai R1.3."""
    skenario = json.loads((DATA / "skenario_uji.json").read_text(encoding="utf-8"))
    baris = {
        r["id_peserta"]: r
        for r in conn.execute("select id_peserta, status, penerima from panggilan where id_peserta like 'P-S%'")
    }
    hasil = []
    for s in skenario:
        sid, pid = s["id_skenario"], s["id_peserta"]
        r = baris.get(pid)
        if sid in TIDAK_DITELEPON:
            hasil.append((f"{sid} tidak ada di panggilan", r is None, "ada baris" if r else "tidak ada"))
            continue
        penerima = "peserta" if s["penerima_telepon"]["hubungan"] == "peserta" else "keluarga"
        ok = r is not None and r["status"] == "antre" and r["penerima"] == penerima
        hasil.append((f"{sid} antre, penerima {penerima}", ok, f"{r['status']}/{r['penerima']}" if r else "tidak ada"))
    return hasil


def periksa_ringkasan(conn):
    """Ringkasan RS awal (aturan.py dari isi DB) dan persen dipicu per RS sama dengan expected_ringkasan_rs.json."""
    harapan = json.loads((DATA / "expected_ringkasan_rs.json").read_text(encoding="utf-8"))
    aturan = muat_aturan()
    selesai = conn.execute("select id_rs, label from panggilan where status = 'selesai' and label is not null").fetchall()
    ringkasan = aturan.ringkasan_rs(selesai)
    hasil = [("ringkasan RS awal = expected sebelum_skenario", ringkasan == harapan["sebelum_skenario"], "")]
    melati = ringkasan.get("RS01", {})
    hasil.append((
        "RS Melati Normal, 2 tidak sesuai dari 4 terjawab",
        (melati.get("status"), melati.get("tidak_sesuai"), melati.get("terjawab")) == ("Normal", 2, 4),
        f"{melati.get('status')} {melati.get('tidak_sesuai')}/{melati.get('terjawab')}",
    ))
    pemicu = {
        r["id_rs"]: {
            "id_rs": r["id_rs"], "pasien_aktif": r["aktif"], "pasien_dipicu": r["dipicu"],
            "persen_dipicu": round(100 * r["dipicu"] / r["aktif"], 1),
        }
        for r in conn.execute(
            "select id_rs, count(*) as aktif, count(*) filter (where dipicu) as dipicu"
            " from indikator_bulanan where bulan = %s group by id_rs",
            (BULAN,),
        )
    }
    hasil.append(("persen dipicu per RS = expected", pemicu == harapan[f"pemicu_per_rs_{BULAN}"], ""))
    return hasil


def main() -> int:
    from app.config import database_url

    url = database_url()
    if not url:
        print("DATABASE_URL kosong. Isi backend/.env dulu.")
        return 1
    try:
        with psycopg.connect(url, row_factory=dict_row, prepare_threshold=None, connect_timeout=10) as conn:
            conn.read_only = True
            hasil = periksa_jumlah(conn) + periksa_skenario(conn) + periksa_ringkasan(conn)
    except psycopg.OperationalError:
        print(PESAN_KONEKSI)
        return 1
    except psycopg.errors.UndefinedTable:
        print("Tabel v3 belum ada. Jalankan scripts.terapkan_v3 dulu.")
        return 1
    for nama, lulus, detail in hasil:
        print(f"{'LULUS' if lulus else 'GAGAL'}  {nama}" + (f" ({detail})" if detail and not lulus else ""))
    gagal = sum(not lulus for _, lulus, _ in hasil)
    print(f"{len(hasil) - gagal} lulus, {gagal} gagal")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
