# Privacy-safe claim references

This directory contains aggregate outputs produced from local structured claim samples. Raw
and participant-level data must never be placed here.

`rehab-2024/` contains the first outpatient physiotherapy reference:

- `summary.json`: cohort, time, visit-frequency, and cost aggregates;
- `diagnoses.csv`: diagnosis frequencies with cells below 10 suppressed;
- `procedures.csv`: procedure frequencies with cells below 10 suppressed;
- `data-dictionary.json`: source-field purposes without row-level examples;
- `manifest.json`: source and output checksums plus generation parameters.

These files describe historical sample distributions. They are not fraud labels, clinical
guidance, or production claim records.
