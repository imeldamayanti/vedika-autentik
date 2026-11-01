# Technical PRD — Vedika Autentik: Data-Aligned Feature Strategy

**Product:** Vedika Autentik  
**Analysis engine:** PRAMANA  
**Version:** 1.0  
**Date:** 21 October 2026  
**Status:** Proposed implementation scope  
**Category:** Efficiency and risk management for healthcare facilities

## 1. Purpose

Vedika Autentik is a verifier-assistance feature for outpatient physiotherapy claims. It combines:

1. structured claim-history analysis to identify cases that deserve earlier review; and
2. document analysis to show quality problems, inconsistencies, reuse, or suspicious regions.

The product produces review evidence, not a fraud verdict. The backend determines review priority
from explicit rules, and the verifier retains the final decision.

This PRD defines which existing capabilities remain defensible, which capabilities must be removed
from the product scope, and which capabilities may be added using relevant external datasets until
approved BPJS-domain data becomes available.

## 2. Success criteria

The prototype succeeds when it can:

- run an end-to-end upload, analysis, evidence, decision, and reporting workflow;
- demonstrate each technical capability on the closest available task-specific dataset;
- distinguish technical feasibility from BPJS-domain validation;
- replace development datasets through adapters without changing product APIs or reviewer flows;
- fail safely: an unreadable or failed analysis never becomes `Lolos`;
- show a human-readable reason and source for every finding.

The prototype does not need to demonstrate production accuracy on BPJS documents. That validation
requires approved BPJS-domain documents and governed reviewer outcomes.

## 3. Data evidence model

Every result and metric must name one of these evidence tiers:

| Tier | Data | Permitted claim |
|---|---|---|
| A | `Folder Data Asli` | Structured BPJS sample patterns and schema feasibility |
| B | Synthetic Vedika fixtures | Workflow, contract, regression, and controlled manipulation behavior |
| C | External document benchmarks | Technical capability on the benchmark's task and domain |
| D | Future consented Indonesian forms | Domain-oriented calibration for handwriting, capture, and manipulation |
| E | Future approved BPJS pilot data | BPJS-domain performance and operational validation |

Results from different tiers must be reported separately. They must not be combined into one
"AI accuracy" value.

## 4. Available data

### 4.1 `Folder Data Asli`

The local folder contains approximately 6.4 GB of structured administrative samples:

- 115 Stata files, including 63 membership/claim tables and 52 ICD reference tables;
- 40 Excel metadata/code workbooks;
- 43 Stata preparation and analysis scripts;
- membership, FKTP, FKRTL, non-capitated, and secondary-diagnosis tables;
- contextual cohorts for diabetes, TB, maternal/child health, mental health, and COVID;
- uneven historical coverage from approximately 2015 through 2024.

The 2024 regular FKRTL table contains 1,699,219 rows. The current privacy-safe physiotherapy
reference contains 149,997 rows, 13,172 participants, and 41,905 participant-months.

Useful fields include pseudonymous participant and visit identifiers, service dates, partial
referral linkage, diagnosis, procedure, INA-CBG information, billed and verified costs,
geography, facility characteristics, and sample weight `PSTV15`.

The data does not contain document images, SEP values, explicit billed session counts, stable
hospital identities, fraud labels, reviewer decisions, signatures, or document manipulation
annotations.

### 4.2 Existing synthetic document data

The repository contains 17 fictional physiotherapy documents covering genuine-looking files,
reuse, copy-paste, edited values, digitally created files, and bad scans. These fixtures provide
known fields, expected findings, comparison families, and evidence regions.

They are appropriate for software regression and demonstrations, but not for production accuracy
claims.

## 5. Feature decisions

### 5.1 Retain: existing features supported by `Folder Data Asli`

| Feature | Data used | Required output | Decision |
|---|---|---|---|
| Physiotherapy cohort construction | Clinic, diagnosis, procedure, service level | Reproducible cohort manifest | Retain |
| Visit-frequency analysis | Participant ID and service date | Daily, weekly, and monthly counts | Retain and expand |
| Same-day or closely spaced claims | Participant ID and service date | Explainable chronology finding | Retain and expand |
| Referral chronology | `FKP02`, FKTP and FKRTL dates | Missing or inconsistent sequence evidence | Add where linkage exists |
| Diagnosis–procedure frequency | ICD and procedure fields | Commonness and supporting counts | Add |
| Cost reference | Billed/verified costs and peer fields | Median, IQR, p95, and robust deviation | Retain and expand |
| Population-aware summaries | `PSTV15` and survey strata | Weighted and unweighted statistics | Add |
| Fictional claim generation | Privacy-safe aggregate distributions | Synthetic claim and history fixtures | Add |

These features may produce review signals such as `anomali_frekuensi`, `anomali_duplikat`,
`ketidakkonsistenan_kronologi`, `kombinasi_jarang`, and `anomali_biaya`. They must not produce a
fraud verdict.

### 5.2 Retain as experimental: existing document features

These capabilities remain relevant to the product objective but are not supported by `Folder Data
Asli`. They may remain when evaluated with synthetic and external document datasets.

| Feature | Current status | Required evidence before BPJS pilot |
|---|---|---|
| File validation and canonical rendering | Implemented baseline | External malformed-file and multi-page tests |
| Scan-quality gate | Implemented baseline | SmartDoc benchmark, then Indonesian volunteer captures |
| Template-guided extraction | Implemented baseline | CORD/FUNSD benchmark, then hospital-template samples |
| Session-row counting | Implemented on synthetic templates | Volunteer forms with handwritten sessions |
| Masked document fingerprint | Implemented baseline | Cross-template and archive-scale retrieval benchmark |
| Pairwise reuse confirmation | Implemented baseline | Controlled duplicate families and genuine near-neighbors |
| Within-document copy-paste | Implemented baseline | Document tampering benchmark and volunteer negatives |
| Edited text/number localization | Partial | DocTamper benchmark and BPJS-like controlled edits |
| Metadata/provenance checks | Supporting evidence only | Official C2PA positive and negative fixtures |
| AI-assisted alteration signal | Research-only | AIForge-Doc stress test; must remain non-decisive |

### 5.3 Add: capabilities enabled by recommended external datasets

| Capability | Recommended dataset | Technical use | Dataset limitation |
|---|---|---|---|
| Indonesian OCR and numeric extraction | CORD v2 | OCR, boxes, key fields, structured parsing | Receipts rather than medical forms |
| Noisy form understanding | FUNSD | Field grouping, key-value links, spatial grounding | English and small |
| Mobile capture normalization | SmartDoc | Blur, perspective, lighting, crop, occlusion | Generic documents |
| Handwritten digit bootstrap | NIST SD19 | Dates, totals, and digit recognition pretraining | US handprint domain |
| Traditional edit localization | DocTamper | Copy-move, splicing, generated text, pixel masks | Non-commercial research use |
| AI-inpainted field stress test | AIForge-Doc | Numeric-field replacement and pixel masks | Non-commercial; not BPJS-specific |
| Signed provenance validation | C2PA public test files | Valid, invalid, and untrusted manifest handling | Absence of C2PA proves nothing |

External datasets are development and evaluation dependencies, not runtime claim databases.
Dataset licenses and model-weight usage rights must be recorded before download, training, or
redistribution. Non-commercial datasets may be used only for approved research evaluation; models
trained on them must not be deployed commercially without legal approval.

### 5.4 Remove from the product scope

The following features or claims must be removed, not merely relabeled as future work:

- automatic fraud determination or automatic claim rejection;
- a model-generated "probability of fraud" without governed fraud/reviewer labels;
- a generic AI-image detector presented as proof that a document is fraudulent;
- signature-owner identification or biometric signature verification;
- medical-necessity, diagnosis-correctness, or treatment-appropriateness decisions;
- hospital/provider risk ranking when no stable provider identifier is available;
- automatic participant outreach or a claim that PANDAWA integration already exists;
- claims of live JKN Drive, Vedika, V-Claim, or E-Klaim integration;
- claims of BPJS accuracy, financial savings, or prevented leakage before a governed pilot;
- treating a rare pattern, high frequency, missing metadata, or bad scan as fraud.

The PANDAWA screen may remain only as a clearly marked workflow simulation outside the production
MVP scope.

## 6. Product behavior

### 6.1 End-to-end flow

```text
upload document + optional structured claim/history
  -> validate and normalize document
  -> quality gate
      -> unreadable: Scan ulang; stop authenticity checks
      -> readable: continue
  -> extract fields and session evidence
  -> analyze reuse, copy-paste, edits, and provenance
  -> analyze structured claim history when available
  -> return independent findings with evidence and component versions
  -> backend applies deterministic priority rules
  -> verifier reviews, records a decision, and optionally creates a report
```

### 6.2 Label policy

- `Lolos`: no finding, required checks completed, and available claim context is consistent.
- `Scan ulang`: document quality prevents reliable analysis.
- `Perlu dicek`: one uncertain or moderate signal, unsupported template, or analysis failure.
- `Prioritas`: multiple independent strong signals under backend rules.

An AI-generation/provenance signal cannot independently produce `Prioritas`. A structured anomaly
cannot independently establish document manipulation or fraud.

## 7. Technical architecture

```text
Frontend
  reviewer queue, evidence viewer, decisions, reports
      |
Backend
  upload, storage, jobs, claim context, candidate search, labels, audit trail
      |
PRAMANA AI service
  document normalization, extraction, comparison, forensics, claim analysis
      |
Offline data and evaluation
  BPJS aggregate builder + dataset adapters + frozen benchmark manifests
```

Ownership remains separated:

- the backend owns authentication, raw files, claim history, retries, labels, and decisions;
- PRAMANA remains stateless and returns evidence rather than final labels;
- raw `Folder Data Asli` and external training/evaluation data are not runtime dependencies;
- only privacy-reviewed aggregates, schemas, checksums, and synthetic fixtures may be committed.

## 8. Dataset adapter contract

Each evaluation dataset must be converted to a common internal record:

```text
DocumentSample
  sample_id
  source_dataset
  license_id
  evidence_tier
  base_document_id
  image_or_pages
  fields[]                 # value, type, page, bounding box
  quality_labels[]         # blur, crop, perspective, lighting, occlusion
  manipulation             # type, source sample, mask/boxes
  duplicate_family_id
  provenance_expectation
  split                    # development or frozen test
```

All derivatives of one base document must remain in the same split. Dataset-specific parsing must
stay inside adapters so a future BPJS adapter can replace development datasets without changing
the evaluation runner or service API.

## 9. API evolution

Retain:

- `GET /v1/kesehatan`
- `POST /v1/analisis`
- `POST /v1/bandingkan`

Add:

- `POST /v1/analisis-klaim`

`/v1/analisis-klaim` accepts a normalized current claim and a bounded event history supplied by
the backend. It returns findings only, including the contributing fields, reference cohort,
threshold/model version, and score where applicable.

New finding types:

- `anomali_frekuensi`
- `anomali_duplikat`
- `ketidakkonsistenan_kronologi`
- `kombinasi_jarang`
- `anomali_biaya`
- `forensik_visual`
- `ketidakkonsistenan_dokumen`

Every finding must contain an evidence ID, component version, concise Indonesian explanation, and
supporting fields or image regions. Missing or low-confidence values remain null; the service must
not copy values from claim context into OCR output.

## 10. Evaluation and release gates

| Component | Development metric | Prototype gate |
|---|---|---:|
| Scan quality | Class recall and false escalation | Bad genuine scans becoming `Prioritas` = 0 |
| Extraction | Exact match, coverage, accuracy when returned | Incorrect confident critical fields <= 2% |
| Grounding | Correct page and region IoU | Reported separately per dataset |
| Duplicate retrieval | Candidate recall and confirmed-pair precision | >= 95% on controlled families |
| Traditional edit localization | Region precision and recall | Recall >= 70%, precision reported |
| AI-assisted edit test | Per-generator detection/localization | Research result only; no release gate |
| Claim anomaly | Detection by injected anomaly and false positives | Rules baseline must be reported |
| Reviewer explanation | Evidence-link resolution | Unsupported statements = 0 |

Thresholds are tuned only on development splits. Frozen test splits are evaluated once per version.
A learned model remains disabled unless it outperforms the deterministic baseline on the relevant
dataset without increasing genuine-document escalation beyond the gate.

Passing an external benchmark permits only a capability-specific claim, such as "evaluated on
mobile document capture." It does not permit a BPJS production-performance claim.

## 11. Privacy, security, and governance

- Never commit raw BPJS rows, participant-level derivatives, external dataset copies, or volunteer
  captures.
- Do not log names, identifiers, OCR text, filenames, images, claim payloads, or document bytes.
- Use pseudonymous identifiers only for bounded offline linkage; never export the mapping.
- Publish aggregate categories only after minimum-cell suppression and privacy review.
- Encrypt documents in transit and at rest; define retention and deletion before pilot use.
- Record dataset revision, license, source checksum, split manifest, component version, thresholds,
  and evaluation machine for every result.
- Reviewer decisions used for later calibration require governance approval and subgroup audits.

## 12. Delivery sequence

1. **Data truth:** reconcile documentation, add weighted BPJS aggregates, and freeze manifests.
2. **Claim intelligence:** implement deterministic frequency, chronology, combination, and cost
   findings through `/v1/analisis-klaim`.
3. **Open benchmark adapters:** add CORD, FUNSD, SmartDoc, NIST SD19, and C2PA adapters.
4. **Forensics benchmark:** evaluate deterministic methods on controlled edits; use DocTamper and
   AIForge-Doc only after license approval.
5. **Synthetic paired factory:** generate fictional BPJS-like claims, forms, duplicate families,
   capture degradation, and exact manipulation masks.
6. **Domain validation:** collect consented Indonesian volunteer forms, freeze a blind split, and
   recalibrate without exposing raw documents.
7. **BPJS pilot:** replace adapters and reference data with approved integrations, then measure
   operational outcomes separately from model metrics.

## 13. Prototype acceptance criteria

The scope is accepted when:

- every active feature is assigned a data source, evidence tier, metric, and owner;
- every external dataset has a recorded license and checksum;
- external, synthetic, and BPJS-sample results are reported separately;
- the public demo contains only fictional identities and claim histories;
- `Folder Data Asli` is processed offline and no row-level record is committed or served;
- unsupported features listed in section 5.4 cannot affect labels;
- failures and unsupported templates become `Perlu dicek`, never `Lolos`;
- the reviewer can trace every label to explicit findings and evidence;
- the dataset adapters can be replaced without changing the public `/v1` response contract.

## 14. Approved terminology

Use:

- "review priority" or "sinyal telaah";
- "document integrity evidence";
- "evaluated on synthetic/external benchmark data";
- "BPJS-domain validation pending";
- "indication of digital alteration";
- "uncommon in the reference sample."

Do not use:

- "fraud detected";
- "AI proves the document is fake";
- "validated on BPJS documents";
- "provider committed fraud";
- "guaranteed savings";
- "production-ready" before the BPJS pilot gates pass.

## 15. External dataset references

- CORD: <https://github.com/clovaai/cord>
- FUNSD: <https://arxiv.org/abs/1905.13538>
- SmartDoc: <https://sites.google.com/site/icdar15smartdoc/challenge-1/dataset>
- NIST Special Database 19: <https://www.nist.gov/srd/nist-special-database-19>
- DocTamper: <https://github.com/qcf-568/DocTamper>
- AIForge-Doc: <https://arxiv.org/abs/2602.20569>
- C2PA public test files: <https://github.com/c2pa-org/public-testfiles>

