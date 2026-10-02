# AI Validation Protocol — Vedika Autentik

This protocol is the remaining real-data validation step for PRAMANA. It does not
use real JKN participants or claims.

## Dataset

- Recruit 20–30 consenting adult volunteers.
- Use fictitious identities, card numbers, SEP values, facilities, and diagnoses.
- Have each volunteer complete at least two printed physiotherapy forms by hand.
- Capture each original with a scanner and at least one phone under ordinary lighting.
- Create controlled variants: reuse with changed identity/month, copied signature or row,
  edited total/date, design-app recreation, blur, darkness, crop, and perspective.
- Keep the untouched source and an edit log with exact changed regions.

Never commit volunteer names, signatures, or raw captures to the public repository. Store
them in access-controlled project storage with a retention date and participant code only.

## Split and calibration

1. Split by volunteer, never by image: 70% development and 30% blind test.
2. Tune templates and thresholds only on the development split.
3. Freeze engine, template, fingerprint, and threshold versions.
4. Run the blind split once. Report misses and false positives without retuning it.
5. If the engine changes, create a new blind split or record that the old split is no longer blind.

## Required labels

For every file record scan quality, filled rows, session dates, written total, and controlled
manipulation regions. For duplicate families, record the source file and which regions were
reused. Two reviewers resolve ambiguous labels before evaluation.

## Metrics and release gates

| Metric | MVP gate |
|---|---:|
| Session count exact | ≥ 95% |
| Duplicate-family recall | ≥ 95% |
| Pasted signature/stamp recall | ≥ 90% |
| Edited-region recall | ≥ 70%, reported with precision |
| Genuine files incorrectly escalated to Prioritas | ≤ 5% end to end |
| Bad genuine scans escalated to Prioritas | 0 |
| Warm one-page CPU latency | p95 < 10 s |

Also report OCR coverage and accuracy-when-returned separately. A nullable result is not an
OCR error; an incorrect confident value is.

## Execution record

Record dataset revision, consent batch, split manifest, engine/model/template versions,
machine CPU and memory, Docker image digest, per-file output, aggregate metrics, and failures.
Do not publish raw documents or extracted personal text.

The repository command for the synthetic preflight is:

```bash
cd ai-service
uv run python scripts/evaluate.py --check --output evaluation.json
```

Passing the synthetic preflight is necessary but is not evidence that the real-data gates pass.
