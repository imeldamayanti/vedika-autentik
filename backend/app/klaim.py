"""Data klaim pembanding (stand-in E-Klaim), dicari lewat nomor SEP.

Sumber sementara: klaim pada ground truth dataset. Produksi: E-Klaim INA-CBG.
"""
import json
from functools import lru_cache

from .config import AKAR


@lru_cache
def _peta() -> dict[str, dict]:
    manifest = json.loads((AKAR / "dataset" / "manifest.json").read_text())
    return {b["klaim"]["sep"]: b["klaim"] for b in manifest}


def cari(sep: str | None) -> dict | None:
    klaim = _peta().get(sep or "")
    return dict(klaim) if klaim else None
