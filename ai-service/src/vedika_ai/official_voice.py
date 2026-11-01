"""Adapters for the repository's official synthetic voice-confirmation fixtures."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .answer_reader import ReadAnswerRequest, ReadContext, TranscriptTurn
from .answers import AnswerLabel, JawabanTerstruktur

KEY_FIELDS = (
    "status_panggilan",
    "penerima",
    "hadir",
    "jumlah_maks",
    "keyakinan",
    "tanda_bahaya",
)
SPEAKERS = {"AI": "ai", "Penerima": "penerima"}


@dataclass(frozen=True, slots=True)
class OfficialVoiceCase:
    id_skenario: str
    request: ReadAnswerRequest
    expected_key_fields: dict[str, Any]
    expected_label: AnswerLabel


def parse_official_transcript(path: Path) -> list[TranscriptTurn]:
    """Parse the fixture's readable speaker lines into the runtime request shape."""

    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if lines and all(line.startswith("(tidak ada transkrip:") for line in lines):
        return []

    turns = []
    for index, line in enumerate(lines):
        if ": " not in line:
            raise ValueError(f"baris transkrip tidak valid: {path.name}")
        speaker, text = line.split(": ", maxsplit=1)
        if speaker not in SPEAKERS:
            raise ValueError(f"pembicara tidak dikenal: {speaker}")
        turns.append(
            TranscriptTurn(
                detik=index,
                pembicara=SPEAKERS[speaker],
                teks=text,
            )
        )
    return turns


def load_official_cases(root: Path) -> list[OfficialVoiceCase]:
    """Load scenarios with expected answers without reading evaluator-only ground truth."""

    scenarios = json.loads((root / "skenario_uji.json").read_text(encoding="utf-8"))
    cases = []
    for scenario in scenarios:
        if scenario.get("expected_jawaban") is None:
            continue
        indicators = scenario["expected_indikator"]
        expected = JawabanTerstruktur.model_validate(scenario["expected_jawaban"])
        expected_values = expected.model_dump(mode="json")
        cases.append(
            OfficialVoiceCase(
                id_skenario=scenario["id_skenario"],
                request=ReadAnswerRequest(
                    id=f"CALL-{scenario['id_peserta']}-{scenario['bulan_layanan']}",
                    transkrip=parse_official_transcript(
                        root / "transkrip_uji" / f"{scenario['id_skenario']}.txt"
                    ),
                    konteks=ReadContext(
                        sesi_ditagih=indicators["sesi_ditagih"],
                        tanggal_libur=indicators["tanggal_libur"],
                        nama_pasien=scenario["nama_peserta"],
                        bulan=scenario["bulan_layanan"],
                    ),
                ),
                expected_key_fields={field: expected_values[field] for field in KEY_FIELDS},
                expected_label=scenario["expected_label"],
            )
        )
    return cases


# S5 never reaches the reader: the backend composes this answer after two unanswered calls.
NOT_CONNECTED_ANSWER = {
    "status_panggilan": "tidak_terhubung",
    "penerima": None,
    "hubungan": None,
    "hadir": None,
    "jumlah_min": None,
    "jumlah_maks": None,
    "keyakinan": None,
    "tanda_bahaya": [],
    "membantah_tanggal_libur": None,
    "kutipan_kunci": "",
    "ringkasan": "Panggilan tidak terhubung.",
}


def read_official_answers(root: Path, reader, *, between_cases=lambda: None) -> list[dict]:
    """Produce `[{id_skenario, jawaban}]` for `data-uji-konfirmasi/tools/uji.py jawaban`."""

    rows = []
    for index, case in enumerate(load_official_cases(root)):
        if index:
            between_cases()
        if case.request.transkrip:
            answer = reader.read(case.request).model_dump(mode="json")
        else:
            answer = NOT_CONNECTED_ANSWER
        rows.append({"id_skenario": case.id_skenario, "jawaban": answer})
    return rows
