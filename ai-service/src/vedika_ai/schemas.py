"""Shared health and error response models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    versi_mesin: str
    versi_pembaca: str
    pembaca_siap: bool


class ErrorDetail(BaseModel):
    kode: str
    pesan: str


class ErrorResponse(BaseModel):
    galat: ErrorDetail
