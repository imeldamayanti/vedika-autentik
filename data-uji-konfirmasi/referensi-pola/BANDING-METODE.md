# Perbandingan model anomali

Dibuat oleh `ai-service/scripts/compare_anomaly_models.py` pada 2026-11-17. Jangan disunting manual.

Tiga cara menandai tagihan bulanan pada data yang sama: 40.650 bulan-pasien fisioterapi
(Juli–Desember 2023, 2024, data sampel reguler BPJS), enam fitur yang sama, sekitar 1,5% bobot ditandai.

- **anomali-v1 (Isolation Forest)**: tabel skor Isolation Forest yang dibekukan (`model-anomali-v1.json`).
- **Kelangkaan nasional**: peluang pola secara nasional, tanpa kelompok.
- **anomali-v2 (umur)**: peluang pola di kelompok umur pasien, dihaluskan ke nasional (model yang dipakai).

## Hasil di data nyata

| Metode | Ditandai | Hanya model | Aturan ATAU model | Antartahun: 2024 oleh model 2023 / 2024 |
|---|---|---|---|---|
| anomali-v1 (Isolation Forest) | 1,53% | 0,68% | 2,72% | – |
| Kelangkaan nasional | 1,53% | 1,05% | 3,09% | 1,34% / 1,51%, Jaccard 0,692 |
| anomali-v2 (umur) | 1,53% | 1,05% | 3,1% | 1,34% / 1,51%, Jaccard 0,669 |

anomali-v1 tidak bisa dilatih ulang di sini, jadi tidak punya baris antartahun.

## Seberapa sering metode sepakat (Jaccard himpunan yang ditandai)

|  | anomali-v1 (Isolation Forest) | Kelangkaan nasional | anomali-v2 (umur) |
|---|---|---|---|
| anomali-v1 (Isolation Forest) | 1 | 0,378 | 0,413 |
| Kelangkaan nasional | 0,378 | 1 | 0,793 |
| anomali-v2 (umur) | 0,413 | 0,793 | 1 |

## Uji sisipan (sintetis)

2.000 bulan-pasien biasa 2024 (tidak terpicu aturan, tidak ditandai metode mana pun) diubah dengan
satu manipulasi, lalu dinilai. Persen = bagian yang tertangkap. Manipulasinya kami rancang sendiri, jadi ini
menunjukkan apa yang bisa dilihat tiap metode, bukan kinerja di lapangan. "Sebagian tanpa rujukan" adalah nilai
tengah sebuah fitur; "rujukan janggal" meniru temuan utama anomali-v1.

| Manipulasi | Aturan | anomali-v1 (Isolation Forest) | Kelangkaan nasional | anomali-v2 (umur) |
|---|---|---|---|---|
| pemadatan seminggu | 27% | 40,5% | 66,3% | 57% |
| sesi hari Minggu | 24% | 26,4% | 75% | 63,3% |
| tagihan digelembungkan | 11,7% | 8,2% | 11,1% | 10,7% |
| sebagian tanpa rujukan | 0% | 17,5% | 34,4% | 49,5% |
| rujukan janggal | 2,1% | 100% | 2,1% | 36,7% |

## Uji luar

Persen bobot yang ditandai pada data sampel kontekstual (tidak dipakai melatih).

| Sampel | Bulan-pasien | anomali-v1 (Isolation Forest) | Kelangkaan nasional | anomali-v2 (umur) |
|---|---|---|---|---|
| KM20152023_fkrtl | 27.062 | 3,59% | 3,07% | 3,7% |
| COV20152024_fkrtl | 8.910 | 5,37% | 4,59% | 5,73% |

## Batasan

Tanpa label, tidak ada cara objektif memilih metode terbaik dari angka di atas. Yang menentukan adalah hasil
panggilan: berapa bagian yang ditandai tiap metode berakhir Tidak sesuai.
