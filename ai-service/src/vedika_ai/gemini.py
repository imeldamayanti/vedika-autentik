"""Small Gemini REST transport with no SDK/runtime dependency."""

import json
import time
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GeminiError(Exception):
    def __init__(
        self,
        code: str,
        *,
        retryable: bool = True,
        retry_exhausted: bool = False,
        status_code: int | None = None,
    ):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.retry_exhausted = retry_exhausted
        self.status_code = status_code


class GeminiTransport:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout: float = 30,
        opener: Callable[..., Any] = urlopen,
        retry_delays: tuple[float, ...] = (),
        sleeper: Callable[[float], None] = time.sleep,
    ):
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.api_key = api_key
        self.model = model.removeprefix("models/")
        self.timeout = timeout
        self.opener = opener
        self.retry_delays = retry_delays
        self.sleeper = sleeper

    def generate_json(self, prompt: str, schema: dict) -> str:
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
                "temperature": 0,
            },
        }
        request = Request(
            (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:generateContent"
            ),
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        for retry_index in range(len(self.retry_delays) + 1):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                return payload["candidates"][0]["content"]["parts"][0]["text"]
            except HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if retryable and retry_index < len(self.retry_delays):
                    self.sleeper(self.retry_delays[retry_index])
                    continue
                raise GeminiError(
                    "penyedia_tidak_tersedia",
                    retryable=retryable,
                    retry_exhausted=retryable and bool(self.retry_delays),
                    status_code=error.code,
                ) from error
            except (URLError, TimeoutError, OSError) as error:
                if retry_index < len(self.retry_delays):
                    self.sleeper(self.retry_delays[retry_index])
                    continue
                timed_out = isinstance(error, TimeoutError) or isinstance(
                    getattr(error, "reason", None), TimeoutError
                )
                raise GeminiError(
                    "batas_waktu" if timed_out else "penyedia_tidak_tersedia",
                    retry_exhausted=bool(self.retry_delays),
                ) from error
            except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
                raise GeminiError("respons_penyedia_tidak_valid") from error

        raise AssertionError("Gemini retry loop exhausted without a result")

