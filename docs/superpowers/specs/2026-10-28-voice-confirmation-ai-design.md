# Voice Confirmation AI Design

**Date:** 2026-10-28  
**Source:** `/Users/sfatimahazzahra/Downloads/PRD Vedika Autentik v3 - Konfirmasi Suara.docx.md`  
**Scope:** AI engineer deliverables on `feat/ai-service`

## Intent

Replace the v2 document-authenticity product path with a prototype that selects unusual
physiotherapy claims, conducts a short Indonesian voice confirmation, and turns the transcript
into auditable structured evidence. The AI extracts and converses; deterministic code decides
indicators and labels. A human verifier remains responsible for any action against a hospital.

## Goals

- Calculate I1-I4 and the two-indicator queue threshold without a learned model.
- Give the browser a safe, short-lived Gemini Live credential without exposing the permanent key.
- Run the required A-F conversation and seven exception branches in Indonesian.
- Capture timestamped input/output transcript and two-way WebM audio in the browser.
- Extract the R4.1 JSON fields with a strict schema, retry invalid output once, and fail to
  `Tidak yakin` after the second invalid result.
- Calculate the R4.4 label and suggested action with inspectable rules.
- Provide narrow HTTP and JavaScript handoff interfaces for the backend/frontend engineer.

## Non-goals

- Queue scheduling, WhatsApp delivery, call retries, PostgreSQL persistence, retention jobs,
  evidence screens, verifier decisions, or hospital summaries.
- Production telephony, VClaim/Mobile JKN integration, regional-language coverage, training a
  model, generic fraud scoring, or automatic rejection.
- Deleting or refactoring the existing document-analysis implementation during the prototype.
- Implementing an OpenAI Realtime adapter before the Gemini/BlackHole gate fails.

## Constraints

- Preserve all pre-existing uncommitted changes and create no commits during this execution.
- Keep permanent provider credentials server-side; browser sessions use one-use ephemeral tokens.
- The agent never requests NIK, OTP, bank details, or money and never says `curang` or `fraud`.
- One question per turn, sentences at most 20 words, at most three core questions, and a maximum
  call duration of 150 seconds.
- Missing, refusing, uncertain, and unreachable answers are never negative hospital signals.
- The official `data-uji-konfirmasi` corpus at commit `7ca9f91` is required for final acceptance.
  It is imported unchanged in this checkout and is authoritative for field shapes and expected results.

## Approaches considered

### Selected: extend `ai-service` in place

Add focused domain modules and new `/v1` endpoints to the current FastAPI service. Add a small
browser-native ES module for Gemini Live and BlackHole routing. Keep old document endpoints
working but outside the v3 product flow. This reuses deployment, authentication, logging, and
Pydantic conventions without coupling live audio to the backend process.

### Rejected: separate voice microservice

This isolates the prototype but duplicates deployment, configuration, authentication, and
observability for a four-day delivery. The operational boundary is not justified yet.

### Rejected: browser-only rules and extraction

This is quick to demo but makes the audit rules harder to test, exposes more provider behavior
to the client, and weakens the backend handoff.

## Architecture

```text
claim sessions -> POST /v1/indikator -> deterministic I1-I4 + eligible flag

browser voice console
  -> POST /v1/suara/token -> one-use Gemini token
  -> Gemini Live WebSocket <-> BlackHole input/output
  -> timestamped transcript + WebM recording
  -> POST /v1/baca-jawaban
       -> Gemini structured extraction (maximum two attempts)
       -> Pydantic validation
       -> deterministic label and suggested action
       -> structured evidence response
```

## Server interfaces

### `POST /v1/indikator`

Consumes one patient-hospital-month and its service dates. It returns booleans for I1-I4,
Sunday/holiday dates, and `masuk_antrean`. A date is treated as a holiday only when the caller
marks it in `tanggal_libur`; the AI service does not maintain an independent holiday calendar.
This avoids two sources of truth and lets the supplied fixture rules remain authoritative.

I3 receives the months in which the same patient had sessions at the same hospital and is true
only when the current month and previous five calendar months are all present.

### `POST /v1/suara/token`

Consumes the call context needed for prompt interpolation and returns a one-use, short-lived
Gemini Live token, model name, constrained WebSocket URL, system instruction, and 150-second
limit. It rejects requests when `GEMINI_API_KEY` is absent and never returns that key.

### `POST /v1/baca-jawaban`

Consumes the timestamped transcript and billed-session count. A structured Gemini extractor is
called at most twice. Each result must validate as `JawabanTerstruktur`. The response also
contains the deterministic label, suggested action, extraction-attempt count, and a safe error
code when both attempts fail.

## Structured answer

`JawabanTerstruktur` contains exactly the PRD fields:

- `status_panggilan`: `selesai`, `tidak_terhubung`, or `menolak`;
- `penerima`: `peserta`, `keluarga`, or `tidak_diketahui`;
- `hubungan`: normalized free text or null;
- `hadir`: `ya`, `tidak`, or `tidak_yakin`;
- nullable non-negative `jumlah_min` and `jumlah_maks`, with min <= max;
- `keyakinan`: `tinggi`, `sedang`, or `rendah`;
- `tanda_bahaya`: only `tanda_tangan_tanpa_layanan`, `diminta_membayar`, and
  `layanan_berbeda`;
- `membantah_tanggal_libur`: boolean;
- `kutipan_kunci`: short verbatim transcript excerpts;
- `ringkasan`: concise Indonesian summary.

On two invalid model results, `hasil` is null and the deterministic wrapper returns
`Tidak yakin` / `Pantau. Tidak dihitung.` with `galat=ekstraksi_tidak_valid`.

## Deterministic label order

Rules are evaluated in PRD order:

1. `tidak_terhubung` -> `Tidak terhubung` / monitor;
2. `menolak` -> `Menolak` / monitor;
3. `hadir=tidak` -> `Tidak sesuai` / ask hospital for clarification;
4. any allowed danger flag -> `Tidak sesuai` / clarification;
5. missing quantity or low confidence -> `Tidak yakin` / monitor;
6. `sesi_ditagih - jumlah_maks > 2` -> `Tidak sesuai` / clarification;
7. otherwise -> `Sesuai` / close case.

## Voice behavior

The system instruction contains the A-F sequence and explicit handling for: wrong recipient,
uncertain memory, scam concern, stop request, answer differing from the claim, off-topic
questions, and a statement that the patient never attended. The model is not told the billed
session count, preventing it from leading the recipient toward the expected answer.

The browser sends 16 kHz mono PCM to Gemini and plays 24 kHz PCM output. It commits finalized
input/output transcription events with local timestamps, clears queued output when interrupted,
emits backend-friendly lifecycle states, and mixes both sides into one MediaRecorder stream.

## Error and privacy behavior

- Logs contain route/error codes but no transcript, names, phone numbers, claim values, or tokens.
- Provider failures return a stable service error, never a guessed extraction.
- The browser stops media tracks, audio contexts, recorder, and WebSocket on close or timeout.
- No raw recording or transcript is persisted by `ai-service`; it is returned to the integration
  caller, which owns the PRD retention policy.

## Verification

- Python unit/API tests cover indicator boundaries, six-month continuity, schema constraints,
  label precedence, extraction retry/fail-safe behavior, token secrecy, and API contracts.
- Node tests cover PCM conversion, transcript event parsing, prompt/session setup, interruption,
  and lifecycle mapping without requiring live hardware.
- Manual Gemini/BlackHole acceptance remains required for three clear consecutive calls, 90%
  transcription accuracy, audio playback, and the 150-second limit.
- Deterministic fixture acceptance is verified against commit `7ca9f91`; live Gemini and
  BlackHole acceptance remains a separate manual gate.

