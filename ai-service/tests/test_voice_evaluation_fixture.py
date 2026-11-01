import json
from pathlib import Path

from vedika_ai.evaluation import EvaluationCase

FIXTURE = Path(__file__).parent / "fixtures" / "voice-evaluation-20.json"
REQUIRED_TAGS = {"peserta", "keluarga", "ragu", "menolak", "tanda_bahaya", "santai", "bising"}
KEY_FIELDS = {
    "status_panggilan",
    "penerima",
    "hadir",
    "jumlah_maks",
    "keyakinan",
    "tanda_bahaya",
}


def test_voice_evaluation_fixture_has_twenty_valid_varied_key_field_cases():
    raw_cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = [EvaluationCase.model_validate(item) for item in raw_cases]

    assert len(cases) == 20
    assert len({case.id for case in cases}) == 20
    assert REQUIRED_TAGS <= {tag for case in cases for tag in case.tags}
    for case in cases:
        assert case.transkrip
        assert set(case.expected) == {"hasil", "label"}
        assert set(case.expected["hasil"]) == KEY_FIELDS


def test_ambiguous_participant_cases_contain_explicit_recipient_evidence():
    raw_cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in raw_cases}

    for case_id in {
        "V11-selisih-tiga",
        "V15-audio-bising",
        "V16-mengoreksi-angka",
        "V17-rentang-tujuh-delapan",
        "V20-rentang-ragu",
    }:
        transcript = " ".join(turn["teks"] for turn in cases[case_id]["transkrip"]).casefold()
        assert "saya pasiennya" in transcript, case_id
