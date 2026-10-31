"""Uji skema v3: idempoten dan kolom/tabel DB-01 ada.

Berjalan di schema sementara `uji` (fixture conn, di-rollback per tes), bukan di tabel produksi.
"""
from pathlib import Path

import psycopg
import pytest

AKAR = Path(__file__).resolve().parents[2]
SKEMA_V3 = (AKAR / "backend" / "db" / "schema_v3.sql").read_text().replace("public.", "uji.")


def kolom(conn, tabel):
    baris = conn.execute(
        "select column_name from information_schema.columns where table_schema = 'uji' and table_name = %s", (tabel,)
    ).fetchall()
    return {b["column_name"] for b in baris}


def test_skema_v3_bisa_dijalankan_dua_kali(conn):
    conn.execute(SKEMA_V3)
    conn.execute(SKEMA_V3)
    n = conn.execute("select count(*) as n from uji.pengaturan").fetchone()["n"]
    assert n == 5


def test_panggilan_punya_kolom_tambahan(conn):
    conn.execute(SKEMA_V3)
    assert {
        "no_tujuan", "chat_cadangan_terkirim", "jawaban_chat", "galat_pembaca", "klarifikasi_selesai_pada",
    } <= kolom(conn, "panggilan")


def test_panggilan_log_ada_dan_menjaga_status(conn):
    conn.execute(SKEMA_V3)
    assert {"id", "panggilan_id", "status", "waktu", "percobaan", "catatan"} <= kolom(conn, "panggilan_log")
    conn.execute("insert into uji.rumah_sakit (id_rs, nama_rs) values ('RS01', 'RS Uji')")
    conn.execute("insert into uji.peserta (id_peserta, nama) values ('P01', 'Peserta Uji')")
    conn.execute(
        "insert into uji.panggilan (id, id_peserta, id_rs, bulan_layanan, sesi_ditagih, penerima)"
        " values ('C1', 'P01', 'RS01', '2026-08', 10, 'peserta')"
    )
    conn.execute("insert into uji.panggilan_log (panggilan_id, status, percobaan) values ('C1', 'menelepon', 1)")
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("insert into uji.panggilan_log (panggilan_id, status) values ('C1', 'ngawur')")
