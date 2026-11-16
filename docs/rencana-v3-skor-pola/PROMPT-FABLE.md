# Task: pattern score from real BPJS data (Vedika Autentik v3, "Skor pola")

You are working in the `vedika-autentik` repo (the current directory). Build this whole feature in one go, end to end, without stopping to ask questions. Where this spec leaves a detail open, pick the simplest option that satisfies it and list that choice in your final report. Stop early only if something blocks all progress (for example, the raw data folder is missing or dependencies won't install).

This file is the authoritative spec.

## 0. Read first

1. `docs/prd-v3-konfirmasi-suara.md`: requirements, label table, indicators I1–I4.
2. `docs/technical-prd-data-aligned.md` §3–§5: evidence tiers (A real aggregates, B synthetic). Every number you report names its tier.
3. `docs/api-contract-v3.md`: Kontrak A. You will add fields; update its "Perubahan" changelog.
4. `data-uji-konfirmasi/README.md` and `tools/aturan.py` (the single source of the rules), `tools/generate.py`.
5. `ai-service/src/vedika_ai/claim_reference.py`, `ai-service/scripts/prepare_claim_reference.py`, `ai-service/tests/test_claim_reference.py`, `ai-service/data/reference/README.md`: the existing privacy-safe reference builder. Reuse its cohort filter (`_PHYSIOTHERAPY_PATTERN`, `REHABILITATION_CLINIC_LABELS`, `FKL10 == 1`) and its privacy guard style.
6. `backend/app/aturan_v3.py` (how the backend loads `aturan.py` by path), `backend/app/repo_v3.py` (`kunci_tugas`, `hitungan_indikator`), `backend/app/tampilan_v3.py` (`urutan_antrean`, `baris_antre`, `detail`, `ringkasan_rs`), `backend/scripts/seed_v3.py`, `backend/db/schema_v3.sql`, `backend/vercel.json`.
7. `app-v3.js` (queue, evidence card, Ringkasan RS), `data-v3.js` (simulation data), `tests/alur-v3.test.js`.
8. Every code file named below, before you edit it.

## 1. Why, in one paragraph

Today a call is triggered by fixed rules (I1 >8 sessions/month, I2 ≥3 in one week, I3 6-month episode, I4 Sunday/holiday; trigger when ≥2). The rules stay the official trigger. This feature adds a **pattern score** (0–1) learned from the real committee sample (`Folder Data Asli`, 2024 FKRTL) by **knowledge-guided weak supervision**: real patient-months are the "normal" class, rule-guided manipulations of them are the "violation" class (method after CleverCatch, arXiv 2510.13205). The score only **orders the call queue and explains why**; it never creates a call, a label or an RS status. A second output is a **national benchmark per hospital type** shown on Ringkasan RS. Call outcomes (Tidak sesuai vs Sesuai) are exported as real labels for retraining, which is the honest path to supervised learning later.

## 2. Final decisions (do not revisit)

1. **Rules unchanged.** `aturan.py` logic, I1–I4, trigger threshold, labels, RS status and every `expected_*` file stay byte-identical. The queue still contains only rule-triggered patient-months.
2. **Model = logistic regression on one-hot binned features**, trained offline with scikit-learn, exported as JSON (coefficients). Evaluated at runtime in **pure Python** (backend) with no numpy/sklearn, so the Vercel backend bundle does not grow. Explanations are exact per-feature contributions.
3. **Privacy.** Raw data is read only by the offline builder on the laptop. Everything committed is aggregate with every cell ≥ 10 raw rows; no participant, family or visit identifiers; no row-level records; no exact max values. The model is trained from the committed aggregate histogram, not from raw rows, so training is reproducible without the raw folder.
4. **One feature definition.** A new stdlib-only module `data-uji-konfirmasi/tools/pola.py` defines features, bins, scoring and reasons. The builder, the trainer, the backend and the tests all use it (backend loads it by path, like `aturan_v3.aturan()`).
5. **No hospital identity in real data.** Peer groups = (FKL06 district/city, FKL07 ownership, FKL08 kind, FKL09 type). They approximate a hospital and are used only for percentile benchmarks.
6. **Queue order** = `prioritas desc` (Dahulukan), then `skor_pola desc nulls last`, then `id`. Same in the agent claim (`kunci_tugas`) and in the website list (`urutan_antrean`) and in simulation mode.
7. **Wording.** Never "fraud", "curang" or "probabilitas curang" in UI or API. Use "Skor pola" and "Pola tidak biasa". The UI says the score is a priority signal, not a verdict.
8. Keep v2, the station, stubs and simulation working.

## 3. Real-data facts already measured (Tier A, 2024 regular FKRTL, physiotherapy cohort)

Use these to sanity-check your builder output (±1% is fine; differences mean a bug):

- 149,997 physiotherapy visits, 13,172 participants, 41,905 participant-months; weighted (PSTV15) 3,521,010 patient-months nationally.
- Indicator prevalence (weighted, Sunday only for I4): I1 1.88%, I2 3.14%, I3 11.49%, I4 0.45%; triggered (≥2) 1.51% ≈ 4,431 patient-months/month nationally.
- Most common triggered combination: I1+I2 (377 of 703 unweighted).
- Billed == verified on 99.999% of rows; no two physiotherapy visits on the same day for one participant; 20% of visits have no FKTP referral. None of these is a usable feature.
- 951 peer groups, 426 with ≥ 30 patient-months; group trigger rate p50 0%, p90 3.8%, p95 9.0%, p99 23.4%.
- Unweighted trigger rate by type: RS Kelas B 1.7%, RS Kelas C 0.9%, RS Swasta Setara Type B 1.0%, Type C 1.5%; Khusus Bedah 36% (legitimate post-surgery rehab is the likely reason, which is why benchmarks compare within type).

## 4. Specification

### 4.1 Shared module `data-uji-konfirmasi/tools/pola.py` (stdlib only)

- `fitur_bulan(tanggal_bulan_ini: list[date], bulan_aktif: set[str], bulan: str, libur: set[date]) -> dict` returns raw features for one patient (and RS when known) in one month:
  - `sesi`: number of sessions in the month.
  - `maks_minggu`: max sessions in one Monday–Sunday week (same as `aturan.py`).
  - `ahad_libur`: number of sessions on a Sunday or a date in `libur`.
  - `episode`: consecutive months with ≥ 1 session ending at `bulan` (`bulan_aktif` holds "YYYY-MM" strings), capped at 7.
- `BIN`: bins per feature. `sesi`: 1…12 then "13+"; `maks_minggu`: 1…5 then "6+"; `ahad_libur`: 0, 1, "2+"; `episode`: 1…6 then "7+". `bin_fitur(fitur) -> dict` maps raw values to bin labels.
- `skor(model: dict, fitur: dict) -> float`: logistic of intercept + sum of coefficients of the active one-hot bins, rounded to 3 decimals.
- `alasan(model: dict, referensi: dict, fitur: dict, n=2) -> list[dict]`: the top `n` features by positive contribution `coef(bin) − Σ_b p_nasional(b)·coef(b)` (p from the weighted national marginal in `referensi`). Each item: `{"fitur", "nilai", "kontribusi", "persentil_nasional", "teks"}`. `persentil_nasional` = weighted share of national patient-months with a value ≤ this bin. `teks` is Indonesian, e.g. `"11 sesi dalam sebulan; lebih tinggi dari 99% bulan-pasien fisioterapi nasional"`, `"2 sesi di hari Minggu/libur; hanya 0,4% bulan-pasien nasional punya sesi seperti ini"`. Skip features with contribution ≤ 0.
- `kombinasi(i1, i2, i3, i4) -> str`, a stable key like `"I1+I2+I4"` (or `"-"`).
- Unit tests in `data-uji-konfirmasi/tools/uji_pola.py` runnable with `python3` (the folder already uses stdlib-only tools): feature parity with `aturan.hitung_indikator` (`sesi == sesi_ditagih`, `maks_minggu == maks_sesi_seminggu`, `ahad_libur > 0 == I4`, `episode >= 6 == I3`) on all 300 August patient-months; bins; a hand-computed score; reasons ordering.

### 4.2 Offline builder (ai-service, reads raw data)

New `ai-service/src/vedika_ai/pola_reference.py` + CLI `ai-service/scripts/prepare_pattern_reference.py`, run with `uv run --group data`. Add `scikit-learn` to the `data` dependency group only.

```bash
cd ai-service
uv run --group data python scripts/prepare_pattern_reference.py \
  --source "../Folder Data Asli/2025 2/Data Sampel Reguler Edisi 2025/data/202403_fkrtl.dta" \
  --output data/reference/pola-2024
```

- Cohort: same filter as `claim_reference.py` (outpatient, FIS/IRM, physiotherapy pattern). Read in chunks; keep only the needed columns: `PSTV01, PSTV15, FKL03, FKL06, FKL07, FKL08, FKL09, FKL10, FKL11, FKL18A, FKL30`.
- Per participant-month, compute features with `pola.fitur_bulan` (pass `libur=set()`: there is no 2024 holiday list, so `ahad_libur` is Sunday only for real data; record this in the manifest).
- Use patient-months 2024-07 … 2024-12 for the histogram, so `episode` up to "7+" is observable; use all months for prevalence and benchmarks.
- Outputs in `ai-service/data/reference/pola-2024/`:
  - `histogram.csv`: columns `sesi, maks_minggu, ahad_libur, episode, n, bobot` (bins, raw count, PSTV15 weight sum). Suppress cells with `n < 10`; write the suppressed row and weight share to the manifest.
  - `marginal.json`: weighted national share per bin of each feature (from all rows before suppression; every bin with n ≥ 10, else merged into the neighbouring bin and noted).
  - `kombinasi.json`: weighted prevalence of each indicator combination among patient-months (I1–I4 computed like `aturan.py`, I4 Sunday only). Combinations with `n < 10` are written as `{"prevalensi_maks": <share of 10 rows>}` instead of an exact value.
  - `pembanding_tipe.json`: per FKL09 type label and for `"Nasional"`: `bulan_pasien` (n), `persen_terpicu` (weighted), `sesi_rata` (weighted), `sesi_p90`, `sesi_p95`, and over peer groups of that type with ≥ 30 patient-months: `kelompok` (count) and `terpicu_p50/p90/p95` only if there are ≥ 20 groups. Omit any type with < 100 patient-months. Never export a max or min.
  - `manifest.json`: source path basename, source checksum, output checksums, parameters, generation date, suppression stats, the privacy flags used by `rehab-2024`.
- Privacy guard and tests modelled on `tests/test_claim_reference.py`: committed files contain no column named like an identifier, every count ≥ 10, manifest checksums match. Builder unit tests use a tiny in-memory frame, not the raw file.
- Update `ai-service/data/reference/README.md` with a `pola-2024/` section.

### 4.3 Trainer (weak supervision)

`ai-service/scripts/train_pattern_model.py` (`uv run --group data`), reads only committed files, deterministic (`random_state=2026`), writes `data-uji-konfirmasi/referensi-pola/`:

- **Normal class**: 50,000 samples drawn from `histogram.csv` with probability ∝ `bobot`.
- **Violation class**: 50,000 samples, each a normal sample changed by 1–2 manipulations chosen at random, mirroring the injection in `tools/generate.py` and the rules:
  - V1 tambah sesi: `sesi += randint(2, 6)`; `maks_minggu = max(maks_minggu, ceil(new_sesi / 4) + randint(0, 1))`.
  - V2 sesi hari libur: `ahad_libur += randint(1, 2)`; `sesi += 1`.
  - V3 pemadatan: `maks_minggu = max(maks_minggu, randint(3, 5))`, then `sesi = max(sesi, maks_minggu)`.
  - V4 perpanjangan episode, only combined with another manipulation: `episode = min(7, episode + randint(3, 6))`.
  - Apply bins after manipulation; values above the top bin go to the top bin.
- Model: `LogisticRegression(C=1.0, max_iter=1000)` on one-hot bins (all bins of `pola.BIN`, unseen bins get coefficient 0).
- `ambang_tinggi`: the weighted 98.5th percentile of the score over the national histogram (so "Pola tidak biasa" fires on ≈ 1.5% of national patient-months, the same rate as the rules).
- Output `data-uji-konfirmasi/referensi-pola/`:
  - `model-pola-v1.json`: `{versi: "pola-v1", fitur, bin, intersep, koefisien: {fitur: {bin: coef}}, ambang_tinggi, dilatih_dari: "ai-service/data/reference/pola-2024", tanggal}`.
  - `referensi.json`: the subset of `marginal.json`, `kombinasi.json`, `pembanding_tipe.json` the backend needs, plus `peta_tipe` (below).
  - `skor_demo.json`: score, `tinggi` flag and reasons for every August 2026 patient-month in `klaim_sesi.csv` (used to fill `data-v3.js` and by tests).
  - `EVALUASI.md` (generated, Indonesian), reported **per tier, never combined**:
    - Tier B (synthetic, method sanity only): holdout AUC of normal vs violation.
    - Tier A: share of national patient-months above `ambang_tinggi`; score mean per rule combination.
    - Tier B (demo data vs `kunci_kebenaran_2026-08.csv`, where inflated = `sesi_ditagih − sesi_sebenarnya > 2`): AUC of the score; precision and recall of the rule trigger; precision@30 of the score; the number of inflated patient-months the rules miss that score above `ambang_tinggi`. `kunci_kebenaran` is read **only** here (offline evaluation), never by the backend or seed.
    - Coefficient table, and the limitation text: the score means "resembles known manipulation patterns relative to the national 2024 pattern", not a fraud probability; the normal class may contain undetected manipulation; I4 in real data is Sunday only.
- **Feature-fit check** before training: compare each feature's marginal for the honest demo hospitals (RS02–RS05, August, from `klaim_sesi.csv`) with the national marginal. If a feature's top-bin share differs by more than 3× in a way that would flag honest demo patients, drop that feature from the model, keep going, and record it in `EVALUASI.md` and your report. Do not edit `generate.py` or the demo data.
- `peta_tipe` maps demo RS types to FKL09 labels: `"Pemerintah kelas B" → "RS Kelas B"`, `"Pemerintah kelas C" → "RS Kelas C"`, `"Swasta setara kelas B" → "RS Swasta Setara Type B"`, `"Swasta setara kelas C" → "RS Swasta Setara Type C"`; unknown → `"Nasional"`.

### 4.4 Backend

- `backend/app/pola_v3.py`: loads `tools/pola.py` by path (like `aturan_v3.aturan()`), and loads `model-pola-v1.json` and `referensi.json` from `DATA_UJI / "referensi-pola"` with `lru_cache`. `backend/vercel.json` already copies `data-uji-konfirmasi` (minus `kunci_kebenaran_*`); confirm `referensi-pola/` is included.
- Schema (`schema_v3.sql`, idempotent `alter table … add column if not exists`, like `prioritas`): `indikator_bulanan.skor_pola real`, `indikator_bulanan.alasan_pola jsonb not null default '[]'`, `indikator_bulanan.pola_tinggi boolean not null default false`. Update `tests/test_schema_v3.py`.
- `seed_v3.py`: compute features with `pola.fitur_bulan` for every `indikator_bulanan` row (all 300, not only triggered), then the score, reasons and `pola_tinggi`. Store `versi_pola` in `pengaturan` (key/value) so the UI can show it. `reset_panggilan` keeps the scores.
- Queue order (decision 6): `repo_v3.kunci_tugas` joins `indikator_bulanan` on `(id_peserta, id_rs, bulan_layanan = bulan)`; `tampilan_v3.urutan_antrean` sorts antre rows by `(0 if prioritas else 1, -(skor or -1), id)`.
- Kontrak A additions (update `docs/api-contract-v3.md` and its changelog):
  - `GET /antrean` rows: `skor_pola` (number or null), `pola_tinggi` (bool).
  - `GET /panggilan/{id}`: `pola: {skor, tinggi, ambang, alasan: [..2], kombinasi: {kunci, teks}, versi}`. `kombinasi.teks` example: `"Kombinasi I1+I2+I4 terjadi pada 0,02% bulan-pasien fisioterapi nasional 2024."`; for suppressed combinations: `"… kurang dari 0,03% …"`.
  - `GET /ringkasan-rs` per RS: `pembanding: {tipe, persen_terpicu_nasional, sesi_rata_nasional, terpicu_p95_kelompok, posisi}` where `posisi` is one of `"di_atas_p95"`, `"di_atas_p90"`, `"wajar"`, `"tidak_ada_pembanding"`; and `pola_tinggi_tidak_terpicu` (count of this RS's patient-months with `pola_tinggi` and not triggered, shown as information only). Top-level `kinerja_pola`: over completed calls labelled Sesuai or Tidak sesuai, `{n, skor_rata_tidak_sesuai, skor_rata_sesuai, tinggi_dan_tidak_sesuai, tinggi}`.
- Tests (backend pytest, local Postgres per `backend/README.md`): schema; seed stores scores for all 300 rows and equals `skor_demo.json`; claim order (Dahulukan first, then score, then id); API fields; ringkasan values; labels and RS status unchanged against `expected_ringkasan_rs.json`. Update existing tests that assumed pure id order.

### 4.5 Website (`app-v3.js`, `api-v3.js`, `app-v3.css`, `data-v3.js`)

- **Queue row:** a compact chip `Pola 0,93` with a thin bar; the chip gets the "tinggi" style when `pola_tinggi`. Tooltip/aria: "Skor pola: prioritas panggilan, bukan putusan."
- **Evidence card:** a section "Mengapa diprioritaskan" with the two reasons and the combination sentence, then one muted line: "Skor pola dihitung dari pola nasional data sampel BPJS 2024 (agregat). Bukan putusan; label tetap dari jawaban pasien."
- **Ringkasan RS:** per RS one line under the counts, e.g. "Terpicu 18,0% · RS sejenis nasional 1,5% · 95% kelompok RS sejenis ≤ 9,0%" with a badge "Di atas 95% RS sejenis" for `di_atas_p95`. If `pola_tinggi_tidak_terpicu > 0`: "N bulan-pasien berpola tidak biasa di bawah ambang aturan (tidak ditelepon)". A small card at the top: "Skor pola vs hasil panggilan" from `kinerja_pola`.
- **Simulation mode:** add `skor_pola`, `pola_tinggi`, `pola` to the hand-written rows in `data-v3.js`, copying values from `skor_demo.json`, and use the same queue order. Add a console self-check next to the existing label self-check.
- `tests/alur-v3.test.js`: chip renders, queue order follows the score after Dahulukan, card shows two reasons for S1, Ringkasan RS shows the benchmark line, no horizontal scroll at 390 px.
- Indonesian number format (comma decimals) everywhere.

### 4.6 Feedback loop (labels from calls)

- `backend/scripts/ekspor_label_pola.py`: writes `label-panggilan.json` (gitignored path under `backend/uploads/` or a path given by `--output`) with, per completed call labelled Sesuai or Tidak sesuai: the binned features and `label` (1 = Tidak sesuai). No names, numbers or IDs.
- `train_pattern_model.py --label-panggilan <file>`: adds those rows as supervised samples with weight 5, writes `model-pola-v2.json` beside v1 (v1 stays the default; the backend reads the version named in `pengaturan.versi_pola`, default `pola-v1`), and appends a "dengan label panggilan" section to `EVALUASI.md`. With the demo, the labels are synthetic; say so in the report.

### 4.7 Docs (Indonesian)

- `docs/rencana-v3-skor-pola/SKOR-POLA.md`: what the score is and isn't, the data and privacy path (raw → aggregate → model → runtime), how to rebuild and retrain, how to read the queue chip, card and benchmark, the tiers, and the limitations.
- `data-uji-konfirmasi/README.md`: add `tools/pola.py` and `referensi-pola/` to the file table and to "Mana yang nyata, mana yang sintetis".
- `docs/prd-v3-konfirmasi-suara.md`: a short section under the indicators: "Skor pola (prioritas, bukan pemicu)".

## 5. Acceptance

Commands that must pass:

```bash
python3 data-uji-konfirmasi/tools/uji.py indikator
python3 data-uji-konfirmasi/tools/uji_pola.py
cd ai-service && uv run pytest -q && uv run ruff check . && cd ..
cd ai-service && uv run --group data python scripts/prepare_pattern_reference.py --source "../Folder Data Asli/2025 2/Data Sampel Reguler Edisi 2025/data/202403_fkrtl.dta" --output data/reference/pola-2024 && cd ..
cd ai-service && uv run --group data python scripts/train_pattern_model.py && cd ..
cd backend && .venv/bin/pytest && cd ..   # see backend/README.md; use local Postgres if Supabase is unreachable
node tests/alur-v3.test.js
TARGET_URL=http://localhost:8899/v2.html node tests/alur.test.js
```

Behaviour checks:

1. `git diff --stat` shows no change to `data-uji-konfirmasi/expected_*`, `kunci_kebenaran_*`, `klaim_sesi.csv`, `peserta.csv`, `tools/aturan.py`, `tools/generate.py`.
2. Builder numbers match §3 within ±1%.
3. National alert rate above `ambang_tinggi` is between 1.0% and 2.0%.
4. Demo: AUC of the score against `kunci_kebenaran` (inflated vs not) ≥ the AUC of `jumlah_indikator`; report both. If it is lower, keep the feature but say so plainly in `EVALUASI.md` and the final report. Do not tune toward `kunci_kebenaran`.
5. S1 has two reasons mentioning sessions and Sunday/holiday. If S1 is not first in the August queue by score, report which call is first and update the demo walkthrough text in `docs/` accordingly; do not hand-tune.
6. Ringkasan RS shows RS Melati Sehat as `di_atas_p95` against "RS Swasta Setara Type C"; honest hospitals are `wajar` or `di_atas_p90` at most. Report the actual positions either way.
7. Every committed file under `ai-service/data/reference/pola-2024/` and `data-uji-konfirmasi/referensi-pola/` passes the privacy guard (no identifiers, counts ≥ 10, no max/min values).
8. The agent claim order in a live run (station in `palsu` mode, `ai-service/scripts/agent_e2e.mjs` or `stub_agen.py`) follows Dahulukan, then score.

## 6. Hard constraints

- Never commit anything from `Folder Data Asli/` or any row-level derivative. The exploration script outside the repo is not part of this task.
- The backend never reads `Folder Data Asli/` or `kunci_kebenaran_*`.
- No numpy, pandas or scikit-learn in `backend/requirements.txt`.
- The score never changes `dipicu`, a label, a suggestion (`saran`) or RS status.
- No "fraud"/"curang" wording in UI, API or WA text.
- Python: uv, functional style, loguru for any new logging, f-strings. JS: no new framework; follow `app-v3.js` patterns.

## 7. Working rules

- Branch `v3-skor-pola` from `main`. Commit per phase with `<type>(<scope>): <what changed>` (Indonesian, like the history), e.g. `feat(pola): referensi agregat pola 2024 dari data sampel`.
- No co-author trailer and no Claude/AI attribution in commits or PRs.
- Never push, force-push or skip hooks. Don't commit `.env`, tokens, uploads or `label-panggilan.json`.

Phases (commit after each, keep tests green):

| Phase | Content |
|---|---|
| P0 | `tools/pola.py` + `uji_pola.py` |
| P1 | builder + `pola-2024/` outputs + privacy tests |
| P2 | trainer + `referensi-pola/` + `EVALUASI.md` |
| P3 | backend schema, seed, order, API, contract doc, tests |
| P4 | website + simulation + `alur-v3` tests |
| P5 | feedback export + retrain option |
| P6 | docs |

## 8. Final report

Reply with:

1. What was built, per phase, with commit hashes.
2. Every number from `EVALUASI.md`, labelled by tier.
3. Features dropped by the feature-fit check, if any, and why.
4. Queue order for August (top 10 ids with score) and the S1 position.
5. Ringkasan RS benchmark position per RS.
6. Choices you made where this spec was open.
7. Anything that failed or was skipped, with the command output.
