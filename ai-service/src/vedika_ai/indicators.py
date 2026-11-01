"""Auditable physiotherapy queue indicators from PRD v3."""

from collections import Counter
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

IndicatorCode = Literal["I1", "I2", "I3", "I4"]


def _parse_month(value: str) -> tuple[int, int]:
    try:
        year_text, month_text = value.split("-", maxsplit=1)
        year, month = int(year_text), int(month_text)
        date(year, month, 1)
    except (TypeError, ValueError) as error:
        raise ValueError("bulan harus berformat YYYY-MM") from error
    if len(year_text) != 4 or len(month_text) != 2:
        raise ValueError("bulan harus berformat YYYY-MM")
    return year, month


def _month_offset(year: int, month: int, offset: int) -> str:
    absolute = year * 12 + month - 1 + offset
    result_year, zero_based_month = divmod(absolute, 12)
    return f"{result_year:04d}-{zero_based_month + 1:02d}"


class ServiceSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tanggal: date
    hari_libur: bool = False


class IndicatorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bulan: str
    sesi: list[ServiceSession] = Field(default_factory=list)
    bulan_aktif: list[str] = Field(default_factory=list)

    @field_validator("bulan")
    @classmethod
    def validate_month(cls, value: str) -> str:
        _parse_month(value)
        return value

    @field_validator("bulan_aktif")
    @classmethod
    def validate_active_months(cls, values: list[str]) -> list[str]:
        for value in values:
            _parse_month(value)
        return values

    @model_validator(mode="after")
    def sessions_belong_to_month(self) -> "IndicatorRequest":
        year, month = _parse_month(self.bulan)
        if any(item.tanggal.year != year or item.tanggal.month != month for item in self.sesi):
            raise ValueError("tanggal sesi harus berada pada bulan yang diminta")
        return self


class IndicatorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    i1: bool
    i2: bool
    i3: bool
    i4: bool
    sesi_ditagih: int = Field(ge=0)
    tanggal_libur: list[date]
    indikator_aktif: list[IndicatorCode]
    masuk_antrean: bool


def calculate_indicators(request: IndicatorRequest) -> IndicatorResult:
    """Calculate I1-I4 in their PRD order for one patient, hospital, and month."""

    session_count = len(request.sesi)
    week_counts = Counter(
        item.tanggal - timedelta(days=item.tanggal.weekday()) for item in request.sesi
    )
    holiday_dates = sorted(
        {
            item.tanggal
            for item in request.sesi
            if item.tanggal.weekday() == 6 or item.hari_libur
        }
    )
    year, month = _parse_month(request.bulan)
    required_months = {_month_offset(year, month, offset) for offset in range(-5, 1)}
    active_months = set(request.bulan_aktif)

    values: dict[IndicatorCode, bool] = {
        "I1": session_count > 8,
        "I2": any(count >= 3 for count in week_counts.values()),
        "I3": required_months <= active_months,
        "I4": bool(holiday_dates),
    }
    active = [code for code, enabled in values.items() if enabled]
    return IndicatorResult(
        i1=values["I1"],
        i2=values["I2"],
        i3=values["I3"],
        i4=values["I4"],
        sesi_ditagih=session_count,
        tanggal_libur=holiday_dates,
        indikator_aktif=active,
        masuk_antrean=len(active) >= 2,
    )

