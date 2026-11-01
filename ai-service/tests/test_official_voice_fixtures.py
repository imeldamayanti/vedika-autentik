import json
from pathlib import Path

import pytest

from vedika_ai.answers import JawabanTerstruktur, classify_answer

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "data-uji-konfirmasi"
SCENARIOS = json.loads((FIXTURE_ROOT / "skenario_uji.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "scenario",
    [scenario for scenario in SCENARIOS if scenario["expected_jawaban"] is not None],
    ids=lambda scenario: scenario["id_skenario"],
)
def test_official_voice_answers_validate_and_produce_expected_label(scenario):
    answer = JawabanTerstruktur.model_validate(scenario["expected_jawaban"])

    decision = classify_answer(
        answer,
        billed_sessions=scenario["expected_indikator"]["sesi_ditagih"],
    )

    assert decision.label == scenario["expected_label"]
