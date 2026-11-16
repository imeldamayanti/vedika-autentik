# Perbandingan metode deteksi anomali tanpa label

Dibuat oleh `ai-service/scripts/compare_anomaly_methods.py` pada 2026-11-17. Jangan disunting manual.

Empat metode tanpa label dibandingkan pada data yang sama: 40.650 bulan-pasien fisioterapi nyata
(Juli–Desember 2023, 2024, data sampel reguler BPJS), enam fitur yang sama dengan `anomali-v1`, dan
volume yang sama (sekitar 1,5% bobot nasional ditandai per metode).

- **Isolation Forest**: mengisolasi titik jarang dengan belahan acak (model `anomali-v1`).
- **Local Outlier Factor**: membandingkan kerapatan satu titik dengan 50 tetangganya.
- **One-Class SVM**: mempelajari batas di sekeliling tagihan normal (kernel RBF, dilatih pada 8.000 sampel).
- **Kelangkaan gabungan**: pembanding paling sederhana, seberapa jarang gabungan bin itu secara nasional.

Semua metode dinilai langsung dari skornya. Model `anomali-v1` yang disimpan memakai tabel, dan gabungan yang muncul
kurang dari 10 kali selalu ditandai; karena itu angka Isolation Forest di sini sedikit berbeda dari `EVALUASI-ANOMALI.md`.

## Hasil di data nyata

| Metode | Ditandai | Hanya model | Aturan ATAU model | Antartahun: ditandai 2024 oleh model 2023 / 2024 | Antartahun: Jaccard |
|---|---|---|---|---|---|
| Isolation Forest | 1,54% | 0,7% | 2,75% | 1,03% / 1,54% | 0,7 |
| Local Outlier Factor | 1,52% | 0,93% | 2,97% | 1,36% / 1,5% | 0,86 |
| One-Class SVM | 1,62% | 1,22% | 3,26% | 33,74% / 33,6% | 0,93 |
| Kelangkaan gabungan | 1,54% | 1,02% | 3,06% | 1,6% / 1,51% | 0,59 |
| Suara ≥ 2 dari 3 | 1,49% | 0,85% | 2,9% | – | – |
| Salah satu dari 3 (ATAU) | 2,57% | 1,65% | 3,7% | – | – |

## Seberapa sering metode sepakat (Jaccard himpunan yang ditandai)

| | Isolation Forest | Local Outlier Factor | One-Class SVM | Kelangkaan gabungan |
|---|---|---|---|---|
| Isolation Forest | 1 | 0,27 | 0,14 | 0,26 |
| Local Outlier Factor | 0,27 | 1 | 0,25 | 0,7 |
| One-Class SVM | 0,14 | 0,25 | 1 | 0,24 |
| Kelangkaan gabungan | 0,26 | 0,7 | 0,24 | 1 |

Ditandai keempat metode sekaligus: 0,27% bobot.

## Uji sisipan (Tingkat B, sintetis)

2.000 bulan-pasien biasa 2024 (tidak terpicu aturan, tidak ditandai metode mana pun) diubah dengan satu
manipulasi, lalu dinilai. Persen = bagian yang tertangkap. Manipulasinya kami rancang sendiri, jadi ini menguji
apa yang bisa dilihat tiap metode, bukan kinerja di lapangan. "Rujukan janggal" meniru pola temuan utama
Isolation Forest, jadi angka 100% di sana sebagian melingkar.

| Manipulasi | Aturan | Isolation Forest | Local Outlier Factor | One-Class SVM | Kelangkaan gabungan | Suara ≥ 2 dari 3 | Salah satu dari 3 (ATAU) |
|---|---|---|---|---|---|---|---|
| pemadatan seminggu | 26% | 27,1% | 32,2% | 41,1% | 66,4% | 45% | 70,3% |
| rujukan janggal | 2% | 100% | 2% | 2% | 2% | 2% | 100% |
| sesi hari Minggu | 22,7% | 8,8% | 74,5% | 54,4% | 73,2% | 73,2% | 74,6% |
| tagihan digelembungkan | 9,8% | 3,1% | 10,9% | 9,8% | 11,3% | 10,9% | 11,9% |

## Cara membaca

- Volume sama, orangnya berbeda: metode hanya sebagian sepakat. Local Outlier Factor dan Kelangkaan gabungan
  paling mirip karena keduanya pada dasarnya mengukur kerapatan.
- Tiap metode melihat hal yang berbeda: Isolation Forest satu-satunya yang menangkap gabungan rujukan janggal,
  tetapi lemah pada sesi hari Minggu; Local Outlier Factor dan Kelangkaan gabungan sebaliknya.
- One-Class SVM tidak cocok untuk enam fitur berbin kasar: di uji antartahun skornya mendatar untuk banyak
  gabungan sekaligus, sehingga ambang 1,5% tidak bisa dipasang.
- Tanpa label, tidak ada cara objektif memilih metode terbaik. Ukuran yang menentukan adalah hasil panggilan:
  berapa bagian yang ditandai tiap metode berakhir Tidak sesuai. Panggilan konfirmasi Vedika menghasilkan ukuran itu,
  dan ukuran yang sama bisa dipakai untuk mesin deteksi lain, termasuk milik BPJS.
