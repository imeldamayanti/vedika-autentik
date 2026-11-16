"""Skor pola v3: sinyal prioritas antrean, bukan pemicu dan bukan putusan.

Fitur, bin, skor, dan alasan dihitung oleh data-uji-konfirmasi/tools/pola.py, dimuat apa adanya seperti
aturan.py. Model dan referensi nasional adalah berkas JSON agregat di data-uji-konfirmasi/referensi-pola.
"""
import importlib.util
import json
import math
from functools import lru_cache

from .config import DATA_UJI

VERSI_BAWAAN = "pola-v1"
NASIONAL = "Nasional"


@lru_cache
def pola():
    spec = importlib.util.spec_from_file_location("pola", DATA_UJI / "tools" / "pola.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@lru_cache
def model(versi: str = VERSI_BAWAAN) -> dict:
    return json.loads((DATA_UJI / "referensi-pola" / f"model-{versi}.json").read_text(encoding="utf-8"))


@lru_cache
def referensi() -> dict:
    return json.loads((DATA_UJI / "referensi-pola" / "referensi.json").read_text(encoding="utf-8"))


def nilai(fitur: dict, versi: str = VERSI_BAWAAN) -> dict:
    """Skor, logit (kunci urutan antrean), penanda tinggi, dan dua alasan teratas untuk satu bulan-pasien."""
    m = model(versi)
    skor = pola().skor(m, fitur)
    return {
        "skor": skor, "logit": pola().logit(m, fitur), "tinggi": skor >= m["ambang_tinggi"],
        "alasan": pola().alasan(m, referensi(), fitur),
    }


def _persen(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def kombinasi(i1: bool, i2: bool, i3: bool, i4: bool) -> dict:
    kunci = pola().kombinasi(i1, i2, i3, i4)
    sel = referensi()["kombinasi"][kunci]
    if "prevalensi" in sel:
        besar = f"{_persen(100 * sel['prevalensi'])}%"
    else:  # sel di bawah 10 baris: hanya batas atas yang disimpan
        besar = f"kurang dari {_persen(math.ceil(10000 * sel['prevalensi_maks']) / 100)}%"
    return {"kunci": kunci, "teks": f"Kombinasi {kunci} terjadi pada {besar} bulan-pasien fisioterapi nasional {referensi()['tahun']}."}


def pembanding(tipe_rs: str | None, aktif: int, persen_terpicu: float) -> dict:
    """Posisi satu RS terhadap RS sejenis nasional. Kelompok sejenis hanya mendekati RS (data sampel tanpa identitas RS)."""
    ref = referensi()
    tipe = ref["peta_tipe"].get(tipe_rs or "", NASIONAL)
    b = ref["pembanding_tipe"][tipe]
    if not aktif or "terpicu_p95" not in b:
        posisi = "tidak_ada_pembanding"
    elif persen_terpicu > b["terpicu_p95"]:
        posisi = "di_atas_p95"
    elif persen_terpicu > b["terpicu_p90"]:
        posisi = "di_atas_p90"
    else:
        posisi = "wajar"
    return {
        "tipe": tipe, "persen_terpicu_nasional": b["persen_terpicu"], "sesi_rata_nasional": b["sesi_rata"],
        "terpicu_p95_kelompok": b.get("terpicu_p95"), "posisi": posisi,
    }
