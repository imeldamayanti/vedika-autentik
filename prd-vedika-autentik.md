<!-- prd-progress
role: executor
pace: normal
prd-language: English
sections:
  metadata: done
  background: done
  success-metrics: done
  documentation: done
  timeline: done
  scope: done
  discussions: done
  competitive-analysis: done
  product-requirement: done
  acceptance-criteria: done
  event-tracker: done
  test-cases: done
gaps:
  - Validate every item marked (*).
-->
<!-- Format rules for scripts/build_docx.py:
  - "# " is the project name. "## " is a section. "### " is a sub-heading.
  - In tables, a cell containing only ^ merges into the cell above.
  - Use <br> for a line break inside a table cell.
  - HTML comments are not exported.
  - Status values: todo, in-progress, done, skipped.
-->

# Vedika Autentik

Disclaimer: filled by AI in Executor role. Every item marked (*) is a prediction. Validate and check each one before sharing or acting on this PRD.

| | |
|---|---|
| **Target release** | 30 October 2026 |
| **Epic** | Vedika Autentik MVP epic, to be created in the team's issue tracker (*) |
| **Document status** | Draft |
| **Document owner** | @product-owner (*) |
| **Designer** | @product-designer (*) |
| **Tech lead** | @tech-lead (*) |
| **Technical writers** | @technical-writer (*) |
| **QA** | @qa-owner (*) |

## Background

### What is the background that initiates this project?

Predicted: BPJS claim reviewers need to examine physiotherapy claim history and supporting documents, but structured claim signals and document-integrity evidence are presented separately or checked manually. Vedika Autentik adds a verifier-assistance workflow that accepts a supporting document and bounded claim context, then returns traceable findings for human review. It prioritizes explainable evidence and safe failure over an automatic fraud conclusion. (*)

Predicted: the current repository already demonstrates a reviewer queue, synthetic physiotherapy documents, four review labels, evidence cards, reviewer actions, PDF reporting, and a PRAMANA analysis service. The public demo still reads expected findings from synthetic ground truth, while the real service and backend are separate. The next release should connect the defensible capabilities into one data-aligned MVP. (*)

### What are the problems? Has the problem been verified?

The problems are:

- **Fragmented review evidence:** Predicted: a claim reviewer must compare document contents, claim history, dates, costs, and repeated submissions without one traceable evidence view. (*)
- **Unreliable document intake:** Predicted: blurred, cropped, rotated, malformed, or unsupported files can produce incomplete extraction unless the system stops and requests a new scan. (*)
- **Repeated or altered documents are difficult to compare:** Predicted: exact reuse, near reuse, copy-paste regions, and edited values require visual comparison that takes reviewer time and can be inconsistent. (*)
- **Risk signals can be overstated:** Predicted: frequency, uncommon combinations, missing referral links, high costs, and visual artifacts can be legitimate; presenting them as fraud would create unsafe decisions. (*)
- **Available data sources answer different questions:** Predicted: `Folder Data Asli` supports structured claim-pattern analysis but contains no claim-document images or reviewer fraud labels, while external and synthetic datasets support document tasks but do not validate BPJS accuracy. (*)

What we know so far:

- Predicted: repository inspection shows 17 fictional physiotherapy document fixtures with expected fields and controlled cases for reuse, editing, AI-assisted creation, and poor scan quality. (*)
- Predicted: repository inspection shows that file checks, scan-quality checks, template-guided extraction, document fingerprinting, pairwise reuse checks, copy-paste checks, and parts of edit localization already have implementation baselines. (*)
- Predicted: local data inspection shows that `Folder Data Asli` contains structured membership, FKTP, FKRTL, diagnosis, procedure, referral, cost, facility, geography, and survey-weight fields, but no PDF or image claim documents. (*)
- Predicted: the 2024 FKRTL sample and privacy-safe physiotherapy extract are large enough to prototype cohort, visit-frequency, chronology, diagnosis-procedure, and cost-reference logic, subject to data-governance approval. (*)
- Predicted: no reviewed public dataset was found that exactly matches annotated BPJS SEP, Indonesian physiotherapy attendance, and supporting claim forms. (*)
- Predicted: HCFA-1500 is the closest open structured claim-form dataset, and ClinOCR-Bench is the closest open clinical-document OCR benchmark; both require later validation on authorized Indonesian forms. (*)

What we have not known:

- Whether BPJS will authorize row-level sample processing, pilot document access, or connection to an operational claim system. (*)
- Which physiotherapy document templates and required fields cover the intended pilot facilities. (*)
- The acceptable false-escalation rate and review-time target for operational users. (*)
- Whether reviewer outcomes may be retained as governed labels for future calibration. (*)
- Required document-retention, deletion, access-control, and audit policies for a BPJS pilot. (*)
- Whether licenses for every external dataset and derived model permit the intended deployment. (*)

### What are the objectives?

- Help claim reviewers reach a traceable review decision from structured claim signals and document evidence in one workflow. (*)
- Stop unreadable, unsupported, or failed analyses from being presented as passed claims. (*)
- Demonstrate retained technical capabilities using the closest permitted dataset while keeping BPJS-domain validation separate. (*)
- Make every development dataset and analysis component replaceable without changing the reviewer flow or public API contract. (*)

## Success Metrics

| Objective | Goal | Metric |
|---|---|---|
| Help reviewers reach a traceable review decision (*) | Complete the upload-to-decision flow on all release fixtures without a blocked screen (*) | `completed_review_cases / started_review_cases = 100%` across the 17 repository fixtures in the release test run (*) |
| ^ | Explain every visible label with independent findings and evidence links (*) | `labels_with_resolvable_evidence / labels_rendered = 100%`; unsupported evidence statements = 0 (*) |
| Stop unsafe passes (*) | Prevent unreadable, unsupported, or failed analysis from producing `Lolos` (*) | Count of quality-blocked, unsupported-template, or failed cases labelled `Lolos` = 0 (*) |
| ^ | Prevent a single experimental signal from producing `Prioritas` (*) | Cases where copy-paste, edit localization, or provenance alone produces `Prioritas` = 0 (*) |
| Demonstrate retained capabilities on permitted data (*) | Extract critical fields without hiding coverage failures (*) | Incorrect confident critical fields `<= 2%` on the frozen development benchmark; exact-match coverage and accuracy-when-returned reported separately (*) |
| ^ | Retrieve controlled document-reuse candidates (*) | Candidate recall `>= 95%` and confirmed-pair precision reported on controlled duplicate families (*) |
| ^ | Localize controlled traditional edits (*) | Region recall `>= 70%`; region precision and false-positive rate reported by dataset (*) |
| Keep BPJS-domain claims separate (*) | Report every result by evidence tier and dataset revision (*) | `results_with_dataset_tier_and_version / evaluation_results = 100%`; combined cross-tier “AI accuracy” values = 0 (*) |
| Keep datasets and components replaceable (*) | Run all development datasets through one adapter contract and stable service contract (*) | Adapter conformance tests pass for every enabled dataset; existing `/v1` response fields remain backward-compatible (*) |
| Guardrail (*) | Avoid presenting pattern anomalies as fraud or automatic rejection (*) | UI, API, report, and logs containing prohibited fraud verdict language = 0 in release checks (*) |

## Documentation

| Document | Link |
|---|---|
| Repository overview and current demo behavior (*) | [README](README.md) (*) |
| Existing data-aligned technical scope and local-data evidence (*) | [Technical PRD: Data-Aligned Feature Strategy](docs/technical-prd-data-aligned.md) (*) |
| PRAMANA service requirements (*) | [PRAMANA PRD](ai-service/PRD_Vedika_Autentik_PRAMANA.md) (*) |
| Backend and AI service API contract (*) | [API contract](docs/api-contract.md) (*) |
| Synthetic document fixtures and ground truth (*) | [Dataset documentation](dataset/README.md) (*) |
| AI validation method (*) | [AI validation protocol](docs/ai-validation-protocol.md) (*) |
| Closest structured medical-claim form benchmark (*) | [HCFA-1500 dataset card](https://huggingface.co/datasets/catochris/hcfa-1500) (*) |
| Clinical scanned-document OCR benchmark (*) | [ClinOCR-Bench repository](https://github.com/ClinOCR-Bench/ClinOCR-Bench) (*) |
| Mobile document-capture benchmark (*) | [SmartDoc dataset](https://sites.google.com/site/icdar15smartdoc/challenge-1/dataset) (*) |
| Traditional document-tampering benchmark (*) | [DocTamper repository](https://github.com/qcf-568/DocTamper) (*) |
| Signed-content provenance fixtures (*) | [C2PA public test files](https://github.com/c2pa-org/public-testfiles) (*) |
| Indonesian printed-text and numeric OCR supplement (*) | [CORD repository](https://github.com/clovaai/cord) (*) |
| UI design file (*) | Product design file, to be created by @product-designer (*) |
| Release evaluation report (*) | Frozen benchmark report, to be created by @qa-owner and @tech-lead (*) |

## Timeline

| Milestones | Finished by |
|---|---|
| **Finalize VPC** | 21 October 2026 (*) |
| **Solution Concept** | 22 October 2026 (*) |
| **Wireframe** | 23 October 2026 (*) |
| **Lo-Fi** | 24 October 2026 (*) |
| **Hi-Fi** | 25 October 2026 (*) |
| **1st Prototype** | 27 October 2026 (*) |
| **Feature and dataset-adapter freeze** | 28 October 2026 (*) |
| **Release candidate and frozen evaluation** | 29 October 2026 (*) |
| **Target release** | 30 October 2026 |

All dates except the target release are planning predictions and require owner confirmation. (*)

## Scope

- Interface: responsive web application for desktop claim review, with mobile layouts supported for demonstration rather than primary operation. (*)
- Product language: Bahasa Indonesia for reviewer-facing labels and explanations. (*)
- PRD language: English. (*)
- Country to launch: Indonesia. (*)
- Release type: evidence-backed prototype, not a BPJS production deployment. (*)
- Primary user: BPJS claim verifier reviewing outpatient physiotherapy claims. (*)
- Secondary users: team lead reviewing escalated cases, QA validating releases, and data or ML engineers maintaining datasets and rules. (*)
- Decision boundary: the system recommends review priority and displays evidence; a human records the claim-review decision. (*)

In Scope for v1 (MVP):

- Validate PDF and image uploads, create canonical pages, and reject unsafe or unsupported inputs. (*)
- Detect unreadable scans and route them to `Scan ulang` before content or integrity conclusions. (*)
- Extract configured medical-form fields with value, confidence, page, region, and missing-value state. (*)
- Count physiotherapy session rows on supported synthetic or configured templates and show the evidence rows. (*)
- Build a physiotherapy cohort and bounded event history from privacy-reviewed structured claim fields. (*)
- Detect visit-frequency, same-day, referral-chronology, diagnosis-procedure, and cost-reference findings without calling them fraud. (*)
- Generate exact fingerprints and retrieve near-duplicate candidates for pairwise comparison. (*)
- Run copy-paste and edited-region checks as experimental findings that require reviewer confirmation. (*)
- Combine independent findings through deterministic priority rules into `Lolos`, `Scan ulang`, `Perlu dicek`, or `Prioritas`. (*)
- Let a reviewer inspect evidence, override a suggestion with a reason, record a decision, and generate a report. (*)
- Produce weighted and unweighted offline summaries from `Folder Data Asli` where the sampling design applies. (*)
- Generate fictional claims and BPJS-like forms from privacy-safe aggregate distributions for demos and regression tests. (*)
- Convert external and future domain datasets through a versioned adapter contract. (*)
- Keep C2PA provenance verification available as optional supporting evidence when a manifest exists. (*)

Out of Scope for v1:

- Automatic fraud determination, fraud probability, or automatic claim rejection: governed fraud or reviewer labels are unavailable. (*)
- A generic AI-image detector: current evidence does not support using it as proof of document fraud. (*)
- Signature-owner identification or biometric signature verification: the required consented identity dataset is unavailable and the risk is disproportionate. (*)
- Medical-necessity, diagnosis-correctness, or treatment-appropriateness decisions: these require clinical policy and expert-labelled outcomes. (*)
- Provider or hospital risk ranking: the available structured sample has no stable provider identity suitable for this claim. (*)
- Automatic participant outreach or operational PANDAWA messaging: the repository only demonstrates a simulation. (*)
- Claims of live JKN Drive, Vedika, V-Claim, or E-Klaim integration: no authorized production connection is in scope. (*)
- Claims of BPJS accuracy, prevented leakage, or financial savings: these require an approved governed pilot. (*)
- Training or commercial deployment using a non-commercial dataset without written legal approval. (*)
- Treating high frequency, high cost, uncommon combinations, missing links, document metadata, or bad scan quality as proof of fraud. (*)

Core Hypothesis: We believe a BPJS claim verifier will use a combined evidence view to complete a physiotherapy claim review because it shows traceable structured and document findings; we will consider the prototype hypothesis supported when all release fixtures complete the review flow, every label resolves to evidence, and no blocked or failed analysis becomes `Lolos`. (*)

### Kept Feature and Data Matrix

| Feature | Current repository status | `Folder Data Asli` support | Additional evidence | Release decision |
|---|---|---|---|---|
| Physiotherapy cohort identification (*) | Partial analysis baseline (*) | Yes: clinic, diagnosis, procedure, and service-level fields (*) | Privacy review and reproducible manifest (*) | Keep as core (*) |
| Visit-frequency analysis (*) | Partial baseline (*) | Yes: pseudonymous participant and service date (*) | Frozen rules and injected-anomaly tests (*) | Keep and expand (*) |
| Same-day or closely spaced claim detection (*) | Partial baseline (*) | Yes: participant and service date (*) | Explainable chronology fixtures (*) | Keep and expand (*) |
| Referral chronology (*) | Not complete (*) | Partial: referral linkage exists with missing values (*) | Missing-link behavior and chronology fixtures (*) | Add as core where linkage exists (*) |
| Diagnosis-procedure pattern analysis (*) | Not complete (*) | Yes: diagnosis and procedure fields (*) | Minimum support and reference-cohort rules (*) | Add as review evidence (*) |
| Cost-reference analysis (*) | Partial baseline (*) | Yes: billed, verified, and peer fields (*) | Median, IQR, p95, and subgroup checks (*) | Keep and expand (*) |
| Weighted population summaries (*) | Not complete (*) | Yes: `PSTV15` and survey strata (*) | Reconciliation with official analysis scripts (*) | Add as offline support (*) |
| Data-driven fictional claim generation (*) | Generic synthetic fixtures exist (*) | Yes through privacy-safe aggregates (*) | Disclosure-risk review and deterministic seeds (*) | Add for demos and tests (*) |
| File validation and canonical rendering (*) | Implemented baseline (*) | No document files (*) | Malformed and multi-page fixtures (*) | Keep as core (*) |
| Scan-quality detection (*) | Implemented baseline (*) | No document files (*) | ClinOCR-Bench, SmartDoc, and Indonesian volunteer captures (*) | Keep as core (*) |
| Medical-form OCR and field extraction (*) | Implemented baseline (*) | No document files (*) | HCFA-1500 and ClinOCR-Bench; CORD only as Indonesian OCR supplement (*) | Keep as core (*) |
| Physiotherapy session-row counting (*) | Implemented on synthetic templates (*) | No document files or billed-session field (*) | BPJS-like synthetic and authorized volunteer forms (*) | Keep as experimental (*) |
| Exact-document fingerprinting (*) | Implemented baseline (*) | No document files (*) | Controlled duplicate families (*) | Keep as core (*) |
| Near-duplicate reuse detection (*) | Implemented baseline (*) | No document files (*) | Controlled genuine neighbors and duplicate families (*) | Keep with human review (*) |
| Within-document copy-paste detection (*) | Implemented baseline (*) | No document files (*) | DocTamper and controlled medical-form edits (*) | Keep as experimental (*) |
| Edited text or number localization (*) | Partial baseline (*) | No document files (*) | DocTamper and controlled BPJS-like alterations (*) | Keep as experimental (*) |
| Metadata and C2PA provenance checks (*) | Supporting baseline only (*) | No document files (*) | C2PA positive, invalid, and untrusted fixtures (*) | Keep in architecture; optional in UI (*) |

### Evidence Tiers

| Tier | Data | Permitted product claim |
|---|---|---|
| A (*) | `Folder Data Asli` structured samples (*) | Structured sample patterns and schema feasibility only (*) |
| B (*) | Vedika synthetic documents and generated claims (*) | Workflow, API, regression, and controlled manipulation behavior only (*) |
| C (*) | External document benchmarks (*) | Capability on that dataset's documented task and domain only (*) |
| D (*) | Future consented Indonesian medical forms (*) | Indonesian form calibration within the consented collection only (*) |
| E (*) | Future approved BPJS pilot data (*) | BPJS-domain performance and operational findings within the governed pilot only (*) |

Results from different tiers must remain separate in dashboards, reports, and release claims. (*)

## Discussions (Optional)

| Question | Answer | Date Answered |
|---|---|---|
| Which BPJS claim fields and document templates are authorized for the first pilot? (*) | Open (*) | Not answered (*) |
| Who owns the deterministic priority thresholds and approves changes? (*) | Open (*) | Not answered (*) |
| What document-retention and deletion policy applies during a pilot? (*) | Open (*) | Not answered (*) |
| Can reviewer decisions be stored and reused as governed calibration labels? (*) | Open (*) | Not answered (*) |
| Which external dataset licenses permit training, redistribution, and commercial deployment? (*) | Open (*) | Not answered (*) |
| What false-escalation rate and review-time reduction are acceptable to operations? (*) | Open (*) | Not answered (*) |

## Competitive Analysis (Optional)

| Competitor Name | Observation | Notes |
|---|---|---|
| Manual claim review using separate document and claim-history views (*) | Predicted: reviewers may switch between files, tables, and notes to assemble one decision; this observation may be out of date. (*) | The MVP should keep all findings, source fields, image regions, and reviewer actions in one case view. (*) |
| Rule-only claim anomaly reports (*) | Predicted: rule outputs may identify unusual frequency or cost without showing document evidence; this observation may be out of date. (*) | Structured anomalies remain independent findings and cannot establish document manipulation. (*) |
| Generic OCR or document extraction services (*) | Predicted: these services may return text or key-value pairs but may not apply the required safe-failure and review-label policy; this observation may be out of date. (*) | The product must preserve missing values, confidence, regions, and component versions rather than returning text alone. (*) |
| Generic image-forensics tools (*) | Predicted: these tools may identify visual artifacts without claim context and may produce false positives on scans; this observation may be out of date. (*) | Visual signals stay experimental and require a reviewer to confirm relevance. (*) |
| Current repository demo using fixture ground truth (*) | Predicted: the demo explains the intended workflow but does not prove that the analysis service produced each finding; this observation may be out of date after integration. (*) | The release should expose evidence source and component version so fixture output and real analysis are distinguishable. (*) |

## Product Requirement

**App Overview:**

Vedika Autentik is a web-based verifier-assistance product for outpatient physiotherapy claims. A verifier opens a case, uploads or views supporting documents, runs document and claim-context checks, reviews traceable findings, records a decision, and exports a report. PRAMANA returns evidence; backend rules assign review priority; the verifier owns the final decision. (*)

**User Story**

As a BPJS claim verifier, I want one evidence view for supporting documents and structured claim history so that I can prioritize and document my review without treating an automated signal as a fraud verdict. (*)

**Feature List vs Importance (MVP)**

| User Flow | User Story | Requirement | Importance |
|---|---|---|---|
| **EPIC 1: Document Intake** (*) | **Feature 1.1: File validation and canonical rendering**<br>As a claim verifier, I want an uploaded file validated and normalized so that every later check receives safe, predictable pages. (*) | The system should accept configured PDF and image types, enforce size and page limits, reject unsafe or malformed files, remove active content, correct page orientation where supported, and create a stable page representation with a file checksum. (*) | P1 - MVP (*) |
| ^ | **Feature 1.2: Scan-quality gate**<br>As a claim verifier, I want unreadable scans identified before content checks so that uncertain extraction cannot pass a case. (*) | The system should report blur, crop, perspective, lighting, occlusion, and unreadable-text evidence by page; a blocking quality result should produce `Scan ulang` and stop authenticity conclusions. (*) | P1 - MVP (*) |
| **EPIC 2: Medical-Form Extraction** (*) | **Feature 2.1: Field extraction with grounding**<br>As a claim verifier, I want extracted claim fields linked to their page regions so that I can verify them against the document. (*) | The system should return configured fields with normalized value, raw text, confidence, page, bounding region, extraction status, template ID, and component version; unknown values remain null. (*) | P1 - MVP (*) |
| ^ | **Feature 2.2: Physiotherapy session-row counting**<br>As a claim verifier, I want detected attendance rows and session dates shown so that I can compare documented sessions with claim context. (*) | On a supported template, the system should identify session rows, return each row's date and region where available, count only grounded rows, and mark the output experimental. (*) | P2 - Experimental (*) |
| **EPIC 3: Structured Claim Intelligence** (*) | **Feature 3.1: Physiotherapy cohort and bounded history**<br>As a claim verifier, I want the relevant participant history selected consistently so that findings use the intended physiotherapy reference context. (*) | The backend should construct a reproducible cohort and bounded event history using approved pseudonymous participant, clinic, diagnosis, procedure, service-level, and date fields; it should attach the cohort definition and data revision. (*) | P1 - MVP (*) |
| ^ | **Feature 3.2: Visit-frequency and same-day findings**<br>As a claim verifier, I want unusual visit frequency and overlapping service dates explained so that I can decide whether the pattern needs review. (*) | The service should calculate daily, weekly, and monthly counts, identify same-day or configured close-date events, and return contributing dates, counts, rule version, and reference context without a fraud label. (*) | P1 - MVP (*) |
| ^ | **Feature 3.3: Referral chronology**<br>As a claim verifier, I want linked referral and service dates checked so that missing or inconsistent sequences are visible. (*) | Where linkage exists, the service should compare referral and service chronology and distinguish valid, inconsistent, missing-link, and unavailable states; missing data should not be treated as inconsistency. (*) | P1 - MVP (*) |
| ^ | **Feature 3.4: Diagnosis-procedure pattern**<br>As a claim verifier, I want an uncommon diagnosis-procedure combination identified with supporting counts so that I can inspect it without assuming it is incorrect. (*) | The service should compare the combination with a versioned reference cohort, enforce minimum cell rules, and return count, denominator, reference cohort, and `uncommon in sample` wording. (*) | P2 (*) |
| ^ | **Feature 3.5: Cost reference**<br>As a claim verifier, I want billed and verified costs compared with an appropriate peer reference so that unusual values receive proportionate review. (*) | The service should return median, IQR, p95, median absolute deviation, contributing cost field, peer definition, and data revision; it should avoid a fraud conclusion. (*) | P2 (*) |
| **EPIC 4: Document Integrity** (*) | **Feature 4.1: Exact-document fingerprint**<br>As a claim verifier, I want exact repeated files found so that I can inspect duplicate submissions. (*) | The backend should compare a masked canonical fingerprint against an authorized archive, return exact-match candidates and source case IDs, and exclude configured identity regions from matching where required. (*) | P1 - MVP (*) |
| ^ | **Feature 4.2: Near-duplicate reuse confirmation**<br>As a claim verifier, I want visually similar prior documents compared side by side so that I can distinguish reuse from common templates. (*) | The system should retrieve bounded candidates, align the selected pair, display matching and differing regions, report similarity and method version, and require reviewer confirmation before a reuse finding affects priority. (*) | P1 - MVP (*) |
| ^ | **Feature 4.3: Within-document copy-paste detection**<br>As a claim verifier, I want repeated regions highlighted so that I can inspect possible copied entries. (*) | The system should return candidate source and destination regions, confidence, and method version; the UI should label the result experimental and allow dismissal. (*) | P2 - Experimental (*) |
| ^ | **Feature 4.4: Edited text or number localization**<br>As a claim verifier, I want suspected altered regions highlighted so that I can compare them with the original document context. (*) | The system should return suspected regions and supporting signals without reconstructing an original value or claiming intent; the UI should label the result experimental. (*) | P2 - Experimental (*) |
| ^ | **Feature 4.5: C2PA provenance check**<br>As a claim verifier, I want signed provenance shown when present so that I can inspect its validity as supporting evidence. (*) | The system should classify manifests as valid, invalid, untrusted, or absent; absence must remain neutral and provenance alone must not produce `Prioritas`. (*) | P3 - Optional (*) |
| **EPIC 5: Review and Decision** (*) | **Feature 5.1: Evidence view and deterministic label**<br>As a claim verifier, I want each label traced to independent findings so that I can understand why the case was prioritized. (*) | The backend should calculate `Lolos`, `Scan ulang`, `Perlu dicek`, or `Prioritas` from versioned rules; the UI should show finding source, strength, evidence, limitations, and recommended next action. (*) | P1 - MVP (*) |
| ^ | **Feature 5.2: Reviewer decision and audit trail**<br>As a claim verifier, I want to accept or override the suggestion with a reason so that accountability stays with the reviewer. (*) | The backend should record the selected action, reason, reviewer pseudonymous ID, timestamp, finding versions, previous state, and case revision; overrides should never rewrite model output. (*) | P1 - MVP (*) |
| ^ | **Feature 5.3: Review report**<br>As a claim verifier, I want a case report so that the evidence and decision can be handed to an authorized next reviewer. (*) | The system should generate a PDF containing case metadata, findings, evidence references, limitations, decision, reason, component versions, and a statement that findings are not a fraud verdict. (*) | P2 (*) |
| **EPIC 6: Data and Evaluation Infrastructure** (*) | **Feature 6.1: Weighted and unweighted summaries**<br>As a data analyst, I want both sample and population-aware statistics so that prototype thresholds are not based on unlabelled aggregation choices. (*) | The offline pipeline should use `PSTV15` and documented strata where applicable, retain unweighted counts, apply minimum-cell suppression, and publish a reconciliation report. (*) | P2 (*) |
| ^ | **Feature 6.2: Fictional claim and form factory**<br>As a QA engineer, I want reproducible fictional cases so that every rule and document check has privacy-safe positive and negative tests. (*) | The factory should generate fictional identities, claims, histories, BPJS-like forms, controlled duplicate families, capture degradation, exact edit masks, expected findings, and deterministic seeds from approved aggregate distributions. (*) | P2 (*) |
| ^ | **Feature 6.3: Dataset adapters and benchmark manifests**<br>As an ML engineer, I want each dataset converted to one versioned contract so that development data can be replaced without rewriting the service or reviewer UI. (*) | Each adapter should output the common `DocumentSample` contract, enforce base-document split isolation, record license and checksum, and produce frozen development and test manifests. (*) | P1 - MVP enabler (*) |

## Technical Architecture and Contracts

### Component ownership

| Component | Responsibility |
|---|---|
| Frontend (*) | Reviewer queue, upload state, evidence viewer, pairwise comparison, decision form, report request, and user-facing limitations. (*) |
| Backend (*) | Authentication, authorization, raw-file storage, jobs, bounded claim context, candidate retrieval, deterministic labels, decisions, audit trail, retention, and reports. (*) |
| PRAMANA service (*) | Stateless document normalization, quality analysis, extraction, pairwise comparison, document forensics, and structured claim findings. (*) |
| Offline data and evaluation (*) | Privacy-reviewed BPJS aggregates, fictional case generation, dataset adapters, frozen manifests, benchmark runner, and release reports. (*) |

### Service flow

1. The backend accepts an authorized file and optional normalized claim context, stores the raw file outside application logs, and creates an analysis job. (*)
2. PRAMANA validates and canonicalizes the document, then runs the quality gate. (*)
3. A blocking quality result returns evidence and stops extraction-dependent integrity checks. (*)
4. A readable document proceeds through field extraction, session-row analysis, fingerprints, bounded candidate comparison, edit checks, and optional provenance checks. (*)
5. The backend supplies a bounded structured event history to claim-analysis rules; raw `Folder Data Asli` is never queried by the runtime service. (*)
6. PRAMANA returns independent findings with evidence IDs and component versions; it does not return the final case label. (*)
7. The backend applies deterministic label rules, and the verifier records the final review action. (*)

### API surface

| Method and path | Decision |
|---|---|
| `GET /v1/kesehatan` (*) | Retain as service health and component-version endpoint. (*) |
| `POST /v1/analisis` (*) | Retain for one-document validation, quality, extraction, fingerprint, forensics, and provenance findings. (*) |
| `POST /v1/bandingkan` (*) | Retain for bounded pairwise reuse comparison. (*) |
| `POST /v1/analisis-klaim` (*) | Add for normalized current claim and bounded history analysis. (*) |

Every finding should include `evidence_id`, `finding_type`, `strength`, `explanation_id`, supporting fields or regions, `component_version`, `dataset_or_rule_revision`, and limitations. Missing values remain null; claim context must never be copied into OCR output. (*)

### Finding types and label policy

| Finding type | Source | Permitted effect |
|---|---|---|
| `kualitas_dokumen` (*) | Document quality gate (*) | May produce `Scan ulang`; cannot imply fraud. (*) |
| `ketidakkonsistenan_dokumen` (*) | Grounded extraction and claim comparison (*) | May contribute to `Perlu dicek` or a multi-signal `Prioritas`. (*) |
| `anomali_frekuensi` (*) | Structured claim history (*) | Review evidence only; cannot establish manipulation. (*) |
| `anomali_duplikat` (*) | Exact or reviewer-confirmed near duplicate (*) | May contribute to priority with linked evidence. (*) |
| `ketidakkonsistenan_kronologi` (*) | Referral and service chronology (*) | Review evidence; missing link stays separate from inconsistency. (*) |
| `kombinasi_jarang` (*) | Diagnosis-procedure reference (*) | `Uncommon in sample` only; cannot assert incorrect care. (*) |
| `anomali_biaya` (*) | Peer cost reference (*) | Review evidence only. (*) |
| `forensik_visual` (*) | Copy-paste or edited-region methods (*) | Experimental; cannot independently produce `Prioritas`. (*) |
| `provenance_dokumen` (*) | C2PA manifest validation (*) | Supporting evidence only; absence is neutral. (*) |

- `Lolos`: all required checks completed, no active findings remain, and available claim context is consistent. (*)
- `Scan ulang`: quality prevents reliable analysis; extraction-dependent checks stop. (*)
- `Perlu dicek`: one uncertain or moderate signal, unsupported template, missing required analysis, or service failure needs human review. (*)
- `Prioritas`: versioned deterministic rules find multiple independent strong signals, or one confirmed strong signal plus another independent finding. (*)

### Dataset adapter contract

Each adapter should return a `DocumentSample` with `sample_id`, `source_dataset`, `license_id`, `evidence_tier`, `base_document_id`, pages, fields with values and regions, quality labels, manipulation type and mask, duplicate-family ID, provenance expectation, and split. All derivatives of one base document should stay in the same split. (*)

### Dataset strategy

| Capability | Primary development data | Limitation |
|---|---|---|
| Claim-form field extraction (*) | HCFA-1500 (*) | Synthetic US CMS-1500 forms; small; not BPJS or Indonesian. (*) |
| Clinical OCR and scan artifacts (*) | ClinOCR-Bench (*) | Synthetic clinical content; transcription focus rather than BPJS claim validation. (*) |
| Mobile capture quality (*) | SmartDoc (*) | Generic documents rather than medical forms. (*) |
| Indonesian printed OCR supplement (*) | CORD v2 (*) | Receipts rather than medical forms; supplemental use only. (*) |
| Handwritten medical text exploration (*) | Consented fictional volunteer forms or a separately approved prescription dataset (*) | Prescription text does not validate claim-form structure. (*) |
| Traditional edit localization (*) | DocTamper and controlled Vedika edits (*) | License review required; not BPJS-specific. (*) |
| Signed provenance (*) | C2PA public test files (*) | Most scans may have no manifest, and absence proves nothing. (*) |
| Structured claim patterns (*) | Privacy-reviewed aggregates from `Folder Data Asli` (*) | No document images, session-billed field, stable provider ID, fraud labels, or reviewer labels. (*) |

### Privacy, security, and governance

- Never commit raw BPJS rows, participant-level derivatives, external dataset copies, or volunteer captures. (*)
- Do not log names, claim identifiers, OCR text, filenames, document bytes, or full claim payloads. (*)
- Encrypt documents in transit and at rest, restrict case access by role, and audit every view, download, decision, and deletion. (*)
- Define retention and deletion before any non-synthetic upload is permitted. (*)
- Publish aggregates only after minimum-cell suppression and privacy review. (*)
- Record dataset revision, source checksum, license, split manifest, component version, thresholds, and evaluation environment for every release result. (*)
- Require governance approval before reviewer outcomes become training or calibration data. (*)

## Acceptance Criteria

| User Flow | User Story | Screen | Acceptance Criteria | Positive Flow |
|---|---|---|---|---|
| **EPIC 1: Document Intake** (*) | **Feature 1.1: File validation and canonical rendering** (*) | Claim upload (*) | The UI lists accepted types and limits; the backend verifies file signature rather than extension alone; accepted files receive a checksum and canonical page count; active content is not executed. (*) | POSITIVE:<br>1. The verifier uploads a permitted readable file.<br>2. The backend validates it and creates canonical pages.<br>3. The case shows `Ready for analysis`. (*) |
| ^ | ^ | Claim upload (*) | ^ | NEGATIVE:<br>1. The verifier uploads a malformed, oversized, encrypted, or unsupported file.<br>2. The system rejects it with a specific reason and does not start analysis.<br>3. The verifier can choose another file. (*) |
| ^ | **Feature 1.2: Scan-quality gate** (*) | Analysis progress and evidence view (*) | Every page receives quality evidence; blocking quality stops dependent checks; the case becomes `Scan ulang`; scan quality never appears as fraud evidence. (*) | POSITIVE:<br>1. The verifier analyzes a readable scan.<br>2. Quality checks pass.<br>3. Extraction and integrity checks continue. (*) |
| ^ | ^ | Analysis progress and evidence view (*) | ^ | NEGATIVE:<br>1. The file is blurred or materially cropped.<br>2. The system highlights the affected page and reason.<br>3. The case becomes `Scan ulang`, and the verifier can request a new scan. (*) |
| **EPIC 2: Medical-Form Extraction** (*) | **Feature 2.1: Field extraction with grounding** (*) | Document evidence viewer (*) | Returned fields show raw text, normalized value, confidence, page, region, status, and version; missing values stay null; selecting a field focuses its region. (*) | POSITIVE:<br>1. The verifier opens a supported readable form.<br>2. The system extracts configured fields.<br>3. Selecting a field highlights its source region. (*) |
| ^ | ^ | Document evidence viewer (*) | ^ | NEGATIVE:<br>1. The document uses an unsupported template or a field is uncertain.<br>2. The system returns null or `unsupported` rather than copying claim context.<br>3. The case becomes `Perlu dicek` when the missing analysis is required. (*) |
| ^ | **Feature 2.2: Physiotherapy session-row counting** (*) | Session evidence panel (*) | Only grounded rows count as sessions; each detected row links to a region; the UI shows the experimental label and documented count separately from billed context. (*) | POSITIVE:<br>1. The verifier opens a supported physiotherapy form.<br>2. The system lists grounded session rows and dates.<br>3. The panel shows the documented count and comparison context. (*) |
| ^ | ^ | Session evidence panel (*) | ^ | NEGATIVE:<br>1. Rows are handwritten, merged, or outside supported layout.<br>2. The system marks the count incomplete or unavailable.<br>3. It does not infer missing rows from billed sessions. (*) |
| **EPIC 3: Structured Claim Intelligence** (*) | **Feature 3.1: Physiotherapy cohort and bounded history** (*) | Claim-context panel (*) | The case shows cohort revision, history window, included event count, and available fields; only approved pseudonymous data enters the analysis request. (*) | POSITIVE:<br>1. The backend receives a claim with an approved participant key.<br>2. It builds the bounded physiotherapy history.<br>3. The panel shows the history and revision used. (*) |
| ^ | ^ | Claim-context panel (*) | ^ | NEGATIVE:<br>1. The participant key or required context is unavailable.<br>2. The backend returns `claim_context_unavailable`.<br>3. Document analysis continues, and the UI states which structured checks were skipped. (*) |
| ^ | **Feature 3.2: Visit-frequency and same-day findings** (*) | Claim-history evidence panel (*) | Findings list contributing dates, daily, weekly, and monthly counts, rule version, and reference context; they use `unusual pattern` wording rather than fraud language. (*) | POSITIVE:<br>1. The bounded history contains repeated or same-day events that meet a configured rule.<br>2. The service returns the finding and contributing events.<br>3. The verifier can inspect each date. (*) |
| ^ | ^ | Claim-history evidence panel (*) | ^ | NEGATIVE:<br>1. History is incomplete or the rule cannot calculate a reference.<br>2. The system reports `insufficient context`.<br>3. It does not create a frequency finding or `Lolos` from the missing check. (*) |
| ^ | **Feature 3.3: Referral chronology** (*) | Chronology panel (*) | The panel distinguishes consistent, inconsistent, missing-link, and unavailable states; an inconsistency cites the dates and linkage used. (*) | POSITIVE:<br>1. A linked referral and service sequence is available.<br>2. The service evaluates the sequence.<br>3. An inconsistent sequence shows the exact dates and rule. (*) |
| ^ | ^ | Chronology panel (*) | ^ | NEGATIVE:<br>1. The referral link is missing.<br>2. The panel displays `link unavailable`.<br>3. The system does not relabel it as inconsistent. (*) |
| ^ | **Feature 3.4: Diagnosis-procedure pattern** (*) | Claim-pattern panel (*) | The result shows combination, count, denominator, cohort, revision, and minimum-cell handling; wording is `uncommon in the reference sample`. (*) | POSITIVE:<br>1. The combination has enough reference support for calculation.<br>2. The service returns its frequency context.<br>3. The verifier sees supporting counts. (*) |
| ^ | ^ | Claim-pattern panel (*) | ^ | NEGATIVE:<br>1. The cell is below the privacy or stability threshold.<br>2. Counts are suppressed.<br>3. No uncommon-combination finding is returned. (*) |
| ^ | **Feature 3.5: Cost reference** (*) | Cost evidence panel (*) | The panel shows compared cost, peer definition, median, IQR, p95, median absolute deviation, and revision; it separates billed and verified costs. (*) | POSITIVE:<br>1. An eligible peer cohort exists.<br>2. The service computes the reference statistics.<br>3. The verifier sees the compared value and distribution summary. (*) |
| ^ | ^ | Cost evidence panel (*) | ^ | NEGATIVE:<br>1. No eligible peer cohort or cost value exists.<br>2. The panel shows `reference unavailable`.<br>3. The system does not substitute a global reference silently. (*) |
| **EPIC 4: Document Integrity** (*) | **Feature 4.1: Exact-document fingerprint** (*) | Duplicate-candidate panel (*) | Fingerprints use canonical pages and configured masks; exact candidates show authorized source case IDs and timestamps; access checks apply to source cases. (*) | POSITIVE:<br>1. An uploaded document matches an authorized prior fingerprint.<br>2. The backend returns the source candidate.<br>3. The verifier can open the comparison. (*) |
| ^ | ^ | Duplicate-candidate panel (*) | ^ | NEGATIVE:<br>1. A matching source case is outside the verifier's access scope.<br>2. The backend withholds source details.<br>3. The UI does not expose the restricted case. (*) |
| ^ | **Feature 4.2: Near-duplicate reuse confirmation** (*) | Pairwise comparison (*) | The viewer aligns both documents, shows matching and differing regions, method version, and similarity; reviewer confirmation is required before the finding affects priority. (*) | POSITIVE:<br>1. The verifier opens a retrieved candidate.<br>2. The system aligns the pair and displays evidence.<br>3. The verifier confirms or dismisses document reuse. (*) |
| ^ | ^ | Pairwise comparison (*) | ^ | NEGATIVE:<br>1. Alignment fails or similarity is below the review threshold.<br>2. The UI shows an inconclusive comparison.<br>3. No confirmed-reuse finding is created. (*) |
| ^ | **Feature 4.3: Within-document copy-paste detection** (*) | Forensic evidence panel (*) | Candidate source and destination regions, confidence, and method version are shown; the panel says `Experimental`; dismissal is available. (*) | POSITIVE:<br>1. The method finds a controlled copied region.<br>2. The UI highlights both regions.<br>3. The verifier confirms or dismisses relevance. (*) |
| ^ | ^ | Forensic evidence panel (*) | ^ | NEGATIVE:<br>1. Repeated table lines or stamps create a likely false positive.<br>2. The verifier dismisses the finding with a reason.<br>3. The dismissal remains in the audit trail and removes the finding from active label calculation. (*) |
| ^ | **Feature 4.4: Edited text or number localization** (*) | Forensic evidence panel (*) | Suspected regions and supporting visual signals are shown without an invented original value; the panel says `Experimental`; one signal alone cannot create `Prioritas`. (*) | POSITIVE:<br>1. A controlled numeric edit produces a candidate region.<br>2. The UI highlights the region and limitation.<br>3. The verifier compares it with surrounding content. (*) |
| ^ | ^ | Forensic evidence panel (*) | ^ | NEGATIVE:<br>1. Compression or a scan artifact triggers a weak signal.<br>2. The UI keeps it non-decisive or lets the verifier dismiss it.<br>3. The case cannot become `Prioritas` from that signal alone. (*) |
| ^ | **Feature 4.5: C2PA provenance check** (*) | Provenance details (*) | Valid, invalid, untrusted, and absent states are distinct; signer and assertion details appear only when available; absence is neutral. (*) | POSITIVE:<br>1. A file contains a testable manifest.<br>2. The system validates its signature and trust state.<br>3. The verifier sees the result as supporting evidence. (*) |
| ^ | ^ | Provenance details (*) | ^ | NEGATIVE:<br>1. A scan has no C2PA manifest.<br>2. The UI shows `No provenance manifest` without warning color or fraud wording.<br>3. The label does not change. (*) |
| **EPIC 5: Review and Decision** (*) | **Feature 5.1: Evidence view and deterministic label** (*) | Case detail (*) | Every label resolves to active findings; each finding shows source, evidence, version, limitation, and suggested action; failures cannot produce `Lolos`. (*) | POSITIVE:<br>1. All required analyses complete.<br>2. The backend calculates the label from versioned rules.<br>3. The verifier opens each contributing finding and evidence item. (*) |
| ^ | ^ | Case detail (*) | ^ | NEGATIVE:<br>1. A required component times out or returns an unsupported state.<br>2. The case becomes `Perlu dicek` and names the incomplete check.<br>3. Retry is available to an authorized verifier. (*) |
| ^ | **Feature 5.2: Reviewer decision and audit trail** (*) | Decision form and case history (*) | The verifier can accept or override with a required reason; the audit entry stores actor, time, prior state, selected action, reason, and versions; model output remains unchanged. (*) | POSITIVE:<br>1. The verifier reviews all evidence.<br>2. The verifier selects an action and enters a reason.<br>3. The system saves the decision and audit entry. (*) |
| ^ | ^ | Decision form and case history (*) | ^ | NEGATIVE:<br>1. The verifier attempts to submit an override without a reason.<br>2. The form shows a reason-required error and preserves entered data.<br>3. No decision is saved until corrected. (*) |
| ^ | **Feature 5.3: Review report** (*) | Report preview and download (*) | The PDF includes case metadata, findings, evidence references, limitations, decision, reason, versions, and non-fraud disclaimer; access and download are audited. (*) | POSITIVE:<br>1. An authorized verifier requests a report for a decided case.<br>2. The backend generates the PDF from the recorded revision.<br>3. The verifier downloads it and an audit event is stored. (*) |
| ^ | ^ | Report preview and download (*) | ^ | NEGATIVE:<br>1. The case has no saved decision or the requester lacks permission.<br>2. The backend blocks generation and gives the applicable reason.<br>3. No incomplete or unauthorized report is downloaded. (*) |
| **EPIC 6: Data and Evaluation Infrastructure** (*) | **Feature 6.1: Weighted and unweighted summaries** (*) | Offline release report (*) | The pipeline states weight, strata, inclusion rules, suppression rules, raw count, weighted estimate, and revision; weighted and unweighted values are not mixed. (*) | POSITIVE:<br>1. The analyst runs a versioned aggregate job.<br>2. The pipeline produces both permitted summaries and reconciliation checks.<br>3. The release report cites the manifest. (*) |
| ^ | ^ | Offline release report (*) | ^ | NEGATIVE:<br>1. Weight or strata fields are missing for a required estimate.<br>2. The pipeline fails that estimate with an explicit error.<br>3. It does not publish an unweighted value as population-aware. (*) |
| ^ | **Feature 6.2: Fictional claim and form factory** (*) | Developer command and fixture manifest (*) | Generated cases use fictional identities, deterministic seeds, source aggregate revision, expected findings, and exact controlled transformations; no row-level source record is recoverable. (*) | POSITIVE:<br>1. QA runs the generator with a fixed seed.<br>2. It creates the same fictional case family and manifest.<br>3. Regression tests consume the expected findings. (*) |
| ^ | ^ | Developer command and fixture manifest (*) | ^ | NEGATIVE:<br>1. Privacy checks detect a forbidden direct identifier or source-row copy.<br>2. Generation fails before files are published.<br>3. The error identifies the failed policy without printing sensitive content. (*) |
| ^ | **Feature 6.3: Dataset adapters and benchmark manifests** (*) | Evaluation command and report (*) | Every sample contains required contract fields; derivatives share the base-document split; license, checksum, and revision are recorded; frozen test data is not used for tuning. (*) | POSITIVE:<br>1. An engineer runs an enabled adapter.<br>2. Contract and split checks pass.<br>3. The benchmark runner produces a versioned report. (*) |
| ^ | ^ | Evaluation command and report (*) | ^ | NEGATIVE:<br>1. An adapter omits license data, breaks split isolation, or changes a frozen checksum.<br>2. Validation fails before evaluation.<br>3. The release report is not marked publishable. (*) |

## Event Tracker (Optional)

Event names use `<EPIC>_<Name>_<Type>`. No event property may contain names, raw identifiers, OCR text, filenames, images, document bytes, or full claim payloads. (*)

| User Flow | User Story | Event Tracker |
|---|---|---|
| **EPIC 1: Document Intake** (*) | **Feature 1.1: File validation and canonical rendering** (*) | `INT_UploadStarted_Action` {case_revision, file_type_group}<br>`INT_FileValidated_Result` {outcome, reason_code, page_count_group}<br>`INT_FileRejected_Error` {reason_code} (*) |
| ^ | **Feature 1.2: Scan-quality gate** (*) | `INT_QualityChecked_Result` {outcome, issue_codes, affected_page_count}<br>`INT_RescanRequested_Action` {issue_codes} (*) |
| **EPIC 2: Medical-Form Extraction** (*) | **Feature 2.1: Field extraction with grounding** (*) | `EXT_ExtractionCompleted_Result` {template_id, returned_field_count, missing_field_count, component_version}<br>`EXT_FieldEvidenceOpened_Action` {field_type, page_number} (*) |
| ^ | **Feature 2.2: Physiotherapy session-row counting** (*) | `EXT_SessionsCounted_Result` {outcome, grounded_row_count, component_version}<br>`EXT_SessionEvidenceOpened_Action` {row_index} (*) |
| **EPIC 3: Structured Claim Intelligence** (*) | **Feature 3.1: Physiotherapy cohort and bounded history** (*) | `CLM_ContextBuilt_Result` {outcome, event_count_group, cohort_revision}<br>`CLM_ContextOpened_Action` {case_revision} (*) |
| ^ | **Feature 3.2: Visit-frequency and same-day findings** (*) | `CLM_FrequencyChecked_Result` {outcome, finding_count, rule_version}<br>`CLM_FrequencyEvidenceOpened_Action` {finding_type} (*) |
| ^ | **Feature 3.3: Referral chronology** (*) | `CLM_ChronologyChecked_Result` {state, rule_version}<br>`CLM_ChronologyEvidenceOpened_Action` {state} (*) |
| ^ | **Feature 3.4: Diagnosis-procedure pattern** (*) | `CLM_CombinationChecked_Result` {outcome, suppressed, reference_revision}<br>`CLM_CombinationEvidenceOpened_Action` {outcome} (*) |
| ^ | **Feature 3.5: Cost reference** (*) | `CLM_CostChecked_Result` {outcome, peer_group_id, reference_revision}<br>`CLM_CostEvidenceOpened_Action` {cost_type} (*) |
| **EPIC 4: Document Integrity** (*) | **Feature 4.1: Exact-document fingerprint** (*) | `DOC_FingerprintChecked_Result` {outcome, authorized_candidate_count, component_version}<br>`DOC_ExactCandidateOpened_Action` {candidate_rank} (*) |
| ^ | **Feature 4.2: Near-duplicate reuse confirmation** (*) | `DOC_NearDuplicateRetrieved_Result` {candidate_count, component_version}<br>`DOC_PairCompared_Result` {outcome, similarity_band}<br>`DOC_ReuseReviewed_Action` {decision, reason_code} (*) |
| ^ | **Feature 4.3: Within-document copy-paste detection** (*) | `DOC_CopyPasteChecked_Result` {outcome, region_count, component_version}<br>`DOC_CopyPasteReviewed_Action` {decision, reason_code} (*) |
| ^ | **Feature 4.4: Edited text or number localization** (*) | `DOC_EditChecked_Result` {outcome, region_count, component_version}<br>`DOC_EditReviewed_Action` {decision, reason_code} (*) |
| ^ | **Feature 4.5: C2PA provenance check** (*) | `DOC_ProvenanceChecked_Result` {state, component_version}<br>`DOC_ProvenanceOpened_Action` {state} (*) |
| **EPIC 5: Review and Decision** (*) | **Feature 5.1: Evidence view and deterministic label** (*) | `REV_CaseOpened_Page` {suggested_label, finding_count}<br>`REV_LabelCalculated_Result` {label, rule_version, incomplete_component_count}<br>`REV_EvidenceOpened_Action` {finding_type, evidence_type} (*) |
| ^ | **Feature 5.2: Reviewer decision and audit trail** (*) | `REV_DecisionStarted_Action` {suggested_label}<br>`REV_DecisionSubmitted_Action` {selected_action, override, reason_code}<br>`REV_DecisionRejected_Error` {reason_code} (*) |
| ^ | **Feature 5.3: Review report** (*) | `REV_ReportRequested_Action` {case_state}<br>`REV_ReportGenerated_Result` {outcome, case_revision}<br>`REV_ReportDownloaded_Action` {case_revision} (*) |
| **EPIC 6: Data and Evaluation Infrastructure** (*) | **Feature 6.1: Weighted and unweighted summaries** (*) | `DAT_AggregateJobCompleted_Result` {outcome, data_revision, suppressed_cell_count} (*) |
| ^ | **Feature 6.2: Fictional claim and form factory** (*) | `DAT_FixtureGenerationCompleted_Result` {outcome, generator_version, fixture_count, seed_id}<br>`DAT_PrivacyCheckFailed_Error` {policy_code} (*) |
| ^ | **Feature 6.3: Dataset adapters and benchmark manifests** (*) | `DAT_AdapterValidated_Result` {dataset_id, revision, outcome, error_code}<br>`DAT_BenchmarkCompleted_Result` {dataset_id, split_id, component_version, outcome} (*) |

## Test Case

| User Flow | Scenario | Test Steps | Expected Result |
|---|---|---|---|
| **EPIC 1: Document Intake** (*) | **Scenario 1.1.1: Accept and normalize a permitted file** (*) | 1. Log in as an authorized verifier.<br>2. Open a fictional claim.<br>3. Upload a permitted readable PDF.<br>4. Start analysis. (*) | The file passes signature and limit checks, receives a checksum and stable page count, and moves to quality analysis. (*) |
| ^ | **Scenario 1.1.2: Reject an invalid file** (*) | 1. Open claim upload.<br>2. Upload a malformed or unsupported fixture.<br>3. Observe the response. (*) | The UI shows the specific rejection reason, starts no analysis job, and allows a replacement upload. (*) |
| ^ | **Scenario 1.2.1: Continue after a readable scan** (*) | 1. Upload the readable quality fixture.<br>2. Run analysis.<br>3. Open analysis progress. (*) | Quality passes and extraction-dependent checks start. (*) |
| ^ | **Scenario 1.2.2: Stop on an unreadable scan** (*) | 1. Upload the blurred or cropped fixture.<br>2. Run analysis.<br>3. Open the quality finding. (*) | The affected page and reason appear, the case becomes `Scan ulang`, and no authenticity conclusion is produced. (*) |
| **EPIC 2: Medical-Form Extraction** (*) | **Scenario 2.1.1: Extract and ground supported fields** (*) | 1. Analyze a supported readable form.<br>2. Open extracted fields.<br>3. Select each critical field. (*) | Each returned value shows confidence, page, region, status, and version; selecting it focuses the source region. (*) |
| ^ | **Scenario 2.1.2: Preserve unknown fields** (*) | 1. Analyze an unsupported-template fixture.<br>2. Inspect required fields and case label. (*) | Unsupported or uncertain fields remain null, claim context is not copied into OCR output, and the case becomes `Perlu dicek` if required analysis is missing. (*) |
| ^ | **Scenario 2.2.1: Count grounded session rows** (*) | 1. Analyze a supported physiotherapy form.<br>2. Open session evidence.<br>3. Compare listed rows with the fixture manifest. (*) | The documented count equals the grounded rows, each row links to its region, and the panel says `Experimental`. (*) |
| ^ | **Scenario 2.2.2: Handle an unsupported session layout** (*) | 1. Analyze a fixture with merged or unsupported rows.<br>2. Open session evidence. (*) | The count is incomplete or unavailable, and the system does not infer rows from billed context. (*) |
| **EPIC 3: Structured Claim Intelligence** (*) | **Scenario 3.1.1: Build a bounded physiotherapy history** (*) | 1. Submit a normalized fictional claim with an approved participant key.<br>2. Call claim analysis.<br>3. Open claim context. (*) | The case shows only events within the configured cohort and window, plus the event count and data revision. (*) |
| ^ | **Scenario 3.1.2: Continue without claim context** (*) | 1. Submit a document case without an available participant key.<br>2. Run analysis. (*) | Structured checks report unavailable, document checks continue, and the case cannot receive `Lolos` if required context is missing. (*) |
| ^ | **Scenario 3.2.1: Explain a frequency or same-day finding** (*) | 1. Analyze an injected high-frequency or same-day history.<br>2. Open the finding. (*) | The UI lists contributing dates, counts, reference context, and rule version with no fraud wording. (*) |
| ^ | **Scenario 3.2.2: Handle insufficient frequency history** (*) | 1. Analyze an incomplete history fixture.<br>2. Inspect frequency results. (*) | The service reports insufficient context and returns no fabricated frequency finding. (*) |
| ^ | **Scenario 3.3.1: Show an inconsistent chronology** (*) | 1. Analyze a fixture with linked referral and service dates in an invalid order.<br>2. Open chronology evidence. (*) | The finding cites the exact linked dates and rule version. (*) |
| ^ | **Scenario 3.3.2: Separate a missing referral link** (*) | 1. Analyze a fixture without a referral link.<br>2. Open chronology evidence. (*) | The state is `link unavailable`, not `inconsistent`, and it does not independently escalate the case. (*) |
| ^ | **Scenario 3.4.1: Report an uncommon supported combination** (*) | 1. Analyze a diagnosis-procedure fixture above the minimum support threshold.<br>2. Open pattern evidence. (*) | The panel shows count, denominator, cohort, revision, and `uncommon in the reference sample`. (*) |
| ^ | **Scenario 3.4.2: Suppress a small reference cell** (*) | 1. Analyze a combination below the minimum cell threshold.<br>2. Inspect the response and logs. (*) | Counts are suppressed, no combination finding appears, and no sensitive value is logged. (*) |
| ^ | **Scenario 3.5.1: Compare a cost with its peer group** (*) | 1. Analyze a claim with an eligible peer group.<br>2. Open cost evidence. (*) | The compared cost, cost type, peer definition, median, IQR, p95, deviation, and revision appear. (*) |
| ^ | **Scenario 3.5.2: Handle a missing cost reference** (*) | 1. Analyze a claim without an eligible cost value or peer group.<br>2. Open cost evidence. (*) | The UI says `reference unavailable` and does not silently use a global distribution. (*) |
| **EPIC 4: Document Integrity** (*) | **Scenario 4.1.1: Retrieve an authorized exact duplicate** (*) | 1. Index a controlled source fixture.<br>2. Submit its authorized duplicate.<br>3. Open duplicate candidates. (*) | The matching source case appears with exact-match evidence and access checks. (*) |
| ^ | **Scenario 4.1.2: Withhold a restricted duplicate source** (*) | 1. Index a matching source outside the test verifier's authorization scope.<br>2. Submit the duplicate.<br>3. Inspect the response. (*) | Restricted source details do not appear in the API, UI, or logs. (*) |
| ^ | **Scenario 4.2.1: Confirm near-duplicate reuse** (*) | 1. Submit a controlled near-duplicate family member.<br>2. Open the top candidate.<br>3. Compare aligned pages.<br>4. Confirm reuse. (*) | The viewer shows matching and differing regions, saves reviewer confirmation, and only then activates the reuse finding. (*) |
| ^ | **Scenario 4.2.2: Handle failed pair alignment** (*) | 1. Compare a non-matching or unalignable pair.<br>2. Observe the comparison. (*) | The result is inconclusive, no confirmed reuse finding is created, and the reviewer can return to candidates. (*) |
| ^ | **Scenario 4.3.1: Review a controlled copy-paste region** (*) | 1. Analyze a controlled copy-paste fixture.<br>2. Open forensic evidence.<br>3. Compare source and destination regions. (*) | Both regions, confidence, version, and the `Experimental` label appear. (*) |
| ^ | **Scenario 4.3.2: Dismiss a repeated-layout false positive** (*) | 1. Analyze a table or stamp negative fixture.<br>2. Dismiss the candidate with a reason.<br>3. Reopen case history. (*) | The dismissal remains auditable and the inactive finding no longer contributes to label calculation. (*) |
| ^ | **Scenario 4.4.1: Localize a controlled numeric edit** (*) | 1. Analyze a controlled edited-number fixture.<br>2. Open the highlighted region. (*) | The suspected region and limitations appear without an invented original value or fraud claim. (*) |
| ^ | **Scenario 4.4.2: Keep a weak edit signal non-decisive** (*) | 1. Analyze a compression-artifact negative fixture.<br>2. Inspect the case label.<br>3. Dismiss the weak signal. (*) | The signal alone does not produce `Prioritas`, and the reviewer can dismiss it. (*) |
| ^ | **Scenario 4.5.1: Validate a signed provenance fixture** (*) | 1. Analyze an official C2PA fixture.<br>2. Open provenance details. (*) | The UI shows signature validity, trust state, available assertions, and component version. (*) |
| ^ | **Scenario 4.5.2: Treat absent provenance as neutral** (*) | 1. Analyze a scan without a C2PA manifest.<br>2. Inspect provenance and label. (*) | The UI shows `No provenance manifest`, uses neutral styling, and does not change the label. (*) |
| **EPIC 5: Review and Decision** (*) | **Scenario 5.1.1: Resolve a label to evidence** (*) | 1. Run all checks on a controlled case.<br>2. Open case detail.<br>3. Open every contributing finding. (*) | The label matches the versioned rule, and every contributing finding resolves to fields, events, or image regions. (*) |
| ^ | **Scenario 5.1.2: Fail safely after a component timeout** (*) | 1. Force a required component timeout.<br>2. Refresh case detail.<br>3. Select retry. (*) | The case becomes `Perlu dicek`, names the incomplete check, never becomes `Lolos`, and allows an authorized retry. (*) |
| ^ | **Scenario 5.2.1: Save a reviewer decision** (*) | 1. Review a completed case.<br>2. Select an action.<br>3. Enter a reason.<br>4. Submit. (*) | The decision and immutable audit entry contain actor, time, prior state, action, reason, and analysis versions. (*) |
| ^ | **Scenario 5.2.2: Require a reason for override** (*) | 1. Choose an action different from the suggestion.<br>2. Leave reason empty.<br>3. Submit. (*) | The form shows a reason-required error, preserves entered data, and stores no decision until corrected. (*) |
| ^ | **Scenario 5.3.1: Generate an authorized report** (*) | 1. Open a decided case as an authorized verifier.<br>2. Request and download the report. (*) | The PDF contains required case, evidence, limitation, decision, and version fields plus the non-fraud disclaimer; the download is audited. (*) |
| ^ | **Scenario 5.3.2: Block an unauthorized or premature report** (*) | 1. Open an undecided case or use a user without report permission.<br>2. Request a report. (*) | Generation is blocked with the applicable reason, and no report file is returned. (*) |
| **EPIC 6: Data and Evaluation Infrastructure** (*) | **Scenario 6.1.1: Produce reconciled aggregate summaries** (*) | 1. Run the aggregate job on the approved fixture extract.<br>2. Open the release report.<br>3. Compare weighted and unweighted sections. (*) | Both sections name their method and revision, suppression is applied, and reconciliation checks pass. (*) |
| ^ | **Scenario 6.1.2: Fail a missing-weight population estimate** (*) | 1. Remove required weight metadata from a test input.<br>2. Run the population-aware job. (*) | The estimate fails explicitly and no unweighted number is published as population-aware. (*) |
| ^ | **Scenario 6.2.1: Regenerate a fictional case family** (*) | 1. Run the fixture factory twice with the same seed and aggregate revision.<br>2. Compare manifests and checksums. (*) | Both runs produce the same fictional outputs, expected findings, and transformations. (*) |
| ^ | **Scenario 6.2.2: Block unsafe generated content** (*) | 1. Inject a forbidden source identifier into a generator test input.<br>2. Run generation.<br>3. Inspect output and logs. (*) | Privacy validation stops publication, reports only the policy code, and exposes no sensitive content. (*) |
| ^ | **Scenario 6.3.1: Validate and evaluate a dataset adapter** (*) | 1. Run an enabled adapter.<br>2. Validate the contract and split manifest.<br>3. Run the benchmark. (*) | Required fields, license, checksum, and split isolation pass, and a versioned report is produced. (*) |
| ^ | **Scenario 6.3.2: Reject a contaminated or changed manifest** (*) | 1. Place derivatives of one base document in different splits or change a frozen checksum.<br>2. Run validation. (*) | Validation fails before evaluation and the report cannot be marked publishable. (*) |

## Executor Validation Summary

- Validate whether the 30 October 2026 release is a judged prototype, internal demo, or pilot candidate; the current scope assumes a prototype. (*)
- Validate metric targets, especially the `<= 2%` confident critical-field error, `>= 95%` duplicate candidate recall, and `>= 70%` edit-region recall. (*)
- Validate that all P1 features fit the nine-day schedule and move P1 features to P2 if implementation evidence is insufficient. (*)
- Validate the label-combination rules and the operational definition of independent strong signals. (*)
- Validate data permissions, dataset licenses, retention, minimum-cell thresholds, and whether reviewer outcomes may be stored. (*)
