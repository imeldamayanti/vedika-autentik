# Evaluasi model anomali (anomali-v1)

Dibuat oleh `ai-service/scripts/train_anomaly_model.py` pada 2026-11-17. Jangan disunting manual.

## Apa yang dilakukan model

Isolation Forest **tanpa label** (unsupervised) dilatih pada 40.650 bulan-pasien fisioterapi
rawat jalan dari data sampel reguler BPJS. Model mencari tagihan bulanan yang polanya jarang dibanding seluruh tagihan
nasional, tanpa diberi tahu mana yang curang. Data sampel memang tidak punya label itu.

Pasien ditelepon bila **aturan (≥ 2 indikator) ATAU model** menandainya. Hasilnya tetap ditentukan jawaban peserta.

Fitur hanya hal yang bisa dikonfirmasi peserta lewat telepon: jumlah sesi sebulan, sesi terbanyak dalam satu minggu,
sesi hari Minggu, bulan berturut-turut, pangsa kunjungan tanpa nomor rujukan FKTP, dan pangsa yang dirujuk dari
kab/kota lain. Kode diagnosis dan INA-CBG tidak dipakai di tingkat pasien karena peserta tidak bisa
mengonfirmasinya; keduanya dipakai di tingkat RS (bagian terakhir).

## Data

| Berkas | Tahun | Bulan-pasien (Juli–Desember) |
|---|---|---|
| `202303_fkrtl.dta` | 2023 | 18.193 |
| `202403_fkrtl.dta` | 2024 | 22.457 |

Hanya Juli–Desember tiap berkas yang dipakai. Fitur bulan berturut-turut melihat 6 bulan ke belakang, dan tiap berkas
mulai Januari, jadi Januari–Mei tidak punya riwayat lengkap (Januari–Juni tetap dipakai sebagai riwayat). Berkas
tidak digabung per peserta: data sampel tiap tahun diambil terpisah.

## Privasi

- Model disimpan sebagai tabel: satu skor per gabungan bin yang muncul pada minimal 10 bulan-pasien
  (77 gabungan). Pohon Isolation Forest, baris, nomor peserta, dan nilai minimum/maksimum tidak disimpan.
- Gabungan yang lebih jarang (0,73% bobot nasional) tidak disimpan dan dianggap
  tidak biasa oleh penilai. Isolation Forest sebelum ditabelkan juga menandai 58,3% bobot gabungan itu.
- Batas bin ditetapkan tangan (ambang aturan dan angka bulat), bukan dari data.

## Perilaku di data nyata (Tingkat A)

Ambang dipilih supaya model menandai sekitar 1,5% bulan-pasien nasional, setara aturan.
"Per bulan" = perkiraan nasional dengan bobot sampel, rata-rata atas 12 bulan.

| Kelompok | Bulan-pasien | Kunjungan | Bobot nasional | Per bulan |
|---|---|---|---|---|
| Ditandai model | 714 | 5.766 | 1,53% | ≈4.345 |
| Dipicu aturan (≥ 2 indikator) | 890 | 8.178 | 2,05% | ≈5.809 |
| Keduanya | 415 | 4.027 | 0,85% | ≈2.425 |
| Hanya model (tidak terlihat aturan) | 299 | 1.739 | 0,68% | ≈1.921 |
| Hanya aturan | 475 | 4.151 | 1,19% | ≈3.384 |
| Ditelepon: aturan ATAU model | 1.189 | 9.917 | 2,72% | ≈7.729 |

- Persen ditandai per bulan: 0,9% sampai 3,29%.
- 423 kelompok RS sejenis punya minimal 30 bulan-pasien;
  272 di antaranya tanpa satu pun yang ditandai. 10% kelompok teratas memuat
  80,2% bobot yang ditandai.
- Kestabilan: irisan (Jaccard) himpunan yang ditandai antara seed pertama dan empat seed lain:
  0,94, 0,91, 0,81, 0,92.

Alasan pertama pada kasus "hanya model":

| Alasan | Bulan-pasien |
|---|---|
| Sesi terbanyak seminggu | 116 |
| Hanya gabungannya yang jarang | 61 |
| Dirujuk dari kab/kota lain | 41 |
| Kunjungan tanpa rujukan FKTP | 39 |
| Sesi hari Minggu | 30 |
| Sesi sebulan | 12 |

Pola "hanya model" yang paling sering:

| Pola | Bulan-pasien |
|---|---|
| 5–8 sesi sebulan, paling banyak 2 sesi seminggu, tanpa sesi hari Minggu, 6 bulan atau lebih berturut-turut, semua kunjungan tanpa rujukan FKTP, semua dirujuk dari kab/kota lain | 61 |
| 5–8 sesi sebulan, 3 sesi dalam satu minggu, tanpa sesi hari Minggu, 3–5 bulan berturut-turut, semua kunjungan tanpa rujukan FKTP, dirujuk dari kab/kota yang sama | 28 |
| 5–8 sesi sebulan, 3 sesi dalam satu minggu, tanpa sesi hari Minggu, 1–2 bulan berturut-turut, semua kunjungan tanpa rujukan FKTP, semua dirujuk dari kab/kota lain | 27 |
| 5–8 sesi sebulan, 3 sesi dalam satu minggu, tanpa sesi hari Minggu, 3–5 bulan berturut-turut, semua kunjungan dengan rujukan FKTP, semua dirujuk dari kab/kota lain | 21 |

## Validasi antartahun

Model dilatih ulang hanya dari 2023, lalu dipakai pada 2024 yang belum pernah dilihatnya.
Pembanding: model yang dilatih dari 2024 sendiri.

| Ukuran | Hasil |
|---|---|
| Ditandai di 2024 oleh model 2023 | 1,41% |
| Ditandai di 2024 oleh model 2024 | 1,51% |
| Irisan (Jaccard) kedua himpunan yang ditandai | 0,65 |
| Hanya model (tidak terpicu aturan), model 2023 | 0,76% |
| Bobot 2024 di gabungan yang tidak ada di tabel 2023 | 1,34% |

## Uji luar (tidak dipakai melatih)

Tabel akhir dipakai pada data sampel kontekstual: peserta yang dipilih karena penyakit tertentu, jadi bukan
gambaran semua pasien fisioterapi. Bobotnya mewakili kelompok penyakit itu, bukan nasional. Tujuannya hanya
melihat apakah model berperilaku wajar pada populasi lain.

| Sampel | Tahun | Bulan-pasien | Ditandai model | Dipicu aturan | Hanya model |
|---|---|---|---|---|---|
| KM20152023_fkrtl | 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023 | 27.062 | 3,59% | 3,34% | 1,51% |
| COV20152024_fkrtl | 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024 | 8.910 | 5,37% | 2,52% | 2,85% |

## Tingkat RS

Isolation Forest kedua atas 423 kelompok RS sejenis (minimal 30 bulan-pasien),
dengan fitur pangsa terpicu, rata-rata sesi, pangsa dengan sesi Minggu, pangsa tanpa rujukan FKTP, pangsa dari kab/kota lain,
pangsa diagnosis jarang, dan pangsa kode INA-CBG jarang (kode di bawah 1% kunjungan nasional). Ditandai
21 kelompok (5% teratas). Identitas kelompok tidak disimpan.

| Fitur paling menyimpang | Kelompok RS |
|---|---|
| Diagnosis jarang | 7 |
| Pangsa terpicu aturan | 6 |
| Kode INA-CBG jarang | 5 |
| Kunjungan tanpa rujukan FKTP | 3 |

## Batasan

- Tidak ada label kecurangan di data sampel, jadi angka di atas adalah perilaku, bukan ketepatan.
  Ketepatan baru bisa diukur dari hasil panggilan (berapa yang ditandai model berakhir Tidak sesuai).
- Nomor rujukan FKTP kosong bisa berarti kunjungan kontrol dengan surat kontrol RS, bukan pelanggaran.
  Arti sinyal ini perlu dipastikan bersama verifikator BPJS.
- Data sampel tidak memuat identitas RS. "Kelompok RS sejenis" = kab/kota + kepemilikan + jenis + tipe.
