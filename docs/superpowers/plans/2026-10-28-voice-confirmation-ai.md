# Voice Confirmation AI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the AI-owned indicator, live-voice, structured-answer, and deterministic-label capabilities from PRD v3 without replacing the existing backend workflow.

**Architecture:** Extend the current FastAPI service with focused v3 domain modules and keep legacy document endpoints intact. A dependency-free browser ES module connects directly to Gemini Live with a server-issued ephemeral token, while structured transcript extraction and deterministic decisions stay server-side.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, standard-library HTTP transport, pytest, vanilla JavaScript ES modules, Node test runner, Gemini Live WebSocket API.

**Spec:** `docs/superpowers/specs/2026-10-28-voice-confirmation-ai-design.md`

## Global Constraints

- Do not create commits; the user explicitly requested an uncommitted execution.
- Preserve existing uncommitted changes and do not delete the current document engine.
- Permanent Gemini keys never reach browser code or API responses.
- No model-generated label: label and action are calculated by ordered deterministic rules.
- Do not claim official fixture acceptance until commit `7ca9f91` is locally available.
- Do not implement OpenAI fallback unless the Gemini/BlackHole gate fails.

## Review Focus

- Month/year boundaries in six-consecutive-month I3 calculation must not treat six arbitrary months as consecutive; Task 1 tests this.
- Three sessions spanning a Sunday/Monday boundary must use Monday-Sunday grouping; Task 1 tests this.
- Danger flags and `hadir=tidak` must override otherwise matching quantities; Task 2 tests precedence.
- Two malformed provider responses must produce `Tidak yakin` without transcript leakage in logs; Task 3 tests this.
- Browser interruption/close must discard queued audio and release tracks/contexts; Task 4 tests state transitions and documents the hardware check.

---

### Task 1: Indicator domain rules

**Files:**
- Create: `ai-service/src/vedika_ai/indicators.py`
- Create: `ai-service/tests/test_indicators.py`

**Interfaces:**
- Produces: `calculate_indicators(request: IndicatorRequest) -> IndicatorResult`
- Produces: `IndicatorRequest`, `IndicatorResult`, and `ServiceSession` Pydantic models.

- [ ] Write failing tests for I1 > 8, Monday-Sunday I2, exact six-month I3 including a year boundary, I4 Sunday/explicit holiday, and the >=2 queue threshold.
- [ ] Run `uv run pytest tests/test_indicators.py -q` and confirm missing-module failure.
- [ ] Implement the typed models and minimum deterministic calculation.
- [ ] Run `uv run pytest tests/test_indicators.py -q` and confirm all tests pass.

### Task 2: Structured answer and deterministic label

**Files:**
- Create: `ai-service/src/vedika_ai/answers.py`
- Create: `ai-service/tests/test_answers.py`

**Interfaces:**
- Produces: `JawabanTerstruktur`, `AnswerAnalysis`, `AnswerLabel`, and `classify_answer(answer, billed_sessions)`.
- Consumes: PRD R4.1-R4.4 field names and rule order.

- [ ] Write failing schema tests for allowed enums/danger flags, quantity range, and min <= max.
- [ ] Write failing parameterized tests for all seven label rules and precedence cases.
- [ ] Run `uv run pytest tests/test_answers.py -q` and confirm missing-module failure.
- [ ] Implement the strict models and ordered classifier.
- [ ] Run `uv run pytest tests/test_answers.py -q` and confirm all tests pass.

### Task 3: Gemini structured extraction with retry

**Files:**
- Create: `ai-service/src/vedika_ai/gemini.py`
- Create: `ai-service/src/vedika_ai/answer_reader.py`
- Create: `ai-service/tests/test_answer_reader.py`

**Interfaces:**
- Produces: `GeminiTransport.generate_json(prompt, schema) -> str`.
- Produces: `AnswerReader.read(request: ReadAnswerRequest) -> AnswerAnalysis`.
- Consumes: `JawabanTerstruktur` and `classify_answer` from Task 2.

- [ ] Write failing tests for valid first response, invalid-then-valid retry, two-invalid fail-safe, and provider transport failure.
- [ ] Run `uv run pytest tests/test_answer_reader.py -q` and confirm missing-module failure.
- [ ] Implement a small injectable standard-library Gemini transport and an `AnswerReader` limited to two attempts.
- [ ] Ensure logs report only safe error codes/attempt counts.
- [ ] Run `uv run pytest tests/test_answer_reader.py -q` and confirm all tests pass.

### Task 4: Voice prompt, ephemeral token, and browser Live client

**Files:**
- Create: `ai-service/src/vedika_ai/voice.py`
- Create: `ai-service/tests/test_voice.py`
- Create: `ai-service/web/voice-agent.mjs`
- Create: `ai-service/web/voice-agent.test.mjs`
- Create: `ai-service/web/voice-console.html`

**Interfaces:**
- Produces: `build_voice_instruction(context: VoiceContext) -> str`.
- Produces: `GeminiTokenIssuer.issue(context) -> VoiceTokenResponse`.
- Produces: browser `VedikaVoiceSession` with `start()`, `stop()`, status/transcript callbacks, and `recording` Blob.
- Consumes: `/v1/suara/token` response and Gemini Live WebSocket events.

- [ ] Write failing Python tests for required prompt branches, absence of billed quantity, one-use token request, and permanent-key secrecy.
- [ ] Write failing Node tests for PCM conversion, session setup, transcript parsing, interruption, and lifecycle states.
- [ ] Run both test files and confirm missing implementations fail.
- [ ] Implement the prompt and injectable token issuer.
- [ ] Implement the dependency-free browser client, recorder mix, and a minimal hardware console.
- [ ] Run `uv run pytest tests/test_voice.py -q` and `node --test web/voice-agent.test.mjs`.

### Task 5: FastAPI contracts and operator documentation

**Files:**
- Modify: `ai-service/src/vedika_ai/main.py`
- Modify: `ai-service/src/vedika_ai/config.py`
- Modify: `ai-service/tests/test_api.py`
- Modify: `ai-service/README.md`
- Create: `ai-service/.env.example`

**Interfaces:**
- Produces: `POST /v1/indikator`, `POST /v1/baca-jawaban`, `POST /v1/suara/token`.
- Consumes: Task 1-4 request/response models and dependency-injected provider clients.

- [ ] Add failing API tests for all three endpoints, missing Gemini configuration, authentication, and OpenAPI inclusion.
- [ ] Run the selected API tests and confirm 404/missing dependency failures.
- [ ] Wire endpoints and dependency overrides without changing legacy endpoint behavior.
- [ ] Document environment variables, BlackHole device routing, API examples, and manual gate steps.
- [ ] Run `uv run pytest tests/test_api.py -q` and confirm all tests pass.

### Task 6: Evaluation adapter and full verification

**Files:**
- Create: `ai-service/scripts/evaluate_voice.py`
- Create: `ai-service/tests/test_evaluate_voice.py`
- Modify: `ai-service/README.md`

**Interfaces:**
- Produces: a CLI that reads a JSON array of transcript cases, runs extraction/classification, and reports exact per-field accuracy without persisting transcript content.
- Defers: official `tools/uji.py` adapters until the unavailable corpus reveals its exact filenames/schema.

- [ ] Write a failing CLI test using a small synthetic fixture and injected deterministic responses.
- [ ] Implement field-level scoring and non-zero exit below a configurable 90% threshold.
- [ ] Run the focused evaluator test.
- [ ] Run `uv run pytest -q`, `uv run ruff check .`, and `node --test web/voice-agent.test.mjs`.
- [ ] Record the missing `7ca9f91` corpus and live Gemini/BlackHole call as explicit unverified acceptance gates.

