"""Export the Python reference behaviour that the Cloudflare Worker must reproduce.

Writes worker/src/answer-schema.json (used at runtime) and worker/test/parity.json
(used by `bun test`). Rerun after changing the prompt, call script, or answer schema.
"""

import json
from pathlib import Path

from pydantic import ValidationError

from vedika_ai import config
from vedika_ai.answer_reader import ReadAnswerRequest, _build_prompt
from vedika_ai.answers import JawabanTerstruktur
from vedika_ai.voice import VoiceContext, build_voice_instruction

WORKER = Path(__file__).resolve().parents[1] / "worker"

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
    "kutipan_kunci": "Tiga kali.",
    "ringkasan": "Peserta hadir tiga kali.",
}
ANSWERS = [
    VALID,
    {**VALID, "penerima": "keluarga", "hubungan": "orang tua"},
    {**VALID, "jumlah_min": None, "jumlah_maks": None, "keyakinan": "rendah", "hadir": None},
    {**VALID, "tanda_bahaya": ["diminta_membayar", "layanan_berbeda"]},
    {**VALID, "status_panggilan": "selesai"},
    {**VALID, "hubungan": "tetangga"},
    {**VALID, "jumlah_min": True, "jumlah_maks": True},
    {**VALID, "jumlah_min": -1, "jumlah_maks": 3},
    {**VALID, "jumlah_min": 4, "jumlah_maks": 3},
    {**VALID, "jumlah_min": 3, "jumlah_maks": None},
    {**VALID, "membantah_tanggal_libur": "false"},
    {**VALID, "tanda_bahaya": ["dugaan_umum"]},
    {**VALID, "ringkasan": ""},
    {**VALID, "kutipan_kunci": "x" * 2001},
    {**VALID, "label": "Sesuai"},
    {key: value for key, value in VALID.items() if key != "hubungan"},
    {key: value for key, value in VALID.items() if key != "tanda_bahaya"},
]
REQUESTS = [
    {
        "id": "CALL-P-S1-2026-08",
        "transkrip": [
            {"detik": 0, "pembicara": "ai", "teks": "Berapa kali datang terapi?"},
            {"detik": 6, "pembicara": "penerima", "teks": "Tiga kali."},
            {"detik": 9, "pembicara": "penerima", "teks": "  "},
        ],
        "konteks": {
            "sesi_ditagih": 11,
            "tanggal_libur": ["2026-08-16", "2026-08-17"],
            "nama_pasien": "Andi Pratama",
            "bulan": "2026-08",
        },
    },
    {"transkrip": [{"detik": 1.5, "pembicara": "penerima", "teks": "Halo?"}]},
]
CONTEXTS = [
    {
        "nama_penerima": "Andi Pratama", "sapaan_penerima": "Bapak", "hubungan": "peserta",
        "nama_pasien": "Andi Pratama", "sapaan_pasien": "Bapak", "nama_rs": "RS Melati Sehat",
        "bulan": "Agustus", "tanggal_libur": ["16 Agustus", "17 Agustus"],
    },
    {
        "nama_penerima": "Dewi Rahmawati", "sapaan_penerima": "Bapak/Ibu", "hubungan": "anak",
        "nama_pasien": "Siti Rahmawati", "sapaan_pasien": "Ibu", "nama_rs": "RS Melati Sehat",
        "bulan": "Agustus", "tanggal_libur": ["23 Agustus"],
    },
    {
        "nama_penerima": "Slamet Riyadi", "sapaan_penerima": "Bapak", "hubungan": "peserta",
        "nama_pasien": "Slamet Riyadi", "sapaan_pasien": "Bapak", "nama_rs": "RS Kenanga Medika",
        "bulan": "Agustus", "tanggal_libur": [],
    },
    {
        "nama_penerima": "Ani", "sapaan_penerima": "Ibu", "hubungan": "peserta",
        "nama_pasien": "Ani", "sapaan_pasien": "Ibu", "nama_rs": "RS Cempaka Asri",
        "bulan": "Agustus", "tanggal_libur": ["31 Agustus", "1 September", "Natal"],
    },
]


def accepted(answer: dict) -> bool:
    try:
        JawabanTerstruktur.model_validate_json(json.dumps(answer))
    except ValidationError:
        return False
    return True


def main() -> None:
    schema = JawabanTerstruktur.model_json_schema()
    (WORKER / "src" / "answer-schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    parity = {
        "engine_version": config.ENGINE_VERSION,
        "reader_version": config.READER_VERSION,
        "prompts": [
            {"request": r, "prompt": _build_prompt(ReadAnswerRequest.model_validate(r))}
            for r in REQUESTS
        ],
        "instructions": [
            {"context": c, "instruction": build_voice_instruction(VoiceContext.model_validate(c))}
            for c in CONTEXTS
        ],
        "answers": [{"answer": a, "valid": accepted(a)} for a in ANSWERS],
    }
    (WORKER / "test" / "parity.json").write_text(
        json.dumps(parity, indent=2, ensure_ascii=False) + "\n"
    )


if __name__ == "__main__":
    main()
