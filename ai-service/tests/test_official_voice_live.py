import os
from pathlib import Path

import pytest

from vedika_ai import config
from vedika_ai.answer_reader import AnswerReader
from vedika_ai.answers import JawabanTerstruktur, classify_answer
from vedika_ai.gemini import GeminiTransport
from vedika_ai.official_voice import (
    NOT_CONNECTED_ANSWER,
    load_official_cases,
    parse_official_transcript,
    read_official_answers,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "data-uji-konfirmasi"
KEY_FIELDS = (
    "status_panggilan",
    "penerima",
    "hadir",
    "jumlah_maks",
    "keyakinan",
    "tanda_bahaya",
)


def test_parse_official_transcript_maps_known_speakers_and_timestamps():
    turns = parse_official_transcript(FIXTURE_ROOT / "transkrip_uji" / "S1.txt")

    assert len(turns) == 9
    assert turns[0].model_dump() == {
        "detik": 0,
        "pembicara": "ai",
        "teks": (
            "Selamat siang, saya asisten otomatis dari BPJS Kesehatan. Panggilan ini "
            "direkam untuk konfirmasi layanan. Ini bukan tagihan, dan saya tidak akan "
            "meminta data pribadi, kode OTP, atau pembayaran apa pun. Apakah benar saya "
            "bicara dengan Bapak Andi Pratama?"
        ),
    }
    assert turns[1].detik == 1
    assert turns[1].pembicara == "penerima"
    assert turns[1].teks == "Iya, saya sendiri."


def test_parse_official_transcript_rejects_unknown_speaker(tmp_path):
    source = tmp_path / "unknown.txt"
    source.write_text("Operator: Halo\n", encoding="utf-8")

    with pytest.raises(ValueError, match="pembicara tidak dikenal"):
        parse_official_transcript(source)


def test_load_official_cases_covers_all_answer_scenarios_with_literal_s1_expectation():
    cases = load_official_cases(FIXTURE_ROOT)

    assert [case.id_skenario for case in cases] == ["S1", "S2", "S3", "S4", "S5", "S6", "S8"]
    s1 = cases[0]
    assert s1.request.id == "CALL-P-S1-2026-08"
    assert s1.request.konteks.model_dump(mode="json") == {
        "sesi_ditagih": 11,
        "tanggal_libur": ["2026-08-16", "2026-08-17"],
        "nama_pasien": "Andi Pratama",
        "bulan": "2026-08",
    }
    assert s1.expected_label == "Tidak sesuai"
    assert s1.expected_key_fields == {
        "status_panggilan": "terjawab",
        "penerima": "peserta",
        "hadir": True,
        "jumlah_maks": 3,
        "keyakinan": "tinggi",
        "tanda_bahaya": [],
    }
    assert len(s1.request.transkrip) == 9
    assert cases[4].id_skenario == "S5"
    assert cases[4].request.transkrip == []


def test_read_official_answers_writes_uji_py_rows_and_skips_reader_for_s5():
    class RecordingReader:
        def __init__(self):
            self.ids = []

        def read(self, request):
            self.ids.append(request.id)
            return JawabanTerstruktur.model_validate(
                {**NOT_CONNECTED_ANSWER, "status_panggilan": "terjawab", "ringkasan": "Uji."}
            )

    reader = RecordingReader()
    rows = read_official_answers(FIXTURE_ROOT, reader)

    assert len(reader.ids) == 6
    assert [row["id_skenario"] for row in rows] == ["S1", "S2", "S3", "S4", "S5", "S6", "S8"]
    assert "CALL-P-S5-2026-08" not in reader.ids
    assert rows[4]["jawaban"] == NOT_CONNECTED_ANSWER


@pytest.mark.live_gemini
@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_GEMINI") != "1",
    reason="set RUN_LIVE_GEMINI=1 to run provider acceptance",
)
def test_live_gemini_matches_all_official_conversation_fields_and_labels():
    api_key = config.gemini_api_key()
    if not api_key:
        pytest.fail("GEMINI_API_KEY is required when RUN_LIVE_GEMINI=1")
    reader = AnswerReader(
        GeminiTransport(api_key, config.gemini_text_model(), timeout=config.READER_TIMEOUT_SECONDS)
    )
    failures = []

    for case in load_official_cases(FIXTURE_ROOT):
        if not case.request.transkrip:
            continue
        answer = reader.read(case.request)
        actual = answer.model_dump(mode="json")
        differences = [
            field
            for field in KEY_FIELDS
            if actual.get(field) != case.expected_key_fields[field]
        ]
        if classify_answer(answer, case.request.konteks.sesi_ditagih).label != case.expected_label:
            differences.append("label")
        if differences:
            failures.append({"id": case.id_skenario, "fields": differences})

    assert failures == []
