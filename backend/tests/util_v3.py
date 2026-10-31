"""Pembantu uji v3: geser jam API dan ubah baris panggilan langsung di DB uji."""
from datetime import datetime

from app import config, jam


def jam_palsu(monkeypatch, tahun=2026, bulan=10, tanggal=6, jam_=10, menit=0, detik=0):
    waktu = datetime(tahun, bulan, tanggal, jam_, menit, detik, tzinfo=config.ZONA)
    monkeypatch.setattr(jam, "sekarang", lambda: waktu)
    return waktu


def wib(*bagian):
    return datetime(*bagian, tzinfo=config.ZONA)


def ubah(conn, id_, **kolom):
    sets = ", ".join(f"{k} = %s" for k in kolom)
    conn.execute(f"update panggilan set {sets} where id = %s", (*kolom.values(), id_))
