import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest

from vedika_ai.answers import JawabanTerstruktur, classify_answer
from vedika_ai.indicators import IndicatorRequest, ServiceSession, calculate_indicators

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "data-uji-konfirmasi"
SCENARIOS = json.loads((FIXTURE_ROOT / "skenario_uji.json").read_text(encoding="utf-8"))


def _csv_rows(filename):
    with (FIXTURE_ROOT / filename).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_official_indicators_match_all_300_expected_rows():
    sessions = defaultdict(list)
    for row in _csv_rows("klaim_sesi.csv"):
        sessions[(row["id_peserta"], row["id_rs"], row["tanggal"][:7])].append(
            date.fromisoformat(row["tanggal"])
        )
    holidays = {
        date.fromisoformat(row["tanggal"])
        for row in _csv_rows("libur_nasional_2026.csv")
    }

    for expected in _csv_rows("expected_indikator_2026-08.csv"):
        participant = expected["id_peserta"]
        hospital = expected["id_rs"]
        current_dates = sessions[(participant, hospital, "2026-08")]
        active_months = [
            month
            for (candidate, candidate_hospital, month) in sessions
            if candidate == participant and candidate_hospital == hospital
        ]
        result = calculate_indicators(
            IndicatorRequest(
                bulan="2026-08",
                sesi=[
                    ServiceSession(tanggal=value, hari_libur=value in holidays)
                    for value in current_dates
                ],
                bulan_aktif=active_months,
            )
        )

        assert result.sesi_ditagih == int(expected["sesi_ditagih"])
        assert result.i1 is (expected["I1_lebih_8_sebulan"] == "True")
        assert result.i2 is (expected["I2_3x_seminggu"] == "True")
        assert result.i3 is (expected["I3_episode_6_bulan"] == "True")
        assert result.i4 is (expected["I4_hari_libur"] == "True")
        assert len(result.indikator_aktif) == int(expected["jumlah_indikator"])
        assert result.masuk_antrean is (expected["dipicu"] == "True")


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
