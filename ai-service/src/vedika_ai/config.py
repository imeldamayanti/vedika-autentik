"""Small environment-based configuration for the stateless service."""

import os

from . import __version__

ENGINE_VERSION = f"pramana-{__version__}"
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def service_key() -> str | None:
    return os.environ.get("AI_SERVICE_KEY") or None


def log_level() -> str:
    return os.environ.get("LOG_LEVEL", "INFO").upper()


def json_logs() -> bool:
    return os.environ.get("LOG_FORMAT", "json").lower() == "json"
