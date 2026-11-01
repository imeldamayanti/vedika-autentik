import io
import json
from urllib.error import HTTPError, URLError

import pytest

from vedika_ai.gemini import GeminiError, GeminiTransport


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def test_transport_sends_schema_and_key_in_header_and_returns_candidate_text():
    captured = {}

    def opener(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        payload = {"candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}]}
        return Response(json.dumps(payload).encode())

    transport = GeminiTransport("server-secret", "models/gemini-test", opener=opener)

    result = transport.generate_json("extract", {"type": "object"})

    request = captured["request"]
    body = json.loads(request.data)
    assert result == '{"ok":true}'
    assert request.get_header("X-goog-api-key") == "server-secret"
    assert "server-secret" not in request.full_url
    assert body["generationConfig"]["responseJsonSchema"] == {"type": "object"}
    assert captured["timeout"] == 30


def test_transport_maps_network_and_malformed_provider_responses_to_safe_codes():
    def unavailable(*_args, **_kwargs):
        raise URLError("secret network detail")

    with pytest.raises(GeminiError) as network_error:
        GeminiTransport("key", "model", opener=unavailable).generate_json("x", {})
    assert network_error.value.code == "penyedia_tidak_tersedia"

    with pytest.raises(GeminiError) as malformed_error:
        GeminiTransport(
            "key",
            "model",
            opener=lambda *_args, **_kwargs: Response(b"{}"),
        ).generate_json("x", {})
    assert malformed_error.value.code == "respons_penyedia_tidak_valid"


@pytest.mark.parametrize("timeout", [TimeoutError("read"), URLError(TimeoutError("connect"))])
def test_transport_maps_read_and_connect_timeouts_to_batas_waktu(timeout):
    def slow(*_args, **_kwargs):
        raise timeout

    with pytest.raises(GeminiError) as raised:
        GeminiTransport("key", "model", opener=slow).generate_json("x", {})
    assert raised.value.code == "batas_waktu"


@pytest.mark.parametrize(
    ("status_code", "retryable"),
    [(400, False), (401, False), (403, False), (404, False), (429, True), (500, True)],
)
def test_transport_preserves_safe_http_diagnostics(status_code, retryable):
    def rejected(request, timeout):
        del timeout
        raise HTTPError(request.full_url, status_code, "provider error", None, None)

    with pytest.raises(GeminiError) as captured:
        GeminiTransport("key", "model", opener=rejected).generate_json("x", {})

    assert captured.value.code == "penyedia_tidak_tersedia"
    assert captured.value.status_code == status_code
    assert captured.value.retryable is retryable


def test_transport_retries_transient_http_errors_with_configured_backoff():
    attempts = 0
    delays = []

    def temporarily_unavailable(request, timeout):
        nonlocal attempts
        del timeout
        attempts += 1
        if attempts < 3:
            raise HTTPError(request.full_url, 503, "unavailable", None, None)
        return Response(
            json.dumps(
                {"candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}]}
            ).encode()
        )

    transport = GeminiTransport(
        "key",
        "model",
        opener=temporarily_unavailable,
        retry_delays=(2, 4, 8),
        sleeper=delays.append,
    )

    result = transport.generate_json("x", {})

    assert result == '{"ok":true}'
    assert attempts == 3
    assert delays == [2, 4]


def test_transport_marks_transient_error_exhausted_after_retry_schedule():
    attempts = 0
    delays = []

    def unavailable(request, timeout):
        nonlocal attempts
        del timeout
        attempts += 1
        raise HTTPError(request.full_url, 503, "unavailable", None, None)

    transport = GeminiTransport(
        "key",
        "model",
        opener=unavailable,
        retry_delays=(1, 2),
        sleeper=delays.append,
    )

    with pytest.raises(GeminiError) as captured:
        transport.generate_json("x", {})

    assert attempts == 3
    assert delays == [1, 2]
    assert captured.value.status_code == 503
    assert captured.value.retryable is True
    assert captured.value.retry_exhausted is True

