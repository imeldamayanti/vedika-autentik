# Vedika AI Service

Stateless PRAMANA document-analysis service for Vedika Autentik. It implements
Contract B between `backend/` and `ai-service/`.

Version 0.5 provides the typed contract, perspective-aware canonical rendering,
scan-quality gating, conservative field/session extraction, claim consistency,
repeated-region checks, robust masked fingerprints, pairwise duplicate
confirmation, and metadata/template-integrity signals. The existing
`backend/stub_mesin` remains available as a demo fallback.

## Development

```bash
cd ai-service
uv sync
uv run pytest
uv run ruff check .
uv run python scripts/evaluate.py --check
uv run uvicorn vedika_ai.main:app --reload --port 8001
```

Open <http://localhost:8001/docs> for the generated OpenAPI contract.

Use `--skip-ocr` only for a faster vision-only regression run.

Set `AI_SERVICE_KEY` to require the `X-Kunci-Layanan` request header. Local
development permits requests without a key when the variable is empty.

## Endpoints

| Endpoint | Behavior |
|---|---|
| `GET /v1/kesehatan` | Returns service and OCR readiness |
| `POST /v1/analisis` | Runs the single-document evidence pipeline |
| `POST /v1/bandingkan` | Confirms a duplicate candidate and shared regions |

The baseline deployment is CPU-only. Tesseract 5 is the current OCR adapter;
PaddleOCR remains a benchmark candidate and is not a runtime dependency.

OCR fields are nullable by design. A low-confidence handwritten value is omitted
instead of guessed. The reproducible evaluator reports both coverage and accuracy
for returned values.

## Logging

Logs contain request IDs, route, status, duration, and error codes only. Do not
log filenames, claim fields, OCR text, images, or uploaded bytes.
