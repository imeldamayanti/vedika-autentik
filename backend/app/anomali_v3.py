"""Anomaly model (anomali-v2) in the backend: who the model selects, why, and the hospital funnel.

Scoring is data-uji-konfirmasi/tools/anomali.py, loaded as is (like pola.py and aturan.py); the model is
the aggregate table referensi-pola/model-anomali-v2.json. Patients are called when the rules OR the model
select them, rarest pattern first. The model never sets a label, a recommendation, or a hospital status.
"""
import importlib.util
import json
from functools import lru_cache

from .config import DATA_UJI

VERSION = "anomali-v2"


@lru_cache
def anomali():
    spec = importlib.util.spec_from_file_location("anomali", DATA_UJI / "tools" / "anomali.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache
def pola():
    """Visit-pattern features (tools/pola.py)."""
    spec = importlib.util.spec_from_file_location("pola", DATA_UJI / "tools" / "pola.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache
def model() -> dict:
    return json.loads((DATA_UJI / "referensi-pola" / f"model-{VERSION}.json").read_text(encoding="utf-8"))


def score(pattern_features: dict, visits: list[dict], age: int | None) -> dict:
    """Score one patient-month. visits: {referred, other_district} per visit in that month."""
    a = anomali()
    features = a.anomaly_features(pattern_features, visits)
    group = a.age_group(age)
    result = a.score(model(), features, group)
    why = a.reasons(model(), features, group)
    return {
        "skor": result["score"],
        "ditandai": result["flagged"],
        "langka": result["rare"],
        "alasan": {"alasan": [r["text"] for r in why["rare_bins"]], "gabungan": why["pattern"]},
    }


def selected_by(triggered: bool, flagged: bool) -> str | None:
    """'keduanya', 'aturan', 'model', or None when neither selects the patient-month."""
    if triggered and flagged:
        return "keduanya"
    if triggered:
        return "aturan"
    return "model" if flagged else None


def funnel(rows: list[tuple[int | None, bool]]) -> dict:
    """Funnel position of one hospital. rows: (age, selected) per patient-month."""
    a = anomali()
    return a.hospital_funnel(model(), [(a.age_group(age), selected) for age, selected in rows])
