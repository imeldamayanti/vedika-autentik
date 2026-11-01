"""Typed Contract B response and context models."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CheckType = Literal[
    "kualitas_scan",
    "kecocokan_klaim",
    "berkas_kembar",
    "copy_paste",
    "tempelan",
    "suntingan",
    "tanda_ai",
]
SignalStrength = Literal["kuat", "sedang", "lemah", "info"]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
Region = tuple[NonNegativeInt, NonNegativeInt, PositiveInt, PositiveInt]
PageSize = tuple[PositiveInt, PositiveInt]


class ClaimContext(BaseModel):
    """Subset of claim data the analysis pipeline may use."""

    model_config = ConfigDict(extra="ignore")

    sep: str | None = None
    sesi_ditagih: int | None = Field(default=None, ge=0)
    periode: str | None = None
    kode_faskes: str | None = None


class ScanQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["baik", "scan_ulang"]
    catatan: str
    ketajaman: float | None = Field(default=None, ge=0, le=1)
    miring_derajat: float | None = None
    kecerahan: float | None = Field(default=None, ge=0, le=1)
    kontras: float | None = Field(default=None, ge=0)
    rasio_aspek: float | None = Field(default=None, gt=0)
    perspektif_dikoreksi: bool = False


class DocumentContent(BaseModel):
    model_config = ConfigDict(extra="allow")

    nama: str | None = None
    tanggal_lahir: str | None = None
    no_rm: str | None = None
    no_kartu: str | None = None
    no_sep: str | None = None
    diagnosis: str | None = None
    icd10: str | None = None
    dpjp: str | None = None
    periode: str | None = None
    baris_terisi: int | None = Field(default=None, ge=0)
    baris_asli: int | None = Field(default=None, ge=0)
    tanggal_sesi: list[str] = Field(default_factory=list)
    jumlah_kunjungan_tertulis: int | None = Field(default=None, ge=0)
    kemiripan_ttd_rerata: float | None = Field(default=None, ge=0, le=1)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cek: CheckType
    kekuatan: SignalStrength
    kalimat: str = Field(min_length=1)
    region: Region | None = None
    area: list[Region] | None = None
    skor: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_signal_strength(self) -> "Finding":
        if self.cek == "tanda_ai" and self.kekuatan == "kuat":
            raise ValueError("tanda_ai tidak boleh menjadi sinyal kuat")
        return self


class Fingerprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algoritma: str = Field(min_length=1)
    halaman: str = Field(min_length=1)
    baris: list[str] = Field(default_factory=list)
    teks: str = Field(min_length=1)
    versi_fingerprint: str | None = None


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    versi_mesin: str
    ukuran: PageSize
    halaman_jpg: str | None
    kualitas_scan: ScanQuality
    isi_lembar: DocumentContent
    temuan: list[Finding]
    metadata_file: dict[str, str | int | float | bool | None]
    sidik_jari: Fingerprint
    waktu_proses_ms: int = Field(ge=0)
    template_id: str | None = None
    versi_template: str | None = None

    @model_validator(mode="after")
    def validate_single_document_findings(self) -> "AnalysisResponse":
        pair_only = {"berkas_kembar", "tempelan"}
        if any(finding.cek in pair_only for finding in self.temuan):
            raise ValueError("analisis satu berkas tidak boleh mengirim temuan pasangan")
        if self.kualitas_scan.status == "scan_ulang" and any(
            finding.cek != "kualitas_scan" for finding in self.temuan
        ):
            raise ValueError("scan_ulang tidak boleh memiliki temuan keaslian")
        return self


class PastedRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bagian: str
    region_a: Region
    region_b: Region
    kemiripan: float = Field(ge=0, le=1)


class ComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kemiripan: float = Field(ge=0, le=1)
    sama: bool
    kalimat: str = Field(min_length=1)
    region_a: list[Region] = Field(default_factory=list)
    region_b: list[Region] = Field(default_factory=list)
    tempelan: list[PastedRegion] = Field(default_factory=list)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    versi_mesin: str
    model: list[str]
    siap_analisis: bool


class ErrorDetail(BaseModel):
    kode: str
    pesan: str


class ErrorResponse(BaseModel):
    galat: ErrorDetail
