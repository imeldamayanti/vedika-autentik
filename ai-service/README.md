# Vedika AI Service

Stateless AI service for Vedika Autentik v3 voice confirmation. It implements
Kontrak B2 (`POST /v1/baca`) and serves the browser voice agent for Kontrak B1
(`../docs/api-contract-v3.md`). The backend owns the queue, retries, labels
(`data-uji-konfirmasi/tools/aturan.py`), and retention; this service only reads
transcripts and runs the call. `backend/stub_mesin` remains the demo fallback.

The v2 document engine (`/v1/analisis`, `/v1/bandingkan`, OCR) was removed; the
v3 PRD discontinued document detection. It remains in git history.

## Development

```bash
cd ai-service
uv sync
uv run pytest
uv run ruff check .
node --test web/voice-agent.test.mjs
uv run uvicorn vedika_ai.main:app --reload --port 8001
```

Open <http://localhost:8001/docs> for the generated OpenAPI contract.

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
| `GET /v1/kesehatan` | `{"status": "ok"}` plus versions and whether the reader is configured |
| `POST /v1/baca` | Kontrak B2: transcript in, structured answer plus `versi_pembaca` out; no label |
| `POST /v1/suara/token` | Takes the B1 `skrip`; returns a one-use Gemini Live credential and call prompt |

## Cloudflare Worker (deployment)

`worker/` is the deployable version of the voice parts: `GET /v1/kesehatan`,
`POST /v1/baca`, `POST /v1/suara/token`, and the agent page at `/voice/`. It is a
JavaScript port of this service; Python stays the reference.
`scripts/export_worker_fixtures.py` writes the answer schema and parity fixtures
(reader prompt, call scripts, answer validation) that `bun test` checks the Worker
against. Rerun it after changing the prompt, call script, or answer schema.

```bash
cd ai-service/worker
bun install
bun test                      # parity + contract tests
bun run dev                   # local, needs .dev.vars with GEMINI_API_KEY
bunx wrangler login           # once
bun run deploy
bunx wrangler secret put GEMINI_API_KEY
bunx wrangler secret put AI_SERVICE_KEY   # same value as KUNCI_MESIN in backend/.env
```

Point the backend at it with `MESIN_URL=https://vedika-ai.<account>.workers.dev`
and add that origin to `CORS_ORIGINS` so the hosted agent page can reach the API.
On the agent page, enter the same `AI_SERVICE_KEY` under **Kunci layanan**.

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
4. starts Gemini Live with the task's `skrip` as soon as the operator dials and
   listens on the line. The recipient's first transcribed words count as the
   answer: it reports `tersambung` and `merekam` and the AI opens the call. No words
   within 40 seconds (ringback does not count) reports `tidak_diangkat` and sends
   `chat_cadangan` when offered;
5. posts one `…/transkrip` line per speaking turn (`detik` from connection,
   `pembicara` `ai` or `penerima`);
6. uploads the two-way `.webm`, final transcript, and `durasi` to `…/hasil`.

The page never sends a label and always ends a call with `hasil` or
`tidak_diangkat`, because an unfinished call holds the backend queue.

### Automated call without WhatsApp

`scripts/agent_e2e.mjs` runs one scenario through the real agent page in a throwaway
Chrome profile, real BlackHole routing, and real Gemini Live. A phone robot replaces
WhatsApp and the recipient: it listens on BlackHole 16ch and speaks the recipient's
lines from `data-uji-konfirmasi/transkrip_uji/<S>.txt` into BlackHole 2ch.

```bash
./dev.sh                          # in another terminal, from the repo root
node scripts/agent_e2e.mjs S1     # stop any other agent page first
```

It exits 0 when the backend label matches the scenario's `expected_label`. The call
must be `antre`; press "Mulai ulang demo" to reset the shared demo.

### Real call setup (WhatsApp Web)

Use WhatsApp **Web** in Chrome as the phone line. WhatsApp Desktop for Mac always
uses the built-in microphone and speakers for calls and ignores BlackHole, even as
the system default.

```text
Tab 1: WhatsApp Web (the line)                Tab 2: agent page /voice/ (the AI)
  mic     = BlackHole 16ch  <---- AI voice ----  output = BlackHole 16ch
  speaker = BlackHole 2ch   --- recipient ---->  input  = BlackHole 2ch
```

1. Install `blackhole-2ch` and `blackhole-16ch` (`brew install --cask blackhole-2ch blackhole-16ch`).
2. Turn off Continuity Camera (or the iPhone's Bluetooth) so macOS does not offer
   the iPhone as a microphone.
3. Set the Mac's default devices; WhatsApp Web follows them:
   `swift scripts/set_audio.swift "BlackHole 2ch" "BlackHole 16ch"`.
4. Quit WhatsApp Desktop, then open web.whatsapp.com in the same Chrome as the
   agent page and link the calling phone.
5. Run `./dev.sh`, then on the agent page enter `AGEN_KEY`, click **Muat perangkat
   audio**, choose input BlackHole 2ch and output BlackHole 16ch, and click
   **Mulai agen**. Hard-reload (Cmd+Shift+R) after any agent code change.
6. Send the notice and place the voice call from WhatsApp Web, then click
   **Saya menelepon**. The AI starts when the recipient says "Halo"; there is no
   answer button. **Tidak diangkat** ends the attempt early.
7. Afterwards restore the Mac:
   `swift scripts/set_audio.swift "MacBook Pro Speakers" "MacBook Pro Microphone"`.

The agent page captures the line with Chrome's echo cancellation, noise
suppression, and auto-gain disabled; otherwise Chrome erases the recipient's voice
as echo of WhatsApp Web's playback. It creates its audio context at the
**Saya menelepon** click, because Chrome keeps a context created later suspended (silent
in both directions).

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

This checks the structured answer/label contracts for S1-S6 and S8 against the
official data (indicators are computed by the backend with `aturan.py`), without reading the evaluator-only
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
| Official S1-S6/S8 answer and label contracts | Pass (2026-11-01) |
| Live official `uji.py jawaban` (S1-S6/S8) | Pass 7/7, two consecutive runs, `gemini-3.5-flash-lite` (2026-11-01) |
| Live 20-case extraction >=90% | Pass: 115/120 key fields (95.8%), labels 19/20 (2026-11-01) |
| Kontrak B2 through backend `KlienMesin` + `baca_dengan_ulang` | Pass over HTTP: S1/S2/S8 in about 1.2 s, schema valid, labels match; empty transcript not retried |
| Kontrak B1 agent flow against the live backend | Pass for S1 (2026-11-01): `runTask` drove all six status reports, transcript, and `hasil`; backend read it through `/v1/baca` and labelled `tidak_sesuai`; RS Melati became Perlu klarifikasi RS; recording plays. Browser audio and Gemini Live were replayed, not live |
| Gemini Live call with synthetic recipient audio | Pass for S1 (2026-11-01): `gemini-3.8-live` followed script A-F, transcribed the recipient accurately, and the transcript was labelled `Tidak sesuai` |
| Agent page in Chrome + BlackHole + Gemini Live, robot recipient (`agent_e2e.mjs`) | Pass for S1 (2026-11-01): 37 s of AI audio, 4/4 recipient lines transcribed, label `tidak_sesuai` |
| Automatic answer detection (`agent_e2e.mjs`, ringback then "Halo?") | Pass (2026-11-01): S4 answered after 8 s of ringback, label `tidak_yakin`; S5 never answered, two attempts, fallback chat, label `tidak_terhubung`, no AI speech during ringing |
| Real call: WhatsApp Web + BlackHole + agent page | Pass, 1 call (2026-11-01): two-way audio, 5-line transcript, recipient denied August, label `tidak_sesuai`. Three consecutive scripted calls still pending |

`gemini-3.8-flash` was the original text model. On 2026-10-31 and 2026-11-01 it
returned HTTP 503 ("high demand") or took 50 seconds or more, beyond the
backend's 30-second budget. `gemini-3.5-flash-lite` answers in about 1.3 seconds
and passes both gates, so it is the default. Set `GEMINI_TEXT_MODEL` to switch,
then rerun both live commands.

## Logging

Logs contain request IDs, route, status, duration, and error codes only. Do not
log transcripts, names, phone numbers, claim values, or tokens.
