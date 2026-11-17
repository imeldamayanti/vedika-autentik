"""Small environment-based configuration for the stateless service."""

import os

from . import __version__

ENGINE_VERSION = f"pramana-{__version__}"
READER_VERSION = f"pembaca-{__version__}"
# The backend waits 30 seconds per /v1/baca attempt; answer before that.
READER_TIMEOUT_SECONDS = 25


def service_key() -> str | None:
    return os.environ.get("AI_SERVICE_KEY") or None


def log_level() -> str:
    return os.environ.get("LOG_LEVEL", "INFO").upper()


def json_logs() -> bool:
    return os.environ.get("LOG_FORMAT", "json").lower() == "json"


def gemini_api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or None


def gemini_live_model() -> str:
    return os.environ.get("GEMINI_LIVE_MODEL", "gemini-3.8-live")


def gemini_text_model() -> str:
    return os.environ.get("GEMINI_TEXT_MODEL", "gemini-3.5-flash-lite")


def gemini_text_fallback_model() -> str | None:
    """Second text model for the answer reader when the main one is busy. Empty value turns it off."""
    model = os.environ.get("GEMINI_TEXT_MODEL_CADANGAN", "gemini-3.5-flash").strip()
    return model if model and model != gemini_text_model() else None


# ---- Phone helper (saluran.py): station laptop only ----


def line_mode() -> str | None:
    """SALURAN_ADB: 1 = real Android phone over adb, palsu = in-memory fake, else disabled."""
    mode = os.environ.get("SALURAN_ADB", "").strip().lower()
    return mode if mode in ("1", "palsu") else None


def adb_bin() -> str:
    return os.environ.get("SALURAN_ADB_BIN") or "adb"


def adb_serial() -> str | None:
    return os.environ.get("SALURAN_ADB_SERIAL") or None


def line_api_url() -> str:
    return os.environ.get("SALURAN_API_URL") or "http://localhost:8000"


def line_agent_key() -> str | None:
    return os.environ.get("SALURAN_AGEN_KEY") or None


def line_audio() -> str:
    return "kabel" if os.environ.get("SALURAN_AUDIO", "").strip().lower() == "kabel" else "speaker"


def line_input() -> str | None:
    return os.environ.get("SALURAN_INPUT") or None


def line_output() -> str | None:
    return os.environ.get("SALURAN_OUTPUT") or None
