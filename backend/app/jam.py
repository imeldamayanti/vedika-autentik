"""Jam API. Satu pintu supaya uji bisa menggeser waktu (monkeypatch jam.sekarang)."""
from datetime import datetime

from .config import ZONA


def sekarang() -> datetime:
    return datetime.now(ZONA)


def iso(waktu: datetime | None) -> str | None:
    """ISO 8601 berzona WIB tanpa pecahan detik, mis. 2026-10-06T09:14:00+07:00."""
    return waktu.astimezone(ZONA).isoformat(timespec="seconds") if waktu else None
