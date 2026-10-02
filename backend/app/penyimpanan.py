"""Penyimpanan berkas di disk lokal. Nanti bisa diganti Supabase Storage tanpa mengubah pemanggil."""
import re
from pathlib import Path


def _aman(nama: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", Path(nama).name) or "berkas"


class Penyimpanan:
    def __init__(self, akar: Path):
        self.akar = Path(akar)

    def simpan(self, id_: str, nama: str, isi: bytes) -> str:
        rel = f"{id_}/{_aman(nama)}"
        tujuan = self.akar / rel
        tujuan.parent.mkdir(parents=True, exist_ok=True)
        tujuan.write_bytes(isi)
        return rel

    def baca(self, rel: str) -> bytes:
        tujuan = (self.akar / rel).resolve()
        if self.akar.resolve() not in tujuan.parents:
            raise ValueError("path di luar penyimpanan")
        return tujuan.read_bytes()
