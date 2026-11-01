# Voice Acceptance Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing v3 AI implementation reproducibly acceptance-testable and automatically analyze completed browser calls.

**Architecture:** Keep the AI service stateless. Adapt official text fixtures into the existing request model, store the 20 additional cases as test data, and use one browser helper to call the existing answer endpoint after every completion path.

**Tech Stack:** Python 3.12, pytest, Pydantic v2, vanilla JavaScript ES modules, Node test runner, FastAPI/Gemini contracts already in the repository.

**Spec:** `docs/superpowers/specs/2026-10-28-voice-acceptance-completion-design.md`

## Global Constraints

- Do not commit; preserve every pre-existing user change in the dirty `feat/ai-service` worktree.
- Default tests must not require a network, Gemini quota, microphone, BlackHole, WhatsApp, or a phone.
- Never log or report transcript content in evaluation summaries.
- Use the six official key fields from `data-uji-konfirmasi/tools/uji.py` and the deterministic label.
- Do not implement backend-owned queue, WhatsApp, storage, retention, or verifier UI behavior.

## Review Focus

- Official transcript parsing must reject unknown speaker prefixes instead of silently assigning a role; Task 1 tests this.
- Live tests must remain opt-in so an absent key or network cannot make the normal suite flaky; Task 1 tests collection behavior.
- The 20-case fixture must be schema-valid, exactly 20 cases, and contain participant/family, uncertainty, refusal, danger, and colloquial variants; Task 2 tests this.
- Completed-call analysis must send one exact request and surface non-2xx responses; Task 3 tests both paths.
- Timeout/socket-close and manual-stop completion must share `onComplete` without duplicate analysis; Task 3 preserves the session's existing exactly-once completion test.

---

### Task 1: Official transcript acceptance adapter

**Files:**
- Create: `ai-service/src/vedika_ai/official_voice.py`
- Create: `ai-service/tests/test_official_voice_live.py`
- Modify: `ai-service/pyproject.toml`

**Interfaces:**
- Produces: `load_official_cases(root: Path) -> list[OfficialVoiceCase]`.
- Produces: opt-in `live_gemini` pytest coverage using the real `AnswerReader`.

- [x] Write failing tests for parsing S1, rejecting unknown speakers, and loading S1-S6/S8 with literal expected key fields.
- [x] Run the focused tests and verify the module is missing.
- [x] Implement the minimal fixture adapter and opt-in live test marker.
- [x] Run the focused offline tests and verify they pass.

### Task 2: Twenty-case evaluation corpus

**Files:**
- Create: `ai-service/tests/fixtures/voice-evaluation-20.json`
- Create: `ai-service/tests/test_voice_evaluation_fixture.py`
- Modify: `ai-service/README.md`

**Interfaces:**
- Consumes: existing `EvaluationCase` and `scripts/evaluate_voice.py`.
- Produces: reproducible 20-case input for the >=90% live Gemini gate.

- [x] Write a failing test requiring exactly 20 schema-valid cases and the required variation tags.
- [x] Run it and verify the fixture is missing.
- [x] Add the smallest complete 20-case synthetic fixture.
- [x] Run the fixture test and evaluator unit tests.

### Task 3: Automatic completed-call analysis

**Files:**
- Modify: `ai-service/web/voice-agent.mjs`
- Modify: `ai-service/web/voice-agent.test.mjs`
- Modify: `ai-service/web/voice-console.html`
- Modify: `ai-service/README.md`

**Interfaces:**
- Produces: `analyzeCompletedCall({fetchImpl, endpoint, billedSessions, transcript}) -> Promise<object>`.
- Consumes: `VedikaVoiceSession.onComplete` and `POST /v1/baca-jawaban`.

- [x] Write failing Node tests for the exact request body, empty transcript, and non-2xx response.
- [x] Run the focused Node suite and verify the export is missing.
- [x] Implement the minimal helper.
- [x] Wire console `onComplete` to preserve recording download and render the structured analysis once.
- [x] Run the Node suite and full Python suite.

### Task 4: Final acceptance verification

**Files:**
- Modify: `ai-service/README.md`

**Interfaces:**
- Documents exact offline, live-Gemini, and physical-call commands without claiming external gates passed.

- [x] Run the full Python suite, Ruff, Node suite, and official 300-row indicator check.
- [x] Attempt the live Gemini benchmark only when provider access is available; record the real outcome.
- [x] Review the complete diff for PRD scope, credential safety, transcript leakage, and accidental backend ownership.
