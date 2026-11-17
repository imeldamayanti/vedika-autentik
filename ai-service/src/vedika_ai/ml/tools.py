"""The stdlib-only feature and scoring modules shared with the backend and the demo data.

They live in data-uji-konfirmasi/tools so the backend can use them without this package.
"""

from __future__ import annotations

import importlib.util
from functools import cache
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[4]
TOOLS = ROOT / "data-uji-konfirmasi" / "tools"
MODEL_DIR = ROOT / "data-uji-konfirmasi" / "referensi-pola"
REFERENCE_DIR = ROOT / "ai-service" / "data" / "reference"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@cache
def pola() -> ModuleType:
    return _load("pola")


@cache
def anomali() -> ModuleType:
    return _load("anomali")
