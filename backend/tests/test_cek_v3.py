"""Seed v3 lalu cek_v3 di schema sementara `uji` (fixture conn, di-rollback): semua butir harus LULUS."""
from pathlib import Path

from scripts import cek_v3, seed_v3

AKAR = Path(__file__).resolve().parents[2]
SKEMA_V3 = (AKAR / "backend" / "db" / "schema_v3.sql").read_text().replace("public.", "uji.")


def semua_butir(conn):
    return cek_v3.periksa_jumlah(conn) + cek_v3.periksa_skenario(conn) + cek_v3.periksa_ringkasan(conn)


def test_seed_lalu_cek_semua_lulus(conn):
    conn.execute(SKEMA_V3)
    seed_v3.isi_ke(conn, seed_v3.muat_data())
    gagal = [(n, d) for n, lulus, d in semua_butir(conn) if not lulus]
    assert gagal == []


def test_reset_mengembalikan_keadaan_awal(conn):
    conn.execute(SKEMA_V3)
    d = seed_v3.muat_data()
    seed_v3.isi_ke(conn, d)
    conn.execute("update uji.panggilan set status = 'selesai', label = 'Tidak sesuai' where id = 'CALL-P-S1-2026-08'")
    conn.execute("insert into uji.panggilan_log (panggilan_id, status) values ('CALL-P-S1-2026-08', 'menelepon')")
    seed_v3.isi_ke(conn, d, reset=True)
    assert conn.execute("select count(*) as n from uji.panggilan_log").fetchone()["n"] == 0
    assert [n for n, lulus, _ in semua_butir(conn) if not lulus] == []
