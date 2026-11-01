"""Strict transcript extraction shape and auditable PRD v3 label rules."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CallStatus = Literal["terjawab", "tidak_terhubung", "menolak"]
RecipientType = Literal["peserta", "keluarga"]
Relationship = Literal["anak", "orang tua", "pasangan"]
Confidence = Literal["tinggi", "rendah"]
DangerFlag = Literal[
    "tanda_tangan_tanpa_layanan",
    "diminta_membayar",
    "layanan_berbeda",
]
AnswerLabel = Literal["Tidak terhubung", "Menolak", "Tidak sesuai", "Tidak yakin", "Sesuai"]
SuggestedAction = Literal["Pantau. Tidak dihitung.", "Minta klarifikasi RS", "Tutup kasus"]


class JawabanTerstruktur(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status_panggilan: CallStatus
    penerima: RecipientType | None
    hubungan: Relationship | None
    hadir: bool | None
    jumlah_min: int | None = Field(ge=0)
    jumlah_maks: int | None = Field(ge=0)
    keyakinan: Confidence | None
    tanda_bahaya: list[DangerFlag]
    membantah_tanggal_libur: bool | None
    kutipan_kunci: str = Field(max_length=2000)
    ringkasan: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_quantity_range(self) -> "JawabanTerstruktur":
        if (self.jumlah_min is None) != (self.jumlah_maks is None):
            raise ValueError("jumlah_min dan jumlah_maks harus diisi bersama-sama")
        if (
            self.jumlah_min is not None
            and self.jumlah_maks is not None
            and self.jumlah_min > self.jumlah_maks
        ):
            raise ValueError("jumlah_min tidak boleh melebihi jumlah_maks")
        return self


class AnswerDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: AnswerLabel
    langkah_disarankan: SuggestedAction


def classify_answer(answer: JawabanTerstruktur, billed_sessions: int) -> AnswerDecision:
    """Apply the seven PRD rules in order; model output never chooses the label."""

    if billed_sessions < 0:
        raise ValueError("sesi ditagih harus non-negatif")
    if answer.status_panggilan == "tidak_terhubung":
        return AnswerDecision(
            label="Tidak terhubung", langkah_disarankan="Pantau. Tidak dihitung."
        )
    if answer.status_panggilan == "menolak":
        return AnswerDecision(label="Menolak", langkah_disarankan="Pantau. Tidak dihitung.")
    if answer.hadir is False:
        return AnswerDecision(
            label="Tidak sesuai", langkah_disarankan="Minta klarifikasi RS"
        )
    if answer.tanda_bahaya:
        return AnswerDecision(
            label="Tidak sesuai", langkah_disarankan="Minta klarifikasi RS"
        )
    if answer.jumlah_maks is None or answer.keyakinan == "rendah":
        return AnswerDecision(
            label="Tidak yakin", langkah_disarankan="Pantau. Tidak dihitung."
        )
    if billed_sessions - answer.jumlah_maks > 2:
        return AnswerDecision(
            label="Tidak sesuai", langkah_disarankan="Minta klarifikasi RS"
        )
    return AnswerDecision(label="Sesuai", langkah_disarankan="Tutup kasus")

