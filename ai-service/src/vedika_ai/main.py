"""HTTP boundary for Contract B."""

import json
import secrets
import sys
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from . import config
from .errors import ServiceError
from .pipeline import AnalysisPipeline
from .schemas import (
    AnalysisResponse,
    ClaimContext,
    ComparisonResponse,
    ErrorResponse,
    HealthResponse,
)


def configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=config.log_level(),
        serialize=config.json_logs(),
        backtrace=False,
        diagnose=False,
    )


configure_logging()

app = FastAPI(
    title="PRAMANA AI Service",
    version=config.ENGINE_VERSION,
    description="Stateless document-evidence engine for Vedika Autentik.",
)


@lru_cache(maxsize=1)
def get_pipeline() -> AnalysisPipeline:
    return AnalysisPipeline()


@app.exception_handler(ServiceError)
async def handle_service_error(_: Request, error: ServiceError) -> JSONResponse:
    logger.warning(
        "request_rejected code={code} status={status}",
        code=error.code,
        status=error.status,
    )
    return JSONResponse(
        status_code=error.status,
        content=ErrorResponse(galat={"kode": error.code, "pesan": error.message}).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
    logger.warning("request_rejected code=validasi status=422")
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            galat={"kode": "validasi", "pesan": "Permintaan tidak valid."}
        ).model_dump(),
    )


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    with logger.contextualize(request_id=request_id, method=request.method, path=request.url.path):
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000)
        logger.info(
            "request_completed status={status} duration_ms={duration_ms}",
            status=response.status_code,
            duration_ms=duration_ms,
        )
    response.headers["X-Request-ID"] = request_id
    return response


def require_service_key(
    supplied: Annotated[str | None, Header(alias="X-Kunci-Layanan")] = None,
) -> None:
    expected = config.service_key()
    if expected and (supplied is None or not secrets.compare_digest(supplied, expected)):
        raise ServiceError(401, "kunci_layanan_tidak_valid", "Kunci layanan tidak valid.")


router = APIRouter(prefix="/v1", dependencies=[Depends(require_service_key)])


async def read_upload(file: UploadFile) -> bytes:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in config.ALLOWED_EXTENSIONS:
        raise ServiceError(415, "format_tidak_didukung", "Hanya PDF, JPG, atau PNG yang diterima.")
    content = await file.read(config.MAX_FILE_BYTES + 1)
    if len(content) > config.MAX_FILE_BYTES:
        raise ServiceError(413, "terlalu_besar", "Ukuran berkas maksimal 10 MB.")
    if not content:
        raise ServiceError(422, "tidak_terbaca", "Berkas kosong atau tidak dapat dibaca.")
    return content


def parse_claim(raw_claim: str) -> ClaimContext:
    try:
        value = json.loads(raw_claim)
        if not isinstance(value, dict):
            raise ValueError
        return ClaimContext.model_validate(value)
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        raise ServiceError(422, "klaim_tidak_valid", "Konteks klaim tidak valid.") from error


@router.get("/kesehatan", response_model=HealthResponse)
def health(pipeline: Annotated[AnalysisPipeline, Depends(get_pipeline)]) -> HealthResponse:
    return HealthResponse(
        status="ok",
        versi_mesin=config.ENGINE_VERSION,
        model=pipeline.models,
        siap_analisis=pipeline.ready,
    )


@router.post(
    "/analisis",
    response_model=AnalysisResponse,
    responses={
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def analyze(
    file: Annotated[UploadFile, File(...)],
    pipeline: Annotated[AnalysisPipeline, Depends(get_pipeline)],
    klaim: Annotated[str, Form()] = "{}",
    template: Annotated[str, Form()] = "",
) -> AnalysisResponse:
    content = await read_upload(file)
    claim = parse_claim(klaim)
    return await run_in_threadpool(
        pipeline.analyze,
        content,
        file.filename or "berkas",
        claim,
        template,
    )


@router.post(
    "/bandingkan",
    response_model=ComparisonResponse,
    responses={
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def compare(
    file_a: Annotated[UploadFile, File(...)],
    file_b: Annotated[UploadFile, File(...)],
    pipeline: Annotated[AnalysisPipeline, Depends(get_pipeline)],
) -> ComparisonResponse:
    content_a = await read_upload(file_a)
    content_b = await read_upload(file_b)
    return await run_in_threadpool(
        pipeline.compare,
        content_a,
        file_a.filename or "berkas-a",
        content_b,
        file_b.filename or "berkas-b",
    )


app.include_router(router)
