# Vedika AI Service

Stateless PRAMANA AI service for Vedika Autentik. It implements Contract B
between `backend/` and `ai-service/`.

The v3 voice-confirmation path implements Kontrak B2 (`POST /v1/baca`) and the
browser voice agent for Kontrak B1 in `../docs/api-contract-v3.md`. The backend
owns the queue, retries, labels (`data-uji-konfirmasi/tools/aturan.py`), and
retention; this service only reads transcripts and runs the call. The older document endpoints remain available for
branch compatibility but are outside the v3 product flow.

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

Copy `.env.example` into the environment used by Uvicorn and set
`GEMINI_API_KEY` on the server. Never place that permanent key in browser code.
`GEMINI_LIVE_MODEL` and `GEMINI_TEXT_MODEL` are configurable so a model change
does not require a code change.

## Offline claim reference

Raw BPJS sample data is never a runtime dependency and must stay outside Git. Build the
privacy-safe 2024 physiotherapy reference with the optional `data` dependency group:

```bash
cd ai-service
uv run --group data python scripts/prepare_claim_reference.py \
  --source "../Folder Data Asli/2025 2/Data Sampel Reguler Edisi 2025/data/202403_fkrtl.dta" \
  --output data/reference/rehab-2024 \
  --year 2024
```

The command writes aggregate JSON/CSV files, a data dictionary, and a checksum manifest. It
does not export participant IDs, visit IDs, or row-level claims.

## Endpoints

| Endpoint | Behavior |
|---|---|
| `GET /v1/kesehatan` | Returns service and OCR readiness |
| `POST /v1/analisis` | Runs the single-document evidence pipeline |
| `POST /v1/bandingkan` | Confirms a duplicate candidate and shared regions |
| `POST /v1/baca` | Kontrak B2: transcript in, structured answer plus `versi_pembaca` out; no label |
| `POST /v1/suara/token` | Takes the B1 `skrip`; returns a one-use Gemini Live credential and call prompt |
| `POST /v1/indikator` | I1-I4 reference; unused by the backend, which computes them with `aturan.py` |

## Voice confirmation prototype

### Answer reader (Kontrak B2)

`POST /v1/baca` makes one model attempt within `READER_TIMEOUT_SECONDS` (25 s,
under the backend's 30 s limit). The backend retries once and falls back to
`Tidak yakin`.

| Case | Response |
|---|---|
| Valid answer | `200` with the `data-uji-konfirmasi/README.md` schema plus `versi_pembaca` |
| Empty transcript | `422 transkrip_kosong`; the model is not called |
| Provider error or schema-invalid output | `502 llm_gagal` |
| Provider timeout | `504 batas_waktu` |
| Wrong `X-Kunci-Layanan` | `401 kunci_salah` |

`membantah_tanggal_libur` is forced to `null` when `konteks.tanggal_libur` is
empty. Unknown request fields are ignored.

To replace the backend stub, run this service on port 8001 and set
`MESIN_URL=http://localhost:8001` and `KUNCI_MESIN=<AI_SERVICE_KEY>` in
`backend/.env`.

### Voice agent (Kontrak B1)

The agent page is served at <http://localhost:8001/voice/>. Add
`http://localhost:8001` to the backend's `CORS_ORIGINS`, then enter the backend
URL and `AGEN_KEY` on the page and press **Mulai agen**. The page:

1. polls `POST /api/v1/agen/ambil` every 3 seconds;
2. opens `wa.tautan` and reports `wa_terkirim` after the operator sends it
   (skipped on the second attempt);
3. waits `jeda_wa_menit`, asks the operator to dial, and reports `menelepon`,
   retrying each second on `409 jeda_belum_lewat`;
4. reports `tidak_diangkat` and sends `chat_cadangan` when offered, or reports
   `tersambung`, starts Gemini Live with the task's `skrip`, and reports `merekam`;
5. posts one `…/transkrip` line per speaking turn (`detik` from connection,
   `pembicara` `ai` or `penerima`);
6. uploads the two-way `.webm`, final transcript, and `durasi` to `…/hasil`.

The page never sends a label and always ends a call with `hasil` or
`tidak_diangkat`, because an unfinished call holds the backend queue.

### BlackHole route

1. Install `blackhole-2ch` and `blackhole-16ch` and restart the audio apps.
2. In WhatsApp Desktop, set speaker to BlackHole 2ch and microphone to
   BlackHole 16ch.
3. In Audio MIDI Setup, create a multi-output device that includes BlackHole
   and the operator's speaker if the team needs to monitor the call.
4. Open `/voice/`, select BlackHole 2ch as input and BlackHole 16ch as output,
   and keep the yellow **Simulasi** warning visible.
5. Run three consecutive calls. Confirm clear two-way audio, transcripts,
   interruption handling, and automatic stop at 150 seconds.

### Acceptance commands

```bash
cd ai-service
uv run pytest tests/test_indicators.py tests/test_answers.py tests/test_answer_reader.py tests/test_voice.py tests/test_api.py
node --test web/voice-agent.test.mjs
```

Check the official corpus with the handoff's `uji.py` gate (S5 never reaches
the reader; the script writes the answer the backend composes for it):

```bash
uv run --env-file .env python scripts/read_official.py keluaran.json --interval-seconds 15
python3 ../data-uji-konfirmasi/tools/uji.py jawaban keluaran.json
```

Evaluate the committed 20-case transcript corpus with the live Gemini text model:

```bash
uv run --env-file .env python scripts/evaluate_voice.py \
  tests/fixtures/voice-evaluation-20.json \
  --threshold 0.90 \
  --interval-seconds 15
```

The report contains case IDs and field counts only; it never copies transcript
text into the output. `accuracy` is calculated only from the six PRD key fields;
the deterministic result is reported separately as `label_accuracy` and cannot
inflate the 90% extraction gate. Exit code `0` means the configured threshold
passed, `1` means the model completed below threshold, and `2` means the fixture
or provider was unavailable. Provider failures produce `accuracy: null`; they
are never reported as low model accuracy. The interval keeps the 20-case run
below common development-tier request limits. Evaluation stops at the first
provider failure because a partial run cannot satisfy the acceptance gate.
Transient HTTP failures use four bounded transport attempts. Their exponential
backoff starts at the configured case interval (15, 30, and 60 seconds in the
example), so recovered retries also remain rate-safe. This is separate from the
two-attempt malformed-output safeguard.

The official `data-uji-konfirmasi` corpus is imported at the repository root from
commit `7ca9f91`. Run the service-level acceptance coverage with:

```bash
uv run pytest tests/test_official_voice_fixtures.py
```

This checks all 300 indicator rows and the structured answer/label contracts for
S1-S6 and S8 against the official data, without reading the evaluator-only
`kunci_kebenaran_2026-08.csv` from production code.

Run the official transcript extraction against Gemini only when provider access
is intended. This test is excluded from the normal offline suite:

```bash
set -a
source .env
set +a
RUN_LIVE_GEMINI=1 uv run pytest \
  tests/test_official_voice_live.py \
  -m live_gemini
```

S5 has no conversation transcript and remains an orchestration/status case; the
live extractor gate covers S1-S4, S6, and S8. Its `Tidak terhubung` label remains
covered by the deterministic answer-rule tests.

### Acceptance status

| Gate | Status |
|---|---|
| Offline Python, Ruff, Node suites | Pass (2026-11-01) |
| Official 300-row indicators and S1-S6/S8 contracts | Pass (2026-11-01) |
| Live official `uji.py jawaban` (S1-S6/S8) | Pass 7/7, two consecutive runs, `gemini-3.5-flash-lite` (2026-11-01) |
| Live 20-case extraction >=90% | Pass: 115/120 key fields (95.8%), labels 19/20 (2026-11-01) |
| Kontrak B2 through backend `KlienMesin` + `baca_dengan_ulang` | Pass over HTTP: S1/S2/S8 in about 1.2 s, schema valid, labels match; empty transcript not retried |
| Kontrak B1 agent flow against the live backend | Pass for S1 (2026-11-01): `runTask` drove all six status reports, transcript, and `hasil`; backend read it through `/v1/baca` and labelled `tidak_sesuai`; RS Melati became Perlu klarifikasi RS; recording plays. Browser audio and Gemini Live were replayed, not live |
| Gemini Live + BlackHole + WhatsApp call | Not run (manual) |

`gemini-3.8-flash` was the original text model. On 2026-10-31 and 2026-11-01 it
returned HTTP 503 ("high demand") or took 50 seconds or more, beyond the
backend's 30-second budget. `gemini-3.5-flash-lite` answers in about 1.3 seconds
and passes both gates, so it is the default. Set `GEMINI_TEXT_MODEL` to switch,
then rerun both live commands.

The baseline deployment is CPU-only. Tesseract 5 is the current OCR adapter;
PaddleOCR remains a benchmark candidate and is not a runtime dependency.

OCR fields are nullable by design. A low-confidence handwritten value is omitted
instead of guessed. The reproducible evaluator reports both coverage and accuracy
for returned values.

## Logging

Logs contain request IDs, route, status, duration, and error codes only. Do not
log filenames, claim fields, OCR text, images, or uploaded bytes.
