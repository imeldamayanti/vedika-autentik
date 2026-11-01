"""HTTP boundary for Kontrak B2 (answer reader) and the voice agent."""

import secrets
import sys
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from . import config
from .answer_reader import AnswerReader, AnswerResponse, ReadAnswerRequest
from .errors import ServiceError
from .gemini import GeminiError, GeminiTransport
from .schemas import ErrorResponse, HealthResponse
from .voice import GeminiTokenIssuer, VoiceContext, VoiceTokenResponse


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
    description="Stateless answer reader and voice-agent support for Vedika Autentik.",
)


@lru_cache(maxsize=1)
def get_answer_reader() -> AnswerReader:
    api_key = config.gemini_api_key()
    if not api_key:
        raise ServiceError(
            503,
            "gemini_tidak_dikonfigurasi",
            "Pembaca jawaban belum dikonfigurasi.",
        )
    return AnswerReader(
        GeminiTransport(
            api_key, config.gemini_text_model(), timeout=config.READER_TIMEOUT_SECONDS
        )
    )


@lru_cache(maxsize=1)
def get_token_issuer() -> GeminiTokenIssuer:
    api_key = config.gemini_api_key()
    if not api_key:
        raise ServiceError(
            503,
            "gemini_tidak_dikonfigurasi",
            "Agen suara belum dikonfigurasi.",
        )
    return GeminiTokenIssuer(api_key, config.gemini_live_model())


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
        raise ServiceError(401, "kunci_salah", "Header X-Kunci-Layanan kosong atau salah.")


router = APIRouter(prefix="/v1", dependencies=[Depends(require_service_key)])


@router.get("/kesehatan", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        versi_mesin=config.ENGINE_VERSION,
        versi_pembaca=config.READER_VERSION,
        pembaca_siap=bool(config.gemini_api_key()),
    )


@router.post(
    "/baca",
    response_model=AnswerResponse,
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
def read_answer(
    request: ReadAnswerRequest,
    reader: Annotated[AnswerReader, Depends(get_answer_reader)],
) -> AnswerResponse:
    answer = reader.read(request)
    return AnswerResponse(**answer.model_dump(), versi_pembaca=config.READER_VERSION)


@router.post("/suara/token", response_model=VoiceTokenResponse)
def voice_token(
    context: VoiceContext,
    issuer: Annotated[GeminiTokenIssuer, Depends(get_token_issuer)],
) -> VoiceTokenResponse:
    try:
        return issuer.issue(context)
    except GeminiError as error:
        raise ServiceError(503, error.code, "Koneksi agen suara belum tersedia.") from error


app.include_router(router)

PACKAGE_WEB_DIR = Path(__file__).resolve().parent / "web"
SOURCE_WEB_DIR = Path(__file__).resolve().parents[2] / "web"
WEB_DIR = PACKAGE_WEB_DIR if PACKAGE_WEB_DIR.is_dir() else SOURCE_WEB_DIR


@app.get("/voice/", include_in_schema=False)
def voice_console() -> FileResponse:
    return FileResponse(WEB_DIR / "voice-console.html")


app.mount("/voice", StaticFiles(directory=WEB_DIR), name="voice-assets")
