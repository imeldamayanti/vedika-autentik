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
    assert n == 6
    jeda = conn.execute("select nilai from uji.pengaturan where kunci = 'jeda'").fetchone()["nilai"]
    assert jeda is False


def test_panggilan_punya_kolom_tambahan(conn):
    conn.execute(SKEMA_V3)
    assert {
        "no_tujuan", "chat_cadangan_terkirim", "jawaban_chat", "galat_pembaca", "klarifikasi_selesai_pada",
    } <= kolom(conn, "panggilan")


def test_kolom_susulan_ditambahkan_ke_tabel_yang_sudah_ada(conn):
    """Database yang sudah menerapkan skema lama harus mendapat coba_lagi_setelah dan prioritas."""
    conn.execute(SKEMA_V3)
    conn.execute("alter table uji.panggilan drop column coba_lagi_setelah, drop column prioritas")
    assert not {"coba_lagi_setelah", "prioritas"} & kolom(conn, "panggilan")
    conn.execute(SKEMA_V3)
    assert {"coba_lagi_setelah", "prioritas"} <= kolom(conn, "panggilan")


def test_prioritas_bawaan_false_dan_tidak_boleh_null(conn):
    conn.execute(SKEMA_V3)
    conn.execute("insert into uji.rumah_sakit (id_rs, nama_rs) values ('RS01', 'RS Uji')")
    conn.execute("insert into uji.peserta (id_peserta, nama) values ('P01', 'Peserta Uji')")
    conn.execute(
        "insert into uji.panggilan (id, id_peserta, id_rs, bulan_layanan, sesi_ditagih, penerima)"
        " values ('C1', 'P01', 'RS01', '2026-08', 10, 'peserta')"
    )
    baris = conn.execute("select prioritas, coba_lagi_setelah from uji.panggilan where id = 'C1'").fetchone()
    assert baris == {"prioritas": False, "coba_lagi_setelah": None}
    with pytest.raises(psycopg.errors.NotNullViolation):
        conn.execute("update uji.panggilan set prioritas = null where id = 'C1'")


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


def test_kolom_d01_ditambahkan_ke_tabel_yang_sudah_ada(conn):
    """diambil_pada, tangkapan_sementara, durasi_detik harus menyusul di database yang sudah menerapkan skema lama."""
    conn.execute(SKEMA_V3)
    conn.execute("alter table uji.panggilan drop column diambil_pada, drop column tangkapan_sementara, drop column durasi_detik")
    assert not {"diambil_pada", "tangkapan_sementara", "durasi_detik"} & kolom(conn, "panggilan")
    conn.execute(SKEMA_V3)
    assert {"diambil_pada", "tangkapan_sementara", "durasi_detik"} <= kolom(conn, "panggilan")


def tambah_panggilan(conn, id_="C1"):
    conn.execute("insert into uji.rumah_sakit (id_rs, nama_rs) values ('RS01', 'RS Uji') on conflict do nothing")
    conn.execute("insert into uji.peserta (id_peserta, nama) values ('P01', 'Peserta Uji') on conflict do nothing")
    conn.execute(
        "insert into uji.panggilan (id, id_peserta, id_rs, bulan_layanan, sesi_ditagih, penerima)"
        f" values ('{id_}', 'P01', 'RS01', '2026-08', 10, 'peserta')"
    )


def test_keputusan_boleh_pantau_dan_menolak_tindakan_ngawur(conn):
    conn.execute(SKEMA_V3)
    tambah_panggilan(conn)
    conn.execute(
        "insert into uji.keputusan_panggilan (panggilan_id, verifikator, tindakan, ikut_saran)"
        " values ('C1', 'R. Santoso', 'pantau', true)"
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "insert into uji.keputusan_panggilan (panggilan_id, verifikator, tindakan, ikut_saran)"
            " values ('C1', 'R. Santoso', 'ngawur', true)"
        )


def test_batas_tindakan_lama_diganti_di_database_yang_sudah_ada(conn):
    """Tabel buatan skema lama (tanpa pantau) harus bisa menerima pantau setelah skema dijalankan ulang."""
    conn.execute(SKEMA_V3)
    conn.execute("alter table uji.keputusan_panggilan drop constraint keputusan_panggilan_tindakan_check")
    conn.execute(
        "alter table uji.keputusan_panggilan add constraint keputusan_panggilan_tindakan_check"
        " check (tindakan in ('tutup_kasus','minta_klarifikasi_rs','teruskan_pk_jkn'))"
    )
    tambah_panggilan(conn)
    pantau = (
        "insert into uji.keputusan_panggilan (panggilan_id, verifikator, tindakan, ikut_saran)"
        " values ('C1', 'R. Santoso', 'pantau', true)"
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        with conn.transaction():
            conn.execute(pantau)
    conn.execute(SKEMA_V3)
    conn.execute(pantau)
