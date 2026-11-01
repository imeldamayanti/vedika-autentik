import io
import json
from datetime import UTC, datetime

from vedika_ai.voice import GeminiTokenIssuer, VoiceContext, build_voice_instruction


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def context(**updates) -> VoiceContext:
    values = {
        "nama_penerima": "Andi Pratama",
        "sapaan_penerima": "Bapak",
        "hubungan": "peserta",
        "nama_pasien": "Andi Pratama",
        "sapaan_pasien": "Bapak",
        "nama_rs": "RS Melati Sehat",
        "bulan": "Agustus",
        "tanggal_libur": ["16 Agustus", "17 Agustus"],
    }
    values.update(updates)
    return VoiceContext.model_validate(values)


def test_voice_instruction_contains_required_flow_safety_and_seven_branches():
    instruction = build_voice_instruction(context())

    for required in [
        "asisten otomatis",
        "direkam",
        "bukan tagihan",
        "NIK",
        "OTP",
        "rekening",
        "uang",
        "satu pertanyaan",
        "20 kata",
        "curang",
        "fraud",
        "penerima yang benar",
        "tidak ingat",
        "penipuan",
        "berhenti",
        "di luar topik",
        "tidak pernah terapi",
        "Care Center 165",
        "150 detik",
        "Bapak Andi Pratama",
        "RS Melati Sehat",
        "Agustus",
        "16 dan 17 Agustus",
    ]:
        assert required.casefold() in instruction.casefold(), required


def test_voice_context_accepts_the_b1_skrip_with_unknown_fields():
    skrip = context().model_dump() | {"field_baru": "diabaikan"}

    assert VoiceContext.model_validate(skrip) == context()


def test_voice_instruction_greets_family_on_behalf_of_the_patient():
    instruction = build_voice_instruction(
        context(
            nama_penerima="Budi Santoso",
            sapaan_penerima="Bapak/Ibu",
            hubungan="anak",
            nama_pasien="Siti Aminah",
            sapaan_pasien="Ibu",
        )
    )

    assert "keluarga Ibu Siti" in instruction
    assert "(anak)" in instruction


def test_voice_instruction_keeps_holidays_from_different_months_whole():
    instruction = build_voice_instruction(context(tanggal_libur=["31 Agustus", "1 September"]))

    assert "31 Agustus dan 1 September" in instruction


def test_voice_instruction_omits_holiday_question_when_no_holiday_is_flagged():
    instruction = build_voice_instruction(context(tanggal_libur=[]))

    assert "Jangan bertanya tentang tanggal libur" in instruction
    assert "tanggal libur yang perlu ditanyakan" not in instruction.casefold()


def test_token_issuer_requests_one_use_constrained_token_without_leaking_server_key():
    captured = {}

    def opener(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response(
            json.dumps(
                {
                    "name": "auth_tokens/ephemeral-one-use",
                    "expireTime": "2026-10-28T11:35:00Z",
                }
            ).encode()
        )

    issuer = GeminiTokenIssuer(
        api_key="permanent-server-key",
        model="gemini-live-test",
        opener=opener,
        now=lambda: datetime(2026, 10, 28, 11, 30, tzinfo=UTC),
    )

    result = issuer.issue(context())

    request = captured["request"]
    body = json.loads(request.data)
    dumped_result = json.dumps(result.model_dump(mode="json"))
    assert body["uses"] == 1
    assert body["bidiGenerateContentSetup"]["model"] == "models/gemini-live-test"
    assert request.get_header("X-goog-api-key") == "permanent-server-key"
    assert "permanent-server-key" not in request.full_url
    assert "permanent-server-key" not in dumped_result
    assert result.token == "auth_tokens/ephemeral-one-use"
    assert "BidiGenerateContentConstrained" in result.websocket_url
    assert result.maks_durasi_detik == 150
    assert result.instruksi == build_voice_instruction(context())



def test_token_issuer_sends_bidi_generate_content_setup():
    captured = {}

    def opener(request, timeout):
        captured["body"] = json.loads(request.data)
        return Response(
            json.dumps(
                {"name": "auth_tokens/ephemeral-one-use", "expireTime": "2026-10-28T11:35:00Z"}
            ).encode()
        )

    issuer = GeminiTokenIssuer(
        api_key="permanent-server-key",
        model="gemini-live-test",
        opener=opener,
        now=lambda: datetime(2026, 10, 28, 11, 30, tzinfo=UTC),
    )

    issuer.issue(context())

    body = captured["body"]
    assert "liveConnectConstraints" not in body
    assert body["bidiGenerateContentSetup"] == {
        "model": "models/gemini-live-test",
        "generationConfig": {"responseModalities": ["AUDIO"]},
        "inputAudioTranscription": {},
        "outputAudioTranscription": {},
    }


def test_token_issuer_uses_requested_expiry_when_response_has_only_name():
    def opener(request, timeout):
        return Response(json.dumps({"name": "auth_tokens/ephemeral-one-use"}).encode())

    issuer = GeminiTokenIssuer(
        api_key="permanent-server-key",
        model="gemini-live-test",
        opener=opener,
        now=lambda: datetime(2026, 10, 28, 11, 30, tzinfo=UTC),
    )

    result = issuer.issue(context())

    assert result.token == "auth_tokens/ephemeral-one-use"
    assert result.kedaluwarsa == datetime(2026, 10, 28, 11, 35, tzinfo=UTC)
