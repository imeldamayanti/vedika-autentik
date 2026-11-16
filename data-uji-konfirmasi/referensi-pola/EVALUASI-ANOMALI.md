# Evaluasi model anomali (anomali-v2)

Dibuat oleh `ai-service/scripts/train_anomaly_model.py` pada 2026-11-17. Jangan disunting manual.

## Apa yang dilakukan model

Model **tanpa label** mengukur seberapa jarang pola satu tagihan bulanan fisioterapi di antara pasien
seusia, dari 40.650 bulan-pasien data sampel reguler BPJS 2023–2024.
Pola = enam fitur yang bisa dikonfirmasi peserta lewat telepon: sesi sebulan, sesi terbanyak seminggu, sesi hari
Minggu, bulan berturut-turut, pangsa kunjungan tanpa rujukan FKTP, dan pangsa yang dirujuk dari kab/kota lain.

Peluang pola p dihitung dari pangsa berbobot pola itu di kelompok umur pasien, dihaluskan ke pangsa nasional
(alfa 1000); skor = −ln p. Ditandai bila skor ≥ 7,4504, yaitu
peluang di bawah 0,058%. Ambang dipilih supaya sekitar
1,5% bobot nasional ditandai, setara aturan. Pasien ditelepon bila
**aturan (≥ 2 indikator) ATAU model** menandainya; hasilnya tetap ditentukan jawaban peserta.

## Memilih kelompok pembanding

Pola dinilai jarang dibanding pasien sekelompok. Kelompok dipilih dengan data tahun lain yang tidak dipakai
melatih: rata-rata log-peluang berbobot (makin tinggi makin baik) dari model yang dilatih satu tahun dan dinilai
pada tahun lainnya. Alfa = kekuatan penghalusan ke pangsa nasional.

| Kelompok | Jumlah kelompok | Alfa | Latih 2023, uji 2024 | Latih 2024, uji 2023 |
|---|---|---|---|---|
| Nasional (tanpa kelompok) | – | 10 | -2,5997 | -2,8026 |
| Kelompok umur | 4 | 10 | -2,5856 | -2,7902 |
| Kelompok umur | 4 | 50 | -2,5855 | -2,79 |
| Kelompok umur | 4 | 200 | -2,5852 | -2,7896 |
| Kelompok umur | 4 | 1000 | -2,5851 | -2,789 |
| Diagnosis sekunder | 12 | 10 | -2,6113 | -2,8136 |
| Diagnosis sekunder | 12 | 50 | -2,6091 | -2,812 |
| Diagnosis sekunder | 12 | 200 | -2,6042 | -2,8082 |
| Diagnosis sekunder | 12 | 1000 | -2,5976 | -2,8014 |

- Kelompok umur: selisih terhadap nasional 0,0146 (2023 ke 2024) dan 0,0136 (2024 ke 2023).
- Diagnosis sekunder: selisih terhadap nasional 0,0021 (2023 ke 2024) dan 0,0012 (2024 ke 2023). Selisih ini hanya muncul pada penghalusan terkuat, saat model hampir sama dengan nasional.

Model memakai kelompok umur dengan alfa 1000, alfa dengan
log-peluang tertinggi di kedua arah.

## Data

| Berkas | Tahun | Bulan-pasien (Juli–Desember) |
|---|---|---|
| `202303_fkrtl.dta` | 2023 | 18.193 |
| `202403_fkrtl.dta` | 2024 | 22.457 |

Hanya Juli–Desember tiap berkas yang dinilai: bulan berturut-turut melihat 6 bulan ke belakang dan tiap berkas
mulai Januari. Berkas tidak digabung per peserta.

## Privasi

- Model menyimpan pangsa pola dan pangsa bin hanya untuk sel dengan minimal 10 bulan-pasien
  (77 pola nasional). Tidak ada baris, nomor peserta, atau nilai minimum/maksimum.
- Pola yang lebih jarang dari itu tidak disimpan dan selalu ditandai.
- Batas bin ditetapkan tangan (ambang aturan dan angka bulat), bukan dari data.

## Perilaku di data nyata

"Per bulan" = perkiraan nasional dengan bobot sampel, rata-rata atas 12 bulan.

| Kelompok | Bulan-pasien | Kunjungan | Bobot nasional | Per bulan |
|---|---|---|---|---|
| Ditandai model | 772 | 5.152 | 1,53% | ≈4.331 |
| Dipicu aturan (≥ 2 indikator) | 890 | 8.178 | 2,05% | ≈5.809 |
| Keduanya | 272 | 2.388 | 0,47% | ≈1.345 |
| Hanya model (tidak terlihat aturan) | 500 | 2.764 | 1,05% | ≈2.985 |
| Hanya aturan | 618 | 5.790 | 1,57% | ≈4.463 |
| Ditelepon: aturan ATAU model | 1.390 | 10.942 | 3,1% | ≈8.794 |

- Persen ditandai per bulan (tanpa bobot): 1,35% sampai 2,72%.

Per kelompok umur:

| Kelompok umur | Bulan-pasien | Ditandai model |
|---|---|---|
| <18 | 4.798 | 1,88% |
| 18-39 | 4.398 | 1,88% |
| 40-59 | 17.192 | 1,59% |
| 60+ | 14.262 | 1,26% |

Alasan pertama pada kasus "hanya model":

| Alasan pertama | Bulan-pasien |
|---|---|
| Sesi terbanyak seminggu | 118 |
| Kunjungan tanpa rujukan FKTP | 112 |
| Dirujuk dari kab/kota lain | 104 |
| Sesi hari Minggu | 102 |
| Sesi sebulan | 64 |

Pola "hanya model" yang paling sering:

| Pola | Bulan-pasien |
|---|---|
| 5–8 sesi sebulan, paling banyak 2 sesi seminggu, tanpa sesi hari Minggu, 1–2 bulan berturut-turut, sebagian kunjungan tanpa rujukan FKTP, dirujuk dari kab/kota yang sama | 24 |
| 5–8 sesi sebulan, 4 sesi atau lebih dalam satu minggu, tanpa sesi hari Minggu, 1–2 bulan berturut-turut, semua kunjungan dengan rujukan FKTP, dirujuk dari kab/kota yang sama | 20 |
| 1–4 sesi sebulan, paling banyak 2 sesi seminggu, tanpa sesi hari Minggu, 1–2 bulan berturut-turut, sebagian kunjungan tanpa rujukan FKTP, sebagian dirujuk dari kab/kota lain | 19 |
| 5–8 sesi sebulan, paling banyak 2 sesi seminggu, 2 sesi atau lebih hari Minggu, 1–2 bulan berturut-turut, semua kunjungan dengan rujukan FKTP, dirujuk dari kab/kota yang sama | 18 |
| 5–8 sesi sebulan, paling banyak 2 sesi seminggu, tanpa sesi hari Minggu, 3–5 bulan berturut-turut, sebagian kunjungan tanpa rujukan FKTP, sebagian dirujuk dari kab/kota lain | 16 |

## Validasi antartahun

| Ukuran | Hasil |
|---|---|
| Ditandai di 2024 oleh model 2023 | 1,34% |
| Ditandai di 2024 oleh model 2024 | 1,51% |
| Irisan (Jaccard) kedua himpunan yang ditandai | 0,669 |
| Hanya model (tidak terpicu aturan), model 2023 | 0,76% |
| Bobot 2024 pada pola yang tidak ada di tabel 2023 | 1,34% |

## Uji luar (tidak dipakai melatih)

Model akhir dipakai pada data sampel kontekstual: peserta yang dipilih karena penyakit tertentu, jadi bukan
gambaran semua pasien fisioterapi. Bobotnya mewakili kelompok penyakit itu.

| Sampel | Tahun | Bulan-pasien | Ditandai model | Dipicu aturan | Hanya model |
|---|---|---|---|---|---|
| KM20152023_fkrtl | 2015–2023 | 27.062 | 3,7% | 3,34% | 2,2% |
| COV20152024_fkrtl | 2015–2024 | 8.910 | 5,73% | 2,52% | 3,89% |

## Tingkat RS (corong)

Untuk tiap kelompok RS sejenis (kab/kota + kepemilikan + jenis + tipe) dengan minimal
30 bulan-pasien: jumlah bulan-pasien yang dipilih (aturan ATAU model) dibanding
harapan menurut umur pasiennya. Simpangan dilebarkan dengan faktor sebaran antar-RS
2,54 (penyesuaian overdispersi Spiegelhalter), karena RS memang lebih beragam
dari yang dijelaskan umur saja.

| Ukuran | Hasil |
|---|---|
| Kelompok RS sejenis yang dinilai | 423 |
| Di atas batas 95% | 44 |
| Di atas batas 99,8% | 27 |
| Pangsa pasien dipilih yang berada di kelompok di atas 99,8% | 43,3% |

Identitas kelompok tidak disimpan.

## Batasan

- Tidak ada label kecurangan, jadi angka di atas adalah perilaku, bukan ketepatan. Ketepatan diukur dari hasil
  panggilan: berapa yang ditandai model berakhir Tidak sesuai.
- Jarang tidak sama dengan curang: pola yang jarang bisa sah.
- Nomor rujukan FKTP kosong bisa berarti kunjungan kontrol dengan surat kontrol RS. Arti sinyal ini perlu
  dipastikan bersama verifikator BPJS.
- Data sampel tidak memuat identitas RS, jadi kelompok RS sejenis hanya mendekati satu RS.
