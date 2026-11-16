# Privacy-safe claim references

This directory contains aggregate outputs produced from local structured claim samples. Raw
and participant-level data must never be placed here.

`rehab-2024/` contains the first outpatient physiotherapy reference:

- `summary.json`: cohort, time, visit-frequency, and cost aggregates;
- `diagnoses.csv`: diagnosis frequencies with cells below 10 suppressed;
- `procedures.csv`: procedure frequencies with cells below 10 suppressed;
- `data-dictionary.json`: source-field purposes without row-level examples;
- `manifest.json`: source and output checksums plus generation parameters.

`pola-2024/` contains the aggregates behind the pattern score ("Skor pola") that orders the
voice-confirmation call queue. Built by `scripts/prepare_pattern_reference.py` from the same
outpatient physiotherapy cohort, with features defined in `data-uji-konfirmasi/tools/pola.py`:

- `histogram.csv`: participant-month counts and PSTV15 weight sums per binned feature cell
  (`sesi`, `maks_minggu`, `ahad_libur`, `episode`), July to December 2024, cells below 10 suppressed;
- `marginal.json`: weighted national share per bin of each feature (small bins merged into a neighbour);
- `kombinasi.json`: weighted prevalence of each I1 to I4 rule combination; combinations below 10
  rows carry only an upper bound (`prevalensi_maks`);
- `pembanding_tipe.json`: per hospital type and nationally, trigger rate, session mean and
  percentiles, and peer-group trigger-rate percentiles (types below 100 participant-months omitted,
  group percentiles only with at least 20 groups, no minimum or maximum values);
- `manifest.json`: source and output checksums, parameters, cohort counts, suppression statistics.

There is no 2024 holiday list, so `ahad_libur` and I4 count Sundays only. The sample has no
hospital identity; peer groups (district, ownership, kind, type) only approximate one.

```bash
uv run --group data python scripts/prepare_pattern_reference.py \
  --source "../Folder Data Asli/2025 2/Data Sampel Reguler Edisi 2025/data/202403_fkrtl.dta" \
  --output data/reference/pola-2024
uv run --group data python scripts/train_pattern_model.py
```

These files describe historical sample distributions. They are not fraud labels, clinical
guidance, or production claim records.
