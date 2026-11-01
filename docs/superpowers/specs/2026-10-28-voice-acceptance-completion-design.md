# Voice Acceptance Completion Design

**Date:** 2026-10-28  
**Source:** PRD v3 and the AI completion audit on `feat/ai-service`  
**Scope:** Close the remaining AI-owned test and operator-console gaps without implementing software-engineer-owned orchestration.

## Intent

Turn the existing AI foundation into an acceptance-testable prototype. Official transcripts and
20 additional conversational cases must be runnable through the real Gemini extractor, while the
operator console must automatically turn a completed call transcript into the deterministic result.

## Goals

- Convert the official S1-S6 and S8 transcript files into the existing `ReadAnswerRequest` contract.
- Provide an opt-in live Gemini acceptance test that compares key fields and labels with the
  official expected results.
- Add exactly 20 synthetic, non-sensitive transcript cases and a fixture validation test so the
  PRD's >=90% field-accuracy gate can be run reproducibly.
- Automatically call `/v1/baca-jawaban` after a browser voice session completes and show the
  structured result alongside the transcript and recording download.
- Keep the default offline test suite deterministic and network-free.

## Non-goals

- WhatsApp sending, dial retries, queue scheduling, family-recipient selection, persistence,
  evidence cards, retention, verifier decisions, or hospital summaries.
- Inventing a backend `/panggilan/{id}/hasil` payload before the backend owner defines its storage
  and upload contract.
- Claiming that real Gemini, BlackHole, or telephone acceptance passed when those external systems
  could not be exercised.

## Selected approach

Reuse the current extraction and evaluator contracts. Add a small fixture adapter for the official
corpus, a checked-in 20-case JSON fixture, and an opt-in live pytest marker. In the browser module,
add one focused `analyzeCompletedCall` function; the console consumes it from `onComplete` so manual
stop, timeout, and socket-close completion all follow the same path.

This avoids a second extraction implementation, keeps credentials server-side, and does not couple
the stateless AI service to backend persistence that it does not own.

## Error behavior

- A non-2xx answer-reader response raises a concise operator-visible error.
- A call with no transcript is not sent to Gemini; the console reports that no answer can be read.
- A recording remains downloadable even when answer extraction fails.
- Live acceptance is skipped unless explicitly enabled and a Gemini key is configured.

## Acceptance

- Offline Python and Node suites pass.
- The official adapter covers S1-S6 and S8 and compares the six key PRD fields plus label.
- The additional fixture contains exactly 20 varied cases and is accepted by the evaluator schema.
- The console sends `sesi_ditagih` plus timestamped transcript to `/v1/baca-jawaban` exactly once
  per completed session.
- Live Gemini and physical WhatsApp/BlackHole calls remain explicitly reported as manual gates.
