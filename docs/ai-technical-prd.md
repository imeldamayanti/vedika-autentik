# AI Technical PRD — Vedika Autentik

**Service:** `ai-service`

**Engine name:** PRAMANA

**Status:** Implemented baseline; real-data validation pending

**Version:** 0.5

**Date:** 2 October 2026

### Implementation status

| Phase | Status | Current result |
|---|---|---|
| 0 — Contract and scaffold | Done | `ai-service/`, typed Contract B, auth, logs, Docker, tests |
| 1 — Read and validate | Done (baseline) | Render, perspective correction, quality gate, templates, conservative field/session OCR, claim mismatch |
| 2 — Reuse detection | Done | Repeated rows/signatures, masked fingerprints, `/v1/bandingkan`, backend pairing |
| 3 — Provenance and editing | Partial by design | Editor/Canva metadata and template integrity are active; unvalidated pixel edit localization stays off |
| 4 — Calibration and deployment | Partial | Synthetic regression and CPU Docker definition exist; blind volunteer validation and deployed benchmark remain |

## 1. Purpose

`ai-service` analyzes a physiotherapy claim document and returns structured evidence about scan quality, document content, reuse, copy-paste, editing, and provenance.

It does **not** decide whether a claim is fraudulent. It does **not** assign the final label. Those decisions remain in `backend/` and with the verifier.

The MVP favors deterministic, explainable document processing over model-heavy automation.

## 2. Goals

1. Process PDF, JPG, and PNG documents through Contract B.
2. Read the fields needed to compare a document with its claim.
3. Detect the strongest, most explainable authenticity signals.
4. Return evidence as scores, regions, and short verifier-facing sentences.
5. Run on CPU in under 10 seconds for a warm one-page request.
6. Remain replaceable without requiring frontend changes.

## 3. Non-goals

- Declaring fraud or automatically rejecting a claim.
- Calculating `Lolos`, `Scan ulang`, `Perlu dicek`, or `Prioritas`.
- Identifying who wrote a signature.
- Training a large model or a custom foundation model.
- Using an LLM to detect manipulation or assign signal strength.
- Supporting arbitrary medical documents in the MVP.
- Production JKN Drive, E-Klaim, or PANDAWA integration.
- A generic AI-image detector presented as proof.

## 4. System boundary

```text
Frontend
   │
   ▼
backend/ ────────────────────────────────────────────────┐
  upload, auth, storage, queue, claim data,              │
  duplicate candidate search, labels, decisions         │
   │ Contract B                                          │
   ▼                                                     │
ai-service/                                              │
  render, normalize, assess, read, fingerprint,          │
  compare, localize, return evidence ────────────────────┘
```

### Ownership

| Concern | Owner |
|---|---|
| Upload, authentication, file storage | `backend/` |
| Job queue, retry, timeout, failure status | `backend/` |
| E-Klaim data lookup | `backend/` |
| Document rendering and normalization | `ai-service/` |
| Quality, OCR, fingerprints, visual checks | `ai-service/` |
| Searching stored fingerprints for candidates | `backend/` |
| Confirming and localizing a candidate pair | `ai-service/` |
| Final label and suggested action | `backend/` |
| Verifier decision, report, PANDAWA | `backend/` |

## 5. MVP capabilities

| ID | Capability | Output | MVP |
|---|---|---|---|
| AI-01 | File validation and page rendering | Canonical page image and metadata | Required |
| AI-02 | Scan-quality assessment | `baik` or `scan_ulang`, measurements, evidence region | Required |
| AI-03 | Template alignment | Template ID and aligned regions | Required |
| AI-04 | Structured extraction | SEP, period, session dates, filled rows, written total | Required |
| AI-05 | Claim consistency | `kecocokan_klaim` finding | Required |
| AI-06 | Within-document copy-paste | Matching rows/signatures/stamps | Required |
| AI-07 | Masked fingerprints | Page, row, and normalized-text fingerprints | Required |
| AI-08 | Pairwise duplicate comparison | Similarity, matching regions, shared pasted regions | Required |
| AI-09 | Metadata and provenance checks | Weak or medium `tanda_ai` evidence | Required |
| AI-10 | Edit localization | Suspicious regions with a medium signal | Experimental |

### Explicit MVP interpretation

- “AI-generated” means provenance or consistency signals, not a definitive classifier.
- `tempelan` is produced only when a source document is found through pairwise comparison.
- A single-document repeated element is `copy_paste`, not `tempelan`.
- An unreadable scan stops authenticity analysis and requests a rescan.

## 6. Processing pipeline

### `POST /v1/analisis`

```text
validate file
  → render pages
  → normalize orientation/perspective/size
  → quality gate
  → align known template
  → extract fields and session rows
  → compare with claim input
  → inspect repeated regions
  → build masked fingerprints
  → inspect metadata/provenance
  → optional edit localization
  → return structured evidence
```

Rules:

1. Normalize evidence coordinates to `[1240, 1754]` per page.
2. If the quality gate returns `scan_ulang`, do not run fraud-related checks.
3. Every finding contains `cek`, `kekuatan`, `kalimat`, and optional `skor`, `region`, or `area`.
4. The service never returns `label` or `saran`.
5. The service keeps no claim document after the request finishes.

### `POST /v1/bandingkan`

```text
render and align A + B
  → mask identity and date regions
  → compare whole content area
  → compare rows/signatures/stamps
  → localize shared regions
  → return similarity and evidence
```

`backend/` calls this endpoint only after its fingerprint search finds a candidate.

## 7. Technical approach

### 7.1 Rendering and normalization

- Render PDFs at A4 150 DPI.
- Convert input to RGB and correct EXIF orientation.
- Detect a photographed paper boundary, correct its quadrilateral perspective, then resize to canonical geometry.
- Keep scanner-origin pages that already fill the frame out of the perspective path.
- Preserve the original file hash and metadata separately from normalized pixels.
- Reject encrypted, corrupt, oversized, or unsupported files.

### 7.2 Quality gate

Measure:

- sharpness;
- brightness and contrast;
- page skew;
- visible page boundary;
- required template-region coverage.

Thresholds live in one versioned configuration file. They are calibrated against originals and bad scans, not chosen per request.

### 7.3 Template alignment

The MVP supports the supplied physiotherapy layouts through versioned JSON templates.

```json
{
  "id": "melati-v1",
  "canonical_size": [1240, 1754],
  "anchors": ["kop", "tabel", "total"],
  "regions": {
    "identity": [88, 250, 1064, 230],
    "session_rows": [[89, 572, 1063, 92]],
    "dates": [[120, 572, 110, 92]],
    "signatures": [[902, 572, 250, 92]],
    "total": [88, 1339, 674, 82]
  },
  "fingerprint_masks": ["identity", "dates"]
}
```

Automatic arbitrary-layout detection is deferred. An unsupported template must fail safely as `Perlu dicek` through the backend, never `Lolos`.

### 7.4 Structured extraction

The implemented baseline uses a whole-page OCR pass plus fixed template crops. Filled-row
counting is pixel-based. Name, card number, SEP, dates, period, and written total are returned
only after field-specific validation:

- SEP and card number: character whitelist and length checks;
- names: high-confidence crop plus a two-word/person-format check;
- dates: full `DD/MM` parse, period validation, and one unambiguous increasing sequence;
- filled rows: visual occupancy plus presence of date/service/signature content;
- written visit total: digit OCR in the total region.

OCR confidence is applied before output. A low-confidence field remains `null`; it is not
guessed or copied from claim context. This trades coverage for precision on handwritten text.

### 7.5 Claim consistency

Compare the provided claim only when `klaim.sesi_ditagih` exists.

A strong mismatch requires reliable extraction, for example:

- claimed sessions exceed supported filled rows; or
- session dates fall outside the claimed period.

The output is a rule result, not a learned fraud prediction.

### 7.6 Copy-paste detection

Compare aligned row, signature, therapist-initial, and stamp crops after grayscale normalization.

The MVP uses background-normalized pixel correlation with a small translation tolerance.
A session is reduced only when both its signature and service/therapist content match a prior
row. Local-feature matching is deferred until real scan variation shows it is needed.
Thresholds are versioned and evaluated against genuine repeated handwriting.

### 7.7 Fingerprints and duplicate comparison

Return:

- 64-bit perceptual hash of the masked content page;
- perceptual hashes for service rows;
- deterministic text-surrogate fingerprint derived from masked visual row hashes;
- fingerprint algorithm version.

Identity and date regions are masked before calculation.

`backend/` retrieves approximate candidates by template and Hamming distance. For the MVP, it may compare a bounded candidate set in application code. A vector database or separate similarity service is not required.

`/v1/bandingkan` confirms a candidate using the aligned full page and region-level comparisons. Fingerprint proximity alone is not a `berkas_kembar` finding.

### 7.8 Metadata and provenance

Inspect:

- PDF `Producer`, `Creator`, creation time, and modification time;
- EXIF/IPTC metadata;
- valid C2PA manifests when a production-approved verifier is later added;
- consistency between claimed scan origin and pixel characteristics.

Metadata is supporting evidence. Missing metadata is not suspicious by itself. A design-tool name or C2PA assertion never becomes a fraud verdict.

The current rules emit medium supporting evidence for explicit Photoshop/GIMP/Canva
metadata and weak evidence when reliable OCR cannot find a known static hospital anchor.
They do not infer AI generation from missing metadata or a generic visual score.

### 7.9 Edit localization

Start with deterministic forensic maps and consistency checks. A pretrained localization model may be evaluated behind a feature flag after the required checks work.

This capability remains experimental until it meets the edited-region target on data not used for threshold selection. Error Level Analysis alone is never sufficient evidence.

## 8. Tools and models

### Selected for the MVP

| Tool/model | Role | Decision |
|---|---|---|
| Python 3.12 | Runtime | Match the existing backend runtime |
| `uv` | Dependency and environment management | One `pyproject.toml` and committed `uv.lock` in `ai-service/` |
| FastAPI + Uvicorn | Contract B HTTP service | Match backend conventions |
| Pydantic | Request/response validation | Contract models and generated OpenAPI |
| Loguru | Structured application logging | No patient identifiers or OCR text in logs |
| `pypdfium2` | PDF rendering | CPU-capable PDFium binding with permissive licensing |
| `pypdf` | PDF metadata | Read metadata without using it as proof |
| Pillow | Image decoding and EXIF/IPTC access | Lightweight file handling |
| OpenCV headless | Quality metrics, masks, normalized correlation, perceptual hashes | Main deterministic vision library |
| NumPy | Image arrays and scoring | Shared numerical base |
| Tesseract 5 + `pytesseract` | Baseline text recognition | Verified locally and packaged in the CPU Docker image |
| pytest + HTTPX | Unit and contract tests | Match backend tests |
| Ruff | Formatting and linting | One fast code-quality tool |

### Not in the initial MVP

| Tool/model | Reason |
|---|---|
| LLM | No task requires probabilistic language reasoning |
| Custom OCR or fraud model training | Dataset is too small and synthetic |
| Generic AI-image detector | Weak generalization; not suitable as proof |
| TruFor or another forgery model | Evaluate later behind a feature flag and license review |
| PaddleOCR PP-OCRv5 mobile | Candidate only; adopt only if a reproducible CPU benchmark beats the baseline |
| GPU runtime | Required checks must run on CPU first |
| Celery, Redis, Kafka | The backend already owns a sufficient PostgreSQL job queue |
| MLflow or Weights & Biases | JSON evaluation reports are sufficient for the MVP |
| Vector database | Bounded Hamming-distance candidate search is sufficient initially |

The service runs one OCR engine by default. Tesseract 5 is the verified Phase 1 baseline.
PaddleOCR remains an evaluation candidate, not a second production engine or current dependency.

## 9. Repository structure

```text
ai-service/
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── README.md
├── src/
│   └── vedika_ai/
│       ├── main.py
│       ├── config.py
│       ├── schemas.py
│       ├── pipeline.py
│       ├── imaging.py
│       ├── quality.py
│       ├── templates.py
│       ├── extraction.py
│       ├── comparison.py
│       ├── fingerprints.py
│       ├── provenance.py
│       └── evidence.py
├── templates/
│   ├── melati-v1.json
│   ├── cipta-medika-v1.json
│   └── bakti-mulia-v1.json
└── tests/
    ├── unit/
    ├── contract/
    └── evaluation/
```

Do not import Python code directly from `backend/`. The two services integrate only through Contract B and shared schema fixtures.

## 10. API contract

The authoritative behavior is [API Contract B](api-contract.md#kontrak-b-api--mesin-ai-v1).

Endpoints:

| Endpoint | Purpose |
|---|---|
| `POST /v1/analisis` | Analyze one original document plus optional claim and template context |
| `POST /v1/bandingkan` | Confirm and localize similarities between two candidate documents |
| `GET /v1/kesehatan` | Report engine and loaded model versions |

Contract B is represented by Pydantic models and exported through FastAPI OpenAPI for contract tests.

Resolved contract decisions:

1. Replace the ambiguous `halaman_jpg` “base64 or URL” with one explicit transport. MVP choice: JPEG base64 returned to the backend for storage.
2. Add `template_id` and `versi_template` to the analysis response.
3. Add `versi_fingerprint` to `sidik_jari`.
4. Ensure the backend always forwards `kode_faskes`; an explicit `template` remains optional.
5. Keep `tempelan` pair-dependent; do not emit it from single-document analysis.

## 11. Configuration and versioning

Version independently:

- service release: `pramana-0.x.y`;
- OCR model;
- template;
- quality thresholds;
- fingerprint algorithm;
- finding thresholds.

Threshold constants stay beside the deterministic module that uses them. Their combined rule
version is included in evaluation output; move them to deployment configuration only when
real-data calibration requires operational tuning.

Tesseract is installed during the image build. Production startup does not download models from the internet.

## 12. Errors and fail-safe behavior

| Condition | AI response | Backend outcome |
|---|---|---|
| Corrupt or unreadable file | `422 tidak_terbaca` | `Perlu dicek` |
| Unsupported format or size | `413/415` structured error | Upload rejected or `Perlu dicek` |
| Bad scan | Successful response with `scan_ulang` | `Scan ulang` |
| Unsupported template | Structured `422` error | `Perlu dicek` |
| OCR uncertainty | Nullable fields; no guessed mismatch | Continue with available evidence |
| OCR timeout/failure | `503 ocr_gagal` | Retry, then `Perlu dicek` |
| Internal model failure | Structured `500` error | Retry, then `Perlu dicek` |

No exception path may result in `Lolos`.

## 13. Privacy, security, and logging

- Keep the service stateless; use request-scoped temporary files only when a library requires a path.
- Delete temporary files in `finally` blocks.
- Do not call external AI or OCR APIs.
- Authenticate backend-to-service traffic with `X-Kunci-Layanan`.
- Enforce file count, size, page count, and processing time limits.
- Treat filenames and metadata as untrusted input.
- Do not log names, card numbers, SEP values, OCR text, raw images, or base64 content.
- Log request ID, route, status, duration, and error code only.

## 14. Testing and evaluation

### Test layers

| Layer | Purpose |
|---|---|
| Unit | Image metrics, masks, parsers, hashes, thresholds |
| Contract | Exact request/response behavior against Contract B |
| Dataset regression | Run all 17 synthetic documents and compare structured outputs |
| Pair regression | Verify known duplicate and non-duplicate pairs |
| Robustness | Recompression, scale, brightness, and phone perspective |
| Performance | Warm CPU latency and memory per page |

### Product targets

| Metric | Target |
|---|---|
| Session count read correctly | ≥ 95% |
| Duplicate documents detected | ≥ 95% |
| Pasted signatures/stamps detected | ≥ 90% |
| Edited text/number regions detected | ≥ 70% |
| Genuine documents incorrectly escalated to Prioritas | ≤ 5% end to end |
| Bad genuine scans escalated to Prioritas | 0 |
| Warm one-page CPU processing | p95 < 10 seconds |

The 17 synthetic files are regression fixtures, not proof that these accuracy targets are met. Accuracy claims require a blind set from 20–30 volunteers with genuine handwriting and varied capture conditions.

Evaluation output is a versioned JSON report containing dataset revision, engine version, threshold version, per-check confusion data, latency, and failures.

Latest synthetic regression for `pramana-0.5.0` with Tesseract on local CPU:

| Metric | Result |
|---|---|
| Quality status | 17/17 |
| Session count on readable scans | 14/14 |
| Session-date sequences | 6/14 returned; 6/6 exact |
| Name / card / SEP / period | 3/14, 5/14, 3/14, 11/14 returned; all returned values exact |
| Written visit total | 1/14 returned; 1/1 exact |
| Duplicate/non-duplicate pairs | 6/6 |
| `copy_paste`, claim mismatch, and `tanda_ai` fixture precision/recall | 1.00 / 1.00 |
| `suntingan` fixture precision/recall | 1.00 / 0.40 |
| One-page latency | p95 1.34 s |

The three missed `suntingan` fixtures are identity edits in duplicate families. The pair
flow still catches those documents through `berkas_kembar` and `tempelan`. These numbers
describe the 17 synthetic fixtures only and are not a real-world accuracy claim.

## 15. Delivery plan

### Phase 0 — Contract and scaffold (done)

- Create `ai-service/` with `uv`, FastAPI, Loguru, linting, and tests.
- Define Pydantic Contract B models.
- Add contract tests against the existing stub examples.
- Add model/version reporting to health output.

### Phase 1 — Read and validate (baseline done)

- Render and normalize documents.
- Implement quality gate and three supplied templates.
- Correct photographed-page perspective and keep canonical evidence coordinates.
- Extract rows plus conservative name, card, SEP, period, date, and written-total fields.
- Produce claim-consistency findings.

### Phase 2 — Reuse detection (done)

- Detect repeated rows and signatures within a document.
- Generate masked fingerprints.
- Implement pairwise duplicate confirmation and evidence regions.
- Integrate backend candidate search.

### Phase 3 — Provenance and editing (partial)

- Read PDF/image metadata. (done)
- Add conservative provenance and template-integrity signals. (done)
- Keep pixel edit localization disabled until it has a blind-set precision result.
- Do not depend on a pretrained forgery-localization model in the MVP.

### Phase 4 — Calibration and deployment (partial)

- Collect volunteer validation data.
- Calibrate thresholds on a development split and report once on a blind split.
- CPU Dockerfile packages Tesseract without runtime downloads. (done; daemon build verification pending)
- Synthetic regression, robustness, failure, and privacy-safe logging tests. (done)
- Run blind volunteer and deployed CPU benchmarks.

## 16. Definition of done for the MVP

- All three Contract B endpoints are implemented and contract-tested.
- The backend can replace `stub_mesin` by changing `MESIN_URL` only.
- Required checks produce evidence from file pixels rather than filenames or ground truth.
- The five demo files complete through the real service.
- All 17 fixtures run without unhandled errors.
- Bad scans never produce fraud-related findings.
- No AI-only evidence can create `Prioritas` by itself.
- Model and threshold versions appear in results and evaluation reports.
- CPU latency and accuracy are reported honestly, including misses.
- No sensitive content appears in logs.

## 17. Implemented decisions

1. Use Tesseract 5 as the verified CPU baseline; benchmark PaddleOCR separately before adoption.
2. Support the three supplied hospital templates; defer arbitrary forms.
3. Return the canonical JPEG as base64 to the backend.
4. Keep approximate fingerprint candidate retrieval in `backend/`.
5. Treat edit localization as experimental until volunteer-data evaluation.
6. Do not include a generic AI-image classifier in the initial MVP.
7. Prefer a missing OCR value over a plausible but unverified handwritten guess.

## References

- Product requirements: [`../PRD_Vedika_Autentik_PRAMANA.md`](../PRD_Vedika_Autentik_PRAMANA.md)
- API contract: [`api-contract.md`](api-contract.md)
- Backend plan: [`rencana-be.md`](rencana-be.md)
- Dataset guide: [`../dataset/README.md`](../dataset/README.md)
- Real-data validation protocol: [`ai-validation-protocol.md`](ai-validation-protocol.md)
- PaddleOCR PP-OCRv5: <https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html>
- Tesseract OCR: <https://github.com/tesseract-ocr/tesseract>
- pypdfium2: <https://pypdfium2.readthedocs.io/en/stable/readme.html>
- uv projects: <https://docs.astral.sh/uv/concepts/projects/>
- C2PA Python SDK: <https://github.com/contentauth/c2pa-python>
