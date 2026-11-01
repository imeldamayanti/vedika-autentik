"""Kontrak B2 transcript-to-JSON extraction. The backend owns retries and labels."""

from datetime import date
from typing import Literal, Protocol

from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from .answers import JawabanTerstruktur
from .errors import ServiceError
from .gemini import GeminiError


class StructuredGenerator(Protocol):
    def generate_json(self, prompt: str, schema: dict) -> str: ...


class TranscriptTurn(BaseModel):
    detik: float = Field(ge=0)
    pembicara: Literal["ai", "penerima"]
    teks: str = Field(max_length=2000)


class ReadContext(BaseModel):
    sesi_ditagih: int | None = Field(default=None, ge=0)
    tanggal_libur: list[date] = Field(default_factory=list)
    nama_pasien: str | None = None
    bulan: str | None = None


class ReadAnswerRequest(BaseModel):
    id: str | None = None
    transkrip: list[TranscriptTurn]
    konteks: ReadContext = Field(default_factory=ReadContext)


class AnswerResponse(JawabanTerstruktur):
    versi_pembaca: str


def _build_prompt(request: ReadAnswerRequest) -> str:
    transcript = "\n".join(
        f"{turn.pembicara}: {turn.teks}" for turn in request.transkrip if turn.teks.strip()
    )
    context = request.konteks
    holidays = ", ".join(item.isoformat() for item in context.tanggal_libur) or "tidak ada"
    return (
        "Ekstrak percakapan konfirmasi fisioterapi berikut ke JSON sesuai skema. "
        "Jangan menebak. Gunakan null untuk jumlah yang tidak disebut. "
        "Keyakinan rendah jika penerima ragu atau tidak ingat. Kutipan harus berasal dari "
        "transkrip. Tanda bahaya hanya boleh memakai enum pada skema. "
        "status_panggilan menolak bila penerima menolak menjawab pertanyaan konfirmasi "
        "atau minta berhenti, tidak_terhubung bila tidak ada percakapan dengan penerima, "
        "selain itu terjawab. "
        "hubungan diisi anak, orang tua, atau pasangan bila penerima keluarga, selain itu null. "
        "membantah_tanggal_libur true bila penerima menyangkal terapi pada tanggal libur, "
        "false bila membenarkan, null bila tidak dibahas.\n\n"
        f"Pasien: {context.nama_pasien or '-'}\n"
        f"Bulan layanan: {context.bulan or '-'}\n"
        f"Tanggal libur yang ditanyakan: {holidays}\n\n"
        f"TRANSKRIP:\n{transcript}"
    )


class AnswerReader:
    def __init__(self, generator: StructuredGenerator):
        self.generator = generator

    def read(self, request: ReadAnswerRequest) -> JawabanTerstruktur:
        if not any(turn.teks.strip() for turn in request.transkrip):
            raise ServiceError(422, "transkrip_kosong", "Transkrip kosong tidak dapat dibaca.")

        try:
            raw = self.generator.generate_json(
                _build_prompt(request), JawabanTerstruktur.model_json_schema()
            )
            answer = JawabanTerstruktur.model_validate_json(raw)
        except GeminiError as error:
            logger.warning(
                "answer_extraction_failed code={code} status={status}",
                code=error.code,
                status=error.status_code,
            )
            if error.code == "batas_waktu":
                raise ServiceError(
                    504, "batas_waktu", "Pembaca jawaban melewati batas waktu."
                ) from error
            raise ServiceError(502, "llm_gagal", "Pembaca jawaban gagal.") from error
        except ValidationError as error:
            logger.warning("answer_extraction_failed code=ekstraksi_tidak_valid")
            raise ServiceError(502, "llm_gagal", "Keluaran pembaca tidak sesuai skema.") from error

        if not request.konteks.tanggal_libur:
            answer = answer.model_copy(update={"membantah_tanggal_libur": None})
        return answer
