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
