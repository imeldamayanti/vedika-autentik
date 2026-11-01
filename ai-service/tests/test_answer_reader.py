import json

import pytest
from loguru import logger

from vedika_ai.answer_reader import AnswerReader, ReadAnswerRequest, ReadContext, TranscriptTurn
from vedika_ai.errors import ServiceError
from vedika_ai.gemini import GeminiError

VALID = {
    "status_panggilan": "terjawab",
    "penerima": "peserta",
    "hubungan": None,
    "hadir": True,
    "jumlah_min": 3,
    "jumlah_maks": 3,
    "keyakinan": "tinggi",
    "tanda_bahaya": [],
    "membantah_tanggal_libur": True,
    "kutipan_kunci": "Tiga kali. Hari Minggu tutup.",
    "ringkasan": "Peserta menyatakan hadir tiga kali dan membantah sesi hari Minggu.",
}


class FakeGenerator:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def generate_json(self, prompt, schema):
        self.calls.append((prompt, schema))
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


def request(secret_text: str = "Tiga kali.", tanggal_libur=("2026-08-16",)) -> ReadAnswerRequest:
    return ReadAnswerRequest(
        id="CALL-P-S1-2026-08",
        transkrip=[
            TranscriptTurn(detik=39, pembicara="ai", teks="Berapa kali datang terapi?"),
            TranscriptTurn(detik=45, pembicara="penerima", teks=secret_text),
            TranscriptTurn(detik=50, pembicara="penerima", teks="Hari Minggu tutup."),
        ],
        konteks=ReadContext(
            sesi_ditagih=11,
            tanggal_libur=list(tanggal_libur),
            nama_pasien="Andi Pratama",
            bulan="2026-08",
        ),
    )


def capture_logs():
    messages = []
    sink = logger.add(lambda message: messages.append(str(message)), format="{message}")
    return messages, sink


def test_reader_returns_the_validated_answer_from_a_single_attempt():
    generator = FakeGenerator([json.dumps(VALID)])

    answer = AnswerReader(generator).read(request())

    assert answer.model_dump() == VALID
    assert len(generator.calls) == 1


@pytest.mark.parametrize(
    "transkrip",
    [[], [TranscriptTurn(detik=0, pembicara="penerima", teks="  ")]],
)
def test_reader_rejects_empty_transcript_without_calling_the_model(transkrip):
    generator = FakeGenerator([])

    with pytest.raises(ServiceError) as raised:
        AnswerReader(generator).read(ReadAnswerRequest(transkrip=transkrip))

    assert (raised.value.status, raised.value.code) == (422, "transkrip_kosong")
    assert generator.calls == []


@pytest.mark.parametrize(
    "malformed",
    [
        "not-json",
        json.dumps({**VALID, "jumlah_min": True, "jumlah_maks": True}),
        json.dumps({**VALID, "membantah_tanggal_libur": "false"}),
        json.dumps({**VALID, "hubungan": "tetangga"}),
        json.dumps({key: value for key, value in VALID.items() if key != "tanda_bahaya"}),
    ],
)
def test_reader_reports_malformed_output_as_llm_failure_without_retrying(malformed):
    generator = FakeGenerator([malformed])

    with pytest.raises(ServiceError) as raised:
        AnswerReader(generator).read(request())

    assert (raised.value.status, raised.value.code) == (502, "llm_gagal")
    assert len(generator.calls) == 1


@pytest.mark.parametrize(
    ("provider_code", "status", "code"),
    [
        ("penyedia_tidak_tersedia", 502, "llm_gagal"),
        ("respons_penyedia_tidak_valid", 502, "llm_gagal"),
        ("batas_waktu", 504, "batas_waktu"),
    ],
)
def test_reader_maps_provider_errors_and_logs_no_transcript(provider_code, status, code):
    secret = "NIK-SECRET-987654321"
    messages, sink = capture_logs()
    try:
        with pytest.raises(ServiceError) as raised:
            AnswerReader(FakeGenerator([GeminiError(provider_code, status_code=503)])).read(
                request(secret)
            )
    finally:
        logger.remove(sink)

    assert (raised.value.status, raised.value.code) == (status, code)
    assert "status=503" in "".join(messages)
    assert secret not in "".join(messages)


def test_reader_clears_holiday_denial_when_no_holiday_was_asked():
    generator = FakeGenerator([json.dumps(VALID)])

    answer = AnswerReader(generator).read(request(tanggal_libur=()))

    assert answer.membantah_tanggal_libur is None


def test_prompt_contains_context_roles_and_every_required_output_field():
    generator = FakeGenerator([json.dumps(VALID)])

    AnswerReader(generator).read(request())

    prompt, schema = generator.calls[0]
    assert "ai: Berapa kali datang terapi?" in prompt
    assert "penerima: Tiga kali." in prompt
    assert "2026-08-16" in prompt
    assert "Andi Pratama" in prompt
    assert "11" not in prompt
    assert set(schema["properties"]) == set(VALID)
