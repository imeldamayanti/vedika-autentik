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


class PembacaPalsu:
    """Pengganti klien pembaca (Kontrak B2) di uji. balasan: urutan jawaban dict atau MesinGalat/Exception;
    balasan terakhir dipakai berulang. Semua permintaan tercatat di .permintaan."""

    def __init__(self, *balasan):
        self.balasan = list(balasan)
        self.permintaan = []

    def baca(self, permintaan, batas_detik=30):
        self.permintaan.append(permintaan)
        b = self.balasan.pop(0) if len(self.balasan) > 1 else self.balasan[0]
        if isinstance(b, Exception):
            raise b
        return b

    def sehat(self):
        return True
