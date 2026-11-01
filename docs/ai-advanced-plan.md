# Advanced AI Plan — Vedika Autentik

**Service:** `ai-service`  
**Engine:** PRAMANA  
**Status:** Phase 0 implemented; review pending  
**Version:** 0.1  
**Date:** 10 October 2026

## 1. Outcome

Extend the current deterministic document engine into a multimodal claim-investigation
system. The system will combine document understanding, visual forensics, structured claim
history, and an evidence-grounded reviewer brief.

The system returns evidence and an optional calibrated risk score. The backend maps that
evidence to review priority. The AI service never declares fraud or automatically rejects a
claim.

## 2. Design decisions

1. Keep the working CPU pipeline as the fallback and control group.
2. Add GPU/VLM components only when they beat the baseline on a blind evaluation set.
3. Keep `backend/` responsible for authentication, files, database access, jobs, retries,
   final labels, and reviewer workflow.
4. Keep `ai-service/` stateless and responsible for extraction, inference, comparison,
   evidence localization, and model/version reporting.
5. Use the LLM/VLM for bounded extraction and explanation. Deterministic code or a calibrated
   tabular model calculates scores.
6. Treat every model output as a signal with provenance, confidence, and supporting fields or
   image regions.
7. Keep raw claims and volunteer documents outside Git. Commit only schemas, aggregate
   statistics that pass privacy review, and synthetic fixtures.

## 3. Target capabilities

| Capability | Production target | Main approach |
|---|---|---|
| Multimodal field extraction | Read typed, handwritten, tabular, and multi-page content | OCR + document VLM + schema validation |
| Cross-document consistency | Compare SEP, referral, therapy log, and invoice fields | Normalized fields + deterministic comparison |
| Visual edit localization | Highlight likely changed or pasted regions | Deterministic forensics, then a gated segmentation model |
| Duplicate/reuse search | Find reused documents, rows, stamps, and signatures | Existing hashes first; embeddings only if needed |
| Claim-history anomaly | Detect unusual frequency, chronology, combinations, and cost | Rules, robust statistics, then unsupervised models |
| Clinical-code consistency | Flag uncommon diagnosis/procedure combinations | Historical frequency tables and text embeddings |
| Evidence fusion | Produce one calibrated review priority with reasons | Rules initially; logistic calibration after labels exist |
| Reviewer brief | Summarize evidence in Indonesian with citations to evidence IDs | Constrained local LLM/VLM output |

## 4. Architecture

```text
Frontend
   │
   ▼
backend/
  upload, auth, storage, DB lookup, job queue, candidate search,
  reviewer decision and final label
   │
   ├── document + current claim ──────────────┐
   └── bounded claim history ──────────────┐  │
                                           ▼  ▼
                                      ai-service/
                       ┌────────────────────┼────────────────────┐
                       │                    │                    │
                 CPU document         GPU document       Claim intelligence
                 normalization        understanding      and anomaly scoring
                 and baseline         and forensics      (CPU initially)
                       │                    │                    │
                       └────────────────────┼────────────────────┘
                                            ▼
                                    evidence fusion
                                            ▼
                              findings + regions + versions
                                            │
                                            ▼
                                         backend/
```

There is no new queue inside `ai-service`. The existing backend worker calls the service and
owns retries and timeouts. CPU checks remain available when the GPU path is disabled or
unhealthy.

## 5. Data plan

### 5.1 `Folder Data Asli`

Use the structured BPJS sample for offline development only:

- ingest `.dta` files in chunks;
- join membership with FKTP/FKRTL through pseudonymous participant and visit identifiers;
- create a rehabilitation subset using clinic, diagnosis, and procedure codes together;
- calculate non-identifying reference distributions;
- create fictional claims from those distributions;
- never serve or commit raw rows.

The first reference cohort is the 2024 outpatient rehabilitation slice: 174,026 rows,
14,197 participants, and 47,049 participant-months. The clinic category includes physical,
occupational, and speech therapy, so procedure and diagnosis filters are mandatory.

The data supports claim patterns and synthetic content. It does not contain document pixels,
tampering labels, confirmed fraud labels, or direct links between scanned forms and claims.

### 5.2 Document data

Three document tiers are required:

| Tier | Purpose | May be committed? |
|---|---|---|
| Existing synthetic fixtures | Fast regression and contract tests | Yes |
| Generated claim/document pairs | Training support and controlled edit masks | Only if fully fictional |
| Consented volunteer blind set | Real handwriting, scanning, and phone capture evaluation | No |

Synthetic edits must store the original value, changed value, operation, page, bounding box or
mask, and parent document. Include changes to dates, totals, session rows, diagnosis, procedure,
stamp, and signature, plus blur, rotation, perspective, print-scan, and recompression variants.

Synthetic data is useful for regression and pretraining; release claims require the untouched
volunteer blind set.

### 5.3 Privacy controls

- Add `Folder Data Asli/`, raw extracts, processed participant-level files, model caches, and
  volunteer captures to `.gitignore` before preprocessing begins.
- Do not place participant identifiers, OCR text, filenames, or images in logs.
- Hash identifiers only when longitudinal grouping is necessary; do not export the mapping.
- Record source edition, transform version, and row counts in a manifest.
- Confirm dataset terms before using derived artifacts outside internal evaluation.

## 6. Models and tools

| Component | Initial choice | Decision rule |
|---|---|---|
| Runtime/API | Existing Python, `uv`, FastAPI, Pydantic, Loguru | Keep |
| Image baseline | Existing OpenCV + Tesseract | Always retained as fallback |
| Stata ingestion | `pyreadstat` chunked reader | Offline dependency only |
| Feature processing | Polars + Parquet | Use for processed, columnar data; no raw data in runtime |
| VLM candidate | Qwen3-VL-8B-Instruct; 4B fallback | Adopt only after extraction benchmark and license record |
| VLM runtime | PyTorch + Transformers initially | Evaluate an optimized server only after correctness |
| Structured anomaly | Robust statistics + scikit-learn Isolation Forest | Deep sequence model only if this baseline is insufficient |
| Evidence calibration | Logistic regression | Train only after enough reviewer outcomes exist |
| Visual localization | Lightweight segmentation model trained/evaluated on labeled edits | Ship only after blind-set gate |
| Reviewer brief | Same local VLM/LLM, constrained to evidence JSON | Feature-flagged; templates remain fallback |
| Experiment tracking | Versioned JSON/Parquet manifests | No MLflow/W&B initially |
| Similarity storage | Existing hashes and backend PostgreSQL | Add vector search only after measured retrieval need |

Qwen3-VL is a candidate because its official release supports document parsing, OCR, key
information extraction, and visual grounding, and its 8B weights are Apache-2.0 licensed.
It is not selected until it passes our Indonesian forms benchmark.

TruFor may be used only as a research benchmark because its official repository restricts
use to informational and nonprofit purposes. It is not a production dependency.

## 7. Contract evolution

Preserve the existing endpoints:

- `POST /v1/analisis` for one document;
- `POST /v1/bandingkan` for a candidate document pair;
- `GET /v1/kesehatan` for readiness and loaded versions.

Add one endpoint when Phase 2 begins:

```text
POST /v1/analisis-klaim
```

It accepts the current normalized claim and a bounded list of previous events supplied by the
backend. It returns structured findings only. `ai-service` does not query the production
database directly.

Extend the finding vocabulary additively:

- `forensik_visual`;
- `anomali_frekuensi`;
- `anomali_duplikat`;
- `ketidakcocokan_klinis`;
- `anomali_biaya`;
- `ketidakkonsistenan_dokumen`.

Every finding must include an evidence ID, component version, score when applicable, concise
sentence, and supporting fields or image regions. The response may include an optional
`ringkasan_peninjau`, but the backend still determines the final label and action.

## 8. Delivery phases and gates

### Phase 0 — Data safety and reproducibility

Deliver:

- ignore rules for raw, processed, model-cache, and volunteer data;
- `scripts/prepare_claim_reference.py` with chunked `.dta` ingestion;
- rehabilitation filter and data dictionary;
- aggregate reference tables and a privacy-safe manifest;
- tests that ensure raw identifiers cannot appear in generated fixtures or logs.

Gate:

- rerunning the pipeline produces the same row counts and aggregate checksums;
- no raw participant-level artifact is tracked by Git;
- cohort counts reconcile with the audited source data.

Implementation record, 10 October 2026: complete. The 2024 source produced 149,997
physiotherapy-reference rows, 13,172 unique participants, and 41,905 participant-months. A
second clean run matched every generated file byte for byte. Privacy-schema, suppression,
manifest-checksum, unit, and full service tests pass.

### Phase 1 — VLM extraction benchmark

Deliver:

- a `DocumentExtractor` interface shared by Tesseract and the VLM adapter;
- constrained JSON extraction with page and region grounding;
- multi-page field reconciliation;
- benchmark report for Tesseract, Qwen3-VL-4B, and Qwen3-VL-8B;
- CPU fallback and a feature flag for the selected GPU path.

Gate on a volunteer-held-out set:

- 100% schema-valid responses;
- critical identifier accuracy when returned at least 98%;
- date and session-count exact accuracy at least 95%;
- incorrect confident values at most 2%;
- measurable coverage improvement over Tesseract without regression in precision;
- latency and peak GPU memory reported, not assumed.

If neither VLM candidate passes, retain Tesseract and improve preprocessing or data before
trying a larger model.

### Phase 2 — Structured claim intelligence

Deliver:

- `/v1/analisis-klaim` request and response schemas;
- frequency, same-day duplicate, chronology, diagnosis/procedure, and cost features;
- robust percentile rules and Isolation Forest baseline;
- synthetic anomaly cases with known expected findings;
- explanations that name the exact contributing features.

Gate:

- deterministic replay from a feature manifest;
- no claim is flagged solely because it belongs to a rare demographic group;
- false-positive rate and detection rate reported by anomaly type;
- anomaly model must outperform the rules baseline to remain enabled.

### Phase 3 — Synthetic document factory

Deliver:

- fictional claim generator based on aggregate distributions;
- template renderer for clean document pairs;
- controlled tampering transformations and pixel masks;
- train/development/test manifests split by base document and volunteer;
- at least 1,000 generated original/edited pairs as the first regression corpus; expand it
  only when the model learning curve or manipulation coverage shows a measured need.

Gate:

- no source participant identifier or exact source row is reproduced;
- every edit is machine-verifiable from its manifest;
- splits contain no derivative of the same base document across boundaries.

### Phase 4 — Visual edit localization

Deliver:

- benchmark of current deterministic checks and one license-compatible segmentation model;
- document-level score, pixel/box localization, and reliability score;
- analysis by manipulation type and capture degradation;
- feature flag with deterministic fallback.

Gate on the volunteer blind set:

- edited-region recall at least 70%, with precision reported;
- genuine-document escalation no more than 5% end to end;
- bad genuine scans are sent to `scan_ulang`, never escalated as manipulation;
- the learned signal cannot independently create the strongest review outcome.

### Phase 5 — Evidence fusion and reviewer brief

Deliver:

- versioned feature-to-score mapping;
- calibrated logistic fusion only when reviewer labels are sufficient;
- constrained Indonesian reviewer brief referencing evidence IDs;
- deterministic sentence-template fallback;
- tests that the LLM cannot add findings absent from input evidence.

Gate:

- every sentence resolves to one or more returned evidence IDs;
- score calibration is reported with reliability curves and subgroup checks;
- removing the LLM changes wording only, not findings or risk score;
- final approval/rejection remains a reviewer or backend decision.

### Phase 6 — GPU deployment and shadow rollout

Deliver:

- separate CPU and GPU dependency/container profiles;
- model weights pinned by revision and checksum;
- startup readiness, bounded concurrency, timeout, and out-of-memory handling;
- GPU path first deployed in shadow mode beside the CPU baseline;
- operational dashboards containing latency and error metrics only.

Gate:

- baseline requests still work when no GPU is available;
- no runtime model downloads;
- no sensitive content in logs or metrics;
- shadow results pass the same frozen evaluation suite before reviewer visibility.

Start capacity testing with one 24 GB NVIDIA GPU for the 8B candidate. Treat that as a test
configuration, not a guaranteed requirement; publish measured latency, throughput, and memory
before choosing the deployment size.

## 9. Evaluation matrix

| Layer | Primary metrics |
|---|---|
| Extraction | Field exact match, coverage, accuracy when returned, schema validity |
| Grounding | Region intersection-over-union and correct page |
| Forensics | Document precision/recall, pixel/region precision/recall, false escalation |
| Claim anomaly | Detection by perturbation type, false positives, score stability |
| Duplicate retrieval | Recall@K followed by pair-verification precision |
| Fusion | Precision/recall, calibration error, subgroup false-positive rates |
| Reviewer brief | Evidence citation completeness and unsupported-statement rate |
| Operations | p50/p95 latency, throughput, GPU memory, timeout and failure rate |

Report synthetic, development, and blind-set results separately. Never combine them into one
headline accuracy number.

## 10. Explicitly deferred

- Training a foundation model from scratch.
- Fine-tuning the VLM before prompt/schema baselines are measured.
- Graph neural networks before stable patient, provider, doctor, and claim identifiers exist.
- A vector database before hash retrieval fails a measured scale or recall target.
- A second orchestration service, Celery, Redis, Kafka, MLflow, or Kubernetes for the initial
  advanced release.
- Cloud LLM/VLM APIs carrying claim documents unless privacy, contract, and data-residency
  approval is obtained separately.
- Automated fraud declarations, claim rejection, or medical-necessity decisions.

## 11. Definition of done

The advanced system is ready for a controlled reviewer pilot when:

1. Phases 0–5 meet their frozen gates on data not used for tuning.
2. Every finding has a versioned source and inspectable evidence.
3. CPU fallback passes the existing Contract B and regression suite.
4. GPU unavailability degrades capability without losing the analysis job.
5. The LLM/VLM cannot change final labels or invent evidence.
6. Privacy review confirms that raw claims, documents, identifiers, and OCR text are absent
   from Git and logs.
7. The evaluation report states limitations, misses, false positives, compute, and dataset
   composition.

## 12. Execution order

The next implementation work should be Phase 0 only. After its artifacts and privacy checks
are reviewed, proceed to the Phase 1 benchmark. Do not add the GPU runtime to the production
image until a VLM passes the Phase 1 gate.

## References

- Baseline technical PRD: [`ai-technical-prd.md`](ai-technical-prd.md)
- Validation protocol: [`ai-validation-protocol.md`](ai-validation-protocol.md)
- API contract: [`api-contract.md`](api-contract.md)
- Qwen3-VL official repository: <https://github.com/QwenLM/Qwen3-VL>
- Qwen3-VL-8B-Instruct model card: <https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct>
- PaddleOCR: <https://github.com/PaddlePaddle/PaddleOCR>
- TruFor official repository and license notice: <https://github.com/grip-unina/TruFor>
