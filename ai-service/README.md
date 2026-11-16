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

## Offline ML pipeline (`vedika_ai.ml`)

Everything that reads the raw sample lives in `src/vedika_ai/ml/`; the voice service never imports it.

| Module | Role |
|---|---|
| `privacy.py` | Export rules: minimum cell count, identifier guard, JSON/CSV writers |
| `cohort.py` | Raw FKRTL visits to participant-months (plus secondary diagnosis and age) |
| `claim_reference.py`, `pattern_reference.py` | `rehab-2024` and `pola-2024` aggregates |
| `anomaly_model.py`, `anomaly_evaluation.py` | Train and evaluate `anomali-v2` |
| `tools.py` | Loads the stdlib scorers in `data-uji-konfirmasi/tools` (`pola.py`, `anomali.py`) |

| Script | Output |
|---|---|
| `prepare_claim_reference.py`, `prepare_pattern_reference.py` | `data/reference/rehab-2024`, `data/reference/pola-2024` |
| `check_pattern_real_data.py`, `train_pattern_model.py` | `pola-v1` behaviour and model |
| `train_anomaly_model.py`, `compare_anomaly_models.py` | `anomali-v2` model, evaluation, and comparison with v1 |

Full commands for the anomaly model: `../docs/rencana-v3-skor-pola/MODEL-ANOMALI.md` (section 15).

## Endpoints

| Endpoint | Behavior |
|---|---|
| `GET /v1/kesehatan` | `{"status": "ok"}` plus versions and whether the reader is configured |
| `POST /v1/baca` | Kontrak B2: transcript in, structured answer plus `versi_pembaca` out; no label |
| `POST /v1/suara/token` | Takes the B1 `skrip`; returns a one-use Gemini Live credential and call prompt |
| `/v1/saluran/*` | Phone helper, station laptop only (`SALURAN_ADB=1` or `palsu`); see "Line station" below |

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

Deployed at `https://vedika-ai.sfatimaple.workers.dev` (2026-11-01; `uji.py jawaban`
7/7 against the live URL). `AI_SERVICE_KEY` is required on every `/v1/*` call. Clients
must send a normal `User-Agent`: Cloudflare answers bare `Python-urllib` with
`403 error code: 1010` (the backend's `httpx` client is fine).

Point the backend at it with `MESIN_URL=https://vedika-ai.<account>.workers.dev`
The Worker serves the reader and the token endpoint. It does not include the Phone
helper, so the agent page it hosts only shows "Halaman ini hanya berjalan di laptop
stasiun"; calls are placed from the station laptop's local ai-service.

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

### Line station (Kontrak B1)

Calls are placed automatically by a line station: an Android phone with an Indonesian
SIM, driven over ADB by this service's Phone helper, with the agent page running Gemini
Live in a dedicated Chrome window. Officers only use the website. Setup, env vars,
Meta WhatsApp, and troubleshooting: `../docs/rencana-v3-otomatis/STASIUN.md`.
Real-phone checklist: `../docs/rencana-v3-otomatis/UJI-HP.md`.

```bash
./stasiun.sh        # from the repo root: checks the phone, starts everything, opens the station page
```

**Phone helper** (`src/vedika_ai/saluran.py`). Mounted only when `SALURAN_ADB` is `1`
(real adb) or `palsu` (in-memory fake phone for tests and e2e); otherwise the routes
return 404. No `X-Kunci-Layanan`; every route answers only `127.0.0.1` / `::1`
(`403 bukan_lokal`), because `/konfigurasi` hands the station browser its keys. Phone
numbers are never logged.

| Endpoint | Behavior |
|---|---|
| `GET /v1/saluran/kesehatan` | `{siap, alasan, perangkat, sim, panggilan}`: one authorised device, SIM `READY`, call state idle |
| `POST /v1/saluran/panggil {"nomor"}` | `am start -a android.intent.action.CALL`; `422 nomor_tidak_valid`, `502 adb_gagal` |
| `POST /v1/saluran/tutup` | `input keyevent KEYCODE_ENDCALL`; idempotent |
| `GET /v1/saluran/status` | `{panggilan: idle \| offhook \| ringing}` from every `mCallState` in `dumpsys telephony.registry` |
| `GET /v1/saluran/konfigurasi` | Backend URL, agent key, service key, audio mode, device label hints |
| `POST /v1/saluran/palsu/tutup-penerima` | `palsu` only: the remote party hangs up |

**Station page** (`/voice/?mulai=1`, `web/voice-console.html` + `web/voice-agent.mjs`).
No inputs; it reads `/v1/saluran/konfigurasi` and then, every 3 seconds:

1. reads `/v1/saluran/kesehatan` and posts it to the backend as `POST /api/v1/agen/detak`
   (the heartbeat keeps running during a call);
2. when ready, claims a task with `POST /api/v1/agen/ambil`. The backend has already
   sent the WhatsApp notice (`wa.dikirim_server`), so the page sends nothing;
3. reports `menelepon`, retrying each second on `409 jeda_belum_lewat`, and only then
   dials through the helper;
4. starts Gemini Live with the task's `skrip` and listens. The call counts as answered
   when the recipient's first **completed turn** is not a carrier announcement
   (`isOperatorAnnouncement`): it then reports `tersambung` and `merekam`. An
   announcement, no accepted turn within 40 seconds, or the line going idle first
   reports `tidak_diangkat`;
5. posts one `…/transkrip` line per speaking turn (`detik` from the answer);
6. hangs up 3 seconds after the AI's closing line (`isClosingLine`) has finished
   playing, after 10 silent seconds following an AI turn, when the recipient hangs up
   (helper status `idle`), or at the 150-second cap, then uploads the recording,
   transcript, and `durasi` to `…/hasil`;
7. stops quietly when any report gets `404` or `409 urutan_salah` /
   `bukan_berlangsung`: the officer cancelled or the backend released the call.

The page never sends a label, always releases the line (`/v1/saluran/tutup`), and
one task's error never stops the loop.

Audio mode comes from `SALURAN_AUDIO`: `speaker` (default; phone on speakerphone,
Chrome echo cancellation, noise suppression, and auto-gain on) or `kabel` (USB audio
interface, processing off). Chrome must be started with
`--autoplay-policy=no-user-gesture-required` (done by `stasiun.sh`); otherwise the page
shows "Chrome memblokir audio; jalankan lewat stasiun.sh" and claims nothing.

### Automated call without a phone

`scripts/agent_e2e.mjs` runs one call through the real station page in a throwaway
Chrome profile, real BlackHole routing, real Gemini Live, and the fake phone. A robot
replaces the recipient: it listens on BlackHole 16ch and speaks into BlackHole 2ch.

```bash
SALURAN_ADB=palsu SALURAN_AUDIO=kabel SALURAN_INPUT="BlackHole 2ch" SALURAN_OUTPUT="BlackHole 16ch" \
  SALURAN_AGEN_KEY="$(grep '^AGEN_KEY=' backend/.env | cut -d= -f2-)" ./dev.sh   # from the repo root
node scripts/agent_e2e.mjs S1           # answered call; label must match expected_label
node scripts/agent_e2e.mjs S5           # two unanswered attempts, fallback chat, tidak_terhubung
node scripts/agent_e2e.mjs pengumuman   # carrier announcement: never tersambung, attempt 2 scheduled
```

Each run needs the call in `antre` with no attempts; press "Mulai ulang demo" first.
The script turns automatic mode off while it runs so only its own call is dialled.

### Archived: WhatsApp Web calls

The earlier setup (WhatsApp Web as the line, BlackHole between two Chrome tabs, an operator
clicking through each step) was replaced by the line station; see git history before 2026-11-16.

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
