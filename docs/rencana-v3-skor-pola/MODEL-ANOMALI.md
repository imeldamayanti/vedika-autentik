# Model anomali `anomali-v1`: penjelasan teknis

Model **tanpa label (unsupervised)** yang ikut memilih tagihan fisioterapi mana yang dikonfirmasi lewat telepon. Dilatih 17 November 2026 dari data sampel reguler BPJS tahun 2023 dan 2024. Angka di dokumen ini berasal dari berkas yang di-commit: `data-uji-konfirmasi/referensi-pola/model-anomali-v1.json`, `ai-service/data/reference/pola-2024/anomali-nyata.json`, dan `data-uji-konfirmasi/referensi-pola/EVALUASI-ANOMALI.md`. Rincian kasus "hanya aturan" di bagian 9 diukur langsung dari data mentah di laptop dan tidak disimpan di repositori.

Status: model sudah dilatih, ditabelkan, diuji, dan dievaluasi di data nyata. Web dalam **mode simulasi** sudah memakainya (kolom "Dipilih oleh" dan bagian "Mengapa dipilih"). **Belum** tersambung ke backend dan database, jadi mode API masih memilih pasien hanya dengan aturan.

---

## 1. Peran model dalam alur

```
Klaim fisioterapi bulan ini (per pasien per bulan)
   │
   ├── Aturan I1–I4: ≥ 2 indikator aktif ──┐
   │                                       ├── ATAU ──► ditelepon agen AI ──► jawaban peserta
   └── Model anomali: pola jarang ─────────┘                                    │
                                                                                ▼
                                             aturan label (aturan.py): Sesuai / Tidak sesuai / ...
                                                                                │
                                                                                ▼
                                                             keputusan verifikator
```

- **Aturan** menangkap pola yang sudah dikenal: lebih dari 8 sesi sebulan, 3 sesi seminggu, 6 bulan berturut-turut, sesi hari libur.
- **Model** menangkap tagihan yang polanya jarang dibanding seluruh tagihan nasional, termasuk pola yang tidak dijelaskan aturan mana pun. Model tidak menandai tagihan *karena* tidak terkena aturan: hampir semua tagihan tidak terkena aturan dan itu normal.
- **Hasil** tetap ditentukan jawaban peserta. Model tidak memberi label, tidak memberi saran tindakan, dan tidak mengubah status RS.

## 2. Mengapa model baru

`pola-v1` (regresi logistik) dilatih membedakan tagihan normal dari "pelanggaran" buatan, yaitu tagihan normal yang diubah dengan manipulasi yang meniru aturan (tambah sesi, sesi hari libur, pemadatan, episode panjang). Akibatnya model pada dasarnya mempelajari ulang aturan I1–I4. Ia hanya bisa mengurutkan antrean yang sudah dipilih aturan, dan urutan tidak banyak berguna bila semua pasien terpicu bisa ditelepon sekaligus.

Data sampel BPJS tidak punya label kecurangan. Pendekatan yang cocok adalah **deteksi anomali tanpa label**: pelajari bentuk tagihan yang umum, lalu tandai yang menyimpang.

## 3. Data dan kohort

| | |
|---|---|
| Sumber latih | `Folder Data Asli/Data Sampel 2015-2023/Data Sampel Reguler Edisi 2024/data/202303_fkrtl.dta` (kunjungan RS 2023) dan `Folder Data Asli/2025 2/Data Sampel Reguler Edisi 2025/data/202403_fkrtl.dta` (kunjungan RS 2024). Data sampel reguler BPJS Kesehatan dari panitia. |
| Kohort | rawat jalan (`FKL10 = 1`), poli rehabilitasi medik/fisioterapi (`FKL11`), pola prosedur fisioterapi di `FKL18A`/`FKL30` |
| Jendela | **Juli–Desember** tiap tahun. Januari–Juni hanya dipakai sebagai riwayat (lihat di bawah). |
| Ukuran | **40.650 bulan-pasien**: 18.193 (2023) + 22.457 (2024) |
| Bobot | `PSTV15` (bobot sampel ke populasi nasional tahun itu) |
| Satuan analisis | **bulan-pasien**: semua kunjungan fisioterapi satu peserta dalam satu bulan kalender, setara satu "tagihan bulanan" |

**Mengapa hanya Juli–Desember.** Fitur `episode` (bulan berturut-turut) melihat 6 bulan ke belakang, dan tiap berkas mulai Januari. Di Januari–Mei tidak ada riwayat, sehingga semua pasien tampak baru mulai: pangsa "6 bulan atau lebih" 0% di Januari–Mei 2024, padahal 15,7–20,9% di Juni–Desember. Versi pertama model ini memakai 12 bulan penuh dan terkena bias tersebut; versi ini sudah diperbaiki.

**Berkas tidak digabung per peserta.** Data sampel tiap tahun diambil terpisah (3.544 peserta kebetulan ada di keduanya), jadi riwayat tidak disambung lintas berkas.

**Yang tidak dipakai untuk melatih:**

- Data sampel **kontekstual** (Kesehatan Mental, COVID, DM, TB, KIA): peserta dipilih karena penyakit tertentu, jadi bukan gambaran pasien fisioterapi pada umumnya. Hanya dipakai sebagai uji luar (bagian 9).
- Data sampel reguler tahun lain: tidak ada. Berkas kunjungan RS reguler hanya tersedia untuk 2023 dan 2024.

## 4. Fitur

Prinsip: di tingkat pasien hanya dipakai hal yang **bisa dikonfirmasi peserta lewat telepon**, yaitu pola kunjungan dan asal rujukan. Pertanyaan agen AI memang tentang itu.

| Fitur | Definisi | Kolom sumber | Bin | Pangsa nasional per bin |
|---|---|---|---|---|
| `sesi` | jumlah kunjungan dalam bulan itu | `FKL03` | 1–4 · 5–8 · 9–12 · 13+ | 68,3% · 29,4% · 2,2% · 0,11% |
| `maks_minggu` | kunjungan terbanyak dalam satu minggu Senin–Minggu | `FKL03` | ≤ 2 · 3 · ≥ 4 | 96,7% · 3,1% · 0,16% |
| `ahad_libur` | kunjungan pada hari Minggu (data tanpa daftar libur nasional) | `FKL03` | 0 · 1 · 2+ | 99,5% · 0,38% · 0,15% |
| `episode` | bulan berturut-turut dengan kunjungan, sampai bulan ini | `FKL03` | 1–2 · 3–5 · 6+ | 55,0% · 26,0% · 18,9% |
| `tanpa_rujukan` | pangsa kunjungan tanpa nomor rujukan FKTP | `FKP02` kosong | 0 · sebagian · semua | 89,2% · 0,55% · 10,2% |
| `lintas_wilayah` | pangsa kunjungan yang dirujuk dari kab/kota lain | `FKL26` ≠ `FKL06` | 0 · sebagian · semua | 84,9% · 0,24% · 14,9% |

Empat fitur pertama memakai definisi bersama di `data-uji-konfirmasi/tools/pola.py`. Dua fitur rujukan baru, didefinisikan di `data-uji-konfirmasi/tools/anomali.py`.

Batas bin **ditetapkan tangan**: ambang aturan (8/9 sesi, 2/3 sesi seminggu, 0/1 hari Minggu, 5/6 bulan) dan angka bulat. Batas tidak dihitung dari data, jadi tidak membawa nilai dari baris tertentu.

### Diperiksa tetapi tidak dipakai di tingkat pasien

| Kolom | Alasan |
|---|---|
| Biaya ditagih `FKL47` | Mengikuti tarif INA-CBG yang tetap: biaya ditagih = biaya diverifikasi pada 99,999% kunjungan 2024, dan rasio terhadap median kunjungan sejenis (kode INA-CBG, tipe RS, regional tarif) berada di 0,9–1,1 pada 99,4% bulan-pasien 2024. Tidak ada variasi untuk dipelajari. |
| Prosedur, alat, dan obat khusus `FKL35`–`FKL46` | Kosong (`NONE`) di seluruh kohort 2024, kecuali 2 kunjungan. |
| Kelas rawat `FKL13` | Satu nilai untuk seluruh kohort 2024. |
| Segmen peserta `FKL12` (PBI, PBPU, dst.) | Sengaja tidak dipakai: menggambarkan peserta, bukan perilaku tagihan, dan berisiko tidak adil. |
| Diagnosis `FKL17A`, kode INA-CBG `FKL19` | Peserta tidak bisa mengonfirmasi pengodean lewat telepon. Dipakai di **tingkat RS** (bagian 10). |

## 5. Model: Isolation Forest

Isolation Forest (Liu, Ting & Zhou, 2008) adalah kumpulan pohon keputusan acak. Di tiap simpul, pohon memilih satu fitur secara acak dan satu titik potong acak di antara nilai terkecil dan terbesar fitur itu di simpul tersebut, lalu membelah data. Tagihan yang polanya jarang **terisolasi setelah sedikit belahan**. Tagihan yang umum butuh banyak belahan karena dikelilingi banyak tagihan serupa.

Skor anomali satu bulan-pasien `x`:

```
s(x) = 2 ^ ( −E[h(x)] / c(ψ) )
```

- `h(x)`: panjang jalur dari akar sampai `x` terisolasi di satu pohon; `E[h(x)]`: rata-ratanya atas semua pohon.
- `c(ψ) = 2·H(ψ−1) − 2(ψ−1)/ψ`: panjang jalur rata-rata pohon acak berukuran `ψ`, dengan `H(i) ≈ ln(i) + 0,5772` (bilangan harmonik). Dipakai sebagai penormal.
- `s` mendekati 1: sangat mudah diisolasi (tidak biasa). `s` sekitar 0,5 atau kurang: umum.
- Di scikit-learn, `score_samples` mengembalikan `−s(x)`. Kami membalik tandanya, sehingga skor makin tinggi makin tidak biasa.

| Parameter | Nilai | Alasan |
|---|---|---|
| Jumlah pohon | 1.000 | Kestabilan antar-seed (bagian 9) |
| Sampel per pohon `ψ` | 512 | Cukup untuk melihat pola langka tanpa tertutup massa tagihan umum |
| Seed | 7 | Seed lain dipakai untuk uji kestabilan (11, 23, 42, 99) |
| Masukan | 6 fitur sebagai nomor bin (bilangan bulat berurutan) | Urutan bin bermakna: lebih banyak sesi, lebih lama, lebih banyak tanpa rujukan |
| Bobot sampel | Tidak dipakai saat membangun pohon | Bobot `PSTV15` dipakai untuk pangsa nasional dan ambang |

Pustaka: `scikit-learn` `IsolationForest`, hanya di grup dependensi `data` di laptop. Kode: `ai-service/src/vedika_ai/anomali_reference.py`.

**Mengapa Isolation Forest:** tanpa label, cepat (seluruh skrip termasuk membaca dua berkas mentah sekitar 40 detik di laptop), tidak berasumsi bentuk sebaran, dan cocok untuk fitur berurutan yang jumlah nilainya sedikit. Alternatif yang dipertimbangkan: kerapatan langsung dari histogram (lebih sederhana, tetapi skornya hanya mengukur kelangkaan satu sel tanpa melihat sel tetangga), dan autoencoder (butuh data dan penyetelan lebih banyak untuk 6 fitur).

## 6. Dari Isolation Forest ke tabel

Pohon-pohon Isolation Forest tidak disimpan. Yang disimpan adalah **tabel**:

1. Tiap bulan-pasien dipetakan ke gabungan 6 bin, misalnya `1|0|0|2|2|2`.
2. Semua bulan-pasien dalam satu gabungan punya fitur yang sama, jadi skornya sama.
3. Gabungan yang muncul pada **minimal 10 bulan-pasien** disimpan dengan skor dan pangsa bobot nasionalnya: **77 gabungan, 99,27% bobot nasional**.
4. Gabungan yang lebih jarang (0,73% bobot) **tidak disimpan**. Penilai menganggapnya tidak biasa, karena muncul kurang dari 10 kali di 40.650 bulan-pasien. Pemeriksaan konsistensi: Isolation Forest sebelum ditabelkan juga menandai 58% bobot gabungan langka itu.

Dua alasan:

- **Privasi.** Pohon Isolation Forest menyimpan titik potong dan ukuran daun. Daun berukuran 1 menunjukkan keberadaan satu baris tertentu. Tabel dengan ambang 10 baris mengikuti aturan agregat yang sama dengan referensi `pola-2024`.
- **Backend tanpa numpy dan scikit-learn.** Menilai cukup dengan mencari kunci di kamus. Penilainya `data-uji-konfirmasi/tools/anomali.py`, hanya pustaka standar.

Contoh isi tabel:

| Gabungan | Arti | Skor | Pangsa nasional |
|---|---|---|---|
| `0|0|0|0|0|0` | 1–4 sesi, ≤ 2 seminggu, tanpa Minggu, 1–2 bulan, dengan rujukan, kab/kota sama | 0,3736 | 30,1% |
| `1|0|0|0|0|0` | sama, tetapi 5–8 sesi | 0,4079 | 10,2% |
| `0|0|0|0|2|2` | 1–4 sesi, semua tanpa rujukan, semua dari kab/kota lain | 0,5601 | 1,7% |
| `0|0|0|2|2|2` | seperti di atas, ditambah 6 bulan atau lebih berturut-turut | 0,6734 (di bawah ambang) | 0,25% |
| `1|0|0|2|2|2` | seperti di atas, tetapi 5–8 sesi | 0,6913 | 0,09% |
| `2|1|0|2|2|0` | 9–12 sesi, 3 seminggu, 6+ bulan, semua tanpa rujukan | 0,7340 (tertinggi) | 0,05% |

## 7. Ambang

Ambang dipilih supaya model menandai sekitar **1,5% bobot nasional**, sebanding dengan aturan (2,05% di jendela yang sama), sehingga beban panggilan dari model sebanding dengan dari aturan.

Ambang = skor gabungan tempat pangsa yang ditandai (gabungan berskor sama atau lebih, ditambah gabungan langka) mencapai 1,5%. Hasilnya **`ambang = 0,6803`**: 14 gabungan di tabel (0,80% bobot) ditambah gabungan langka (0,73%) = **1,53%**.

Keputusan per bulan-pasien (`anomali.nilai`):

```
gabungan ada di tabel  → skor = tabel[gabungan].skor;  ditandai = skor ≥ 0,6803
gabungan tidak ada     → skor = None;  langka = True;  ditandai = True
```

## 8. Alasan untuk verifikator

Model linear seperti `pola-v1` punya sumbangan per fitur yang eksak. Isolation Forest tidak punya. Alasannya dibuat dari kelangkaan yang bisa diperiksa siapa pun di tabel (`anomali.alasan`):

1. **Bin yang jarang**: tiap fitur yang bin-nya dimiliki kurang dari 10% tagihan bulanan nasional, paling jarang dulu, paling banyak 2.
2. **Kalimat gabungan**: bagian yang bukan bin terbanyak fiturnya, ditambah seberapa sering gabungan itu muncul secara nasional.

Kalimat gabungan penting karena 61 dari 299 kasus "hanya model" tidak punya satu fitur pun yang jarang. Yang jarang hanya gabungannya.

Contoh:

| Tagihan bulanan | Skor | Alasan |
|---|---|---|
| 6 sesi, ≤ 2 seminggu, tanpa Minggu, 7 bulan, semua tanpa rujukan, semua dari kab/kota lain | 0,6913, ditandai | "Gabungan 5–8 sesi sebulan, 6 bulan atau lebih berturut-turut, semua kunjungan tanpa rujukan FKTP, dan semua dirujuk dari kab/kota lain muncul pada kurang dari 0,1% tagihan bulanan fisioterapi nasional 2023–2024." |
| 3 sesi, sisanya sama dengan di atas | 0,6734, tidak ditandai | (di bawah ambang; gabungan ini muncul pada 0,2% tagihan bulanan) |
| 10 sesi, 4 dalam seminggu, 2 hari Minggu, 3 bulan, dengan rujukan | langka, ditandai | "2 sesi atau lebih hari Minggu: hanya 0,2% tagihan bulanan fisioterapi nasional." · "4 sesi atau lebih dalam satu minggu: hanya 0,2% …" · "Gabungan 9–12 sesi sebulan, 4 sesi atau lebih dalam satu minggu, 2 sesi atau lebih hari Minggu, dan 3–5 bulan berturut-turut muncul pada kurang dari 10 tagihan bulanan di data sampel BPJS 2023–2024." |
| 4 sesi, ≤ 2 seminggu, tanpa Minggu, 2 bulan, dengan rujukan | 0,3736, tidak ditandai | "Gabungan pola ini muncul pada 30,1% tagihan bulanan fisioterapi nasional 2023–2024." |

Alasan tidak pernah memakai kata "fraud" atau "curang".

## 9. Evaluasi

Data sampel tidak punya label kecurangan, jadi **ketepatan tidak bisa diukur di sini**. Yang diukur adalah perilaku di data nyata, kestabilan, validasi antartahun, dan uji luar.

### Perilaku di data nyata (Juli–Desember 2023 dan 2024)

Bobot sampel; "per bulan" = perkiraan nasional, rata-rata atas 12 bulan jendela.

| Kelompok | Bulan-pasien | Kunjungan | Bobot nasional | ≈ per bulan |
|---|---|---|---|---|
| Ditandai model | 714 | 5.766 | 1,53% | 4.345 |
| Dipicu aturan (≥ 2 indikator) | 890 | 8.178 | 2,05% | 5.809 |
| Keduanya | 415 | 4.027 | 0,85% | 2.425 |
| **Hanya model** | **299** | **1.739** | **0,68%** | **1.921** |
| Hanya aturan | 475 | 4.151 | 1,19% | 3.384 |
| **Ditelepon: aturan ATAU model** | **1.189** | **9.917** | **2,72%** | **7.729** |

Cara membaca:

- Model dan aturan sepakat pada 415 bulan-pasien. Model menambah 299 yang tidak dilihat aturan.
- Kasus "hanya aturan" (475): I1+I2 233, I1+I3 118, I2+I3 98, I3+I4 26. Sebanyak 331 di antaranya punya tepat 3 sesi dalam seminggu, dan 351 lebih dari 8 sesi sebulan. Gabungan itu cukup umum secara nasional, jadi model tidak menganggapnya langka. Dengan ATAU, kasus ini tetap ditelepon.
- Kasus "hanya model" punya sesi lebih sedikit: sekitar 5,8 kunjungan per bulan-pasien (1.739 ÷ 299), dibanding sekitar 9,2 pada yang dipicu aturan (8.178 ÷ 890). Model tidak sekadar mencari "banyak sesi".

Pola "hanya model" yang paling sering:

| Pola | Bulan-pasien |
|---|---|
| 5–8 sesi, ≤ 2 seminggu, tanpa Minggu, **6+ bulan, semua tanpa rujukan, semua dari kab/kota lain** | 61 |
| 5–8 sesi, 3 seminggu, tanpa Minggu, 3–5 bulan, semua tanpa rujukan, kab/kota sama | 28 |
| 5–8 sesi, 3 seminggu, tanpa Minggu, 1–2 bulan, semua tanpa rujukan, semua dari kab/kota lain | 27 |
| 5–8 sesi, 3 seminggu, tanpa Minggu, 3–5 bulan, dengan rujukan, semua dari kab/kota lain | 21 |

Alasan pertama pada kasus "hanya model": sesi terbanyak seminggu 116, hanya gabungannya yang jarang 61, dirujuk dari kab/kota lain 41, tanpa rujukan FKTP 39, sesi hari Minggu 30, sesi sebulan 12.

### Kestabilan dan sebaran

| Ukuran | Hasil |
|---|---|
| Irisan (Jaccard) himpunan yang ditandai, seed 7 dibanding 11, 23, 42, 99 | 0,94 · 0,91 · 0,81 · 0,92 |
| Persen ditandai per bulan | 0,9% sampai 3,29% |
| Kelompok RS sejenis (≥ 30 bulan-pasien) tanpa satu pun yang ditandai | 272 dari 423 |
| Pangsa yang ditandai di 10% kelompok RS sejenis teratas | 80,2% |

Kestabilan antar-seed diukur pada Isolation Forest sebelum ditabelkan. Tabel yang disimpan bersifat tetap: data yang sama selalu menghasilkan skor yang sama.

Konsentrasi di sedikit kelompok RS menunjukkan model sebagian besar menemukan **praktik di RS tertentu**, bukan kejadian acak yang tersebar rata.

### Validasi antartahun

Model dilatih ulang hanya dari 2023, lalu dipakai pada 2024 yang belum pernah dilihatnya. Pembanding: model yang dilatih dari 2024 sendiri.

| Ukuran | Hasil |
|---|---|
| Ditandai di 2024 oleh model 2023 | 1,41% |
| Ditandai di 2024 oleh model 2024 | 1,51% |
| Irisan (Jaccard) kedua himpunan yang ditandai | 0,65 |
| Hanya model (tidak terpicu aturan), model 2023 | 0,76% |
| Bobot 2024 di gabungan yang tidak ada di tabel 2023 | 1,34% |

Cara membaca: besarnya hampir sama antartahun (1,41% dibanding 1,51%), tetapi hanya sekitar dua pertiga orangnya sama. Pola yang jarang ikut bergeser dari tahun ke tahun, jadi model perlu dilatih ulang berkala. Model akhir dilatih dari kedua tahun.

### Uji luar (tidak dipakai melatih)

Tabel akhir dipakai pada data sampel kontekstual, yaitu peserta yang dipilih karena penyakit tertentu. Bobotnya mewakili kelompok penyakit itu, bukan nasional.

| Sampel | Tahun | Bulan-pasien | Ditandai model | Dipicu aturan | Hanya model |
|---|---|---|---|---|---|
| Kesehatan Mental (`KM20152023_fkrtl`) | 2015–2023 | 27.062 | 3,59% | 3,34% | 1,51% |
| COVID (`COV20152024_fkrtl`) | 2015–2024 | 8.910 | 5,37% | 2,52% | 2,85% |

Cara membaca: di kelompok yang lebih sakit, model dan aturan sama-sama menandai lebih banyak. Ini peringatan penting: **tidak biasa tidak sama dengan curang**. Pasien yang memang butuh terapi lebih intensif juga tampak tidak biasa. Karena itu model hanya memilih siapa ditelepon, dan jawaban peserta yang menentukan hasil.

### Perbandingan dengan metode lain

Isolation Forest dibandingkan dengan Local Outlier Factor, One-Class SVM, dan kelangkaan gabungan pada data dan fitur yang sama (`data-uji-konfirmasi/referensi-pola/BANDING-METODE.md`, dibuat `ai-service/scripts/compare_anomaly_methods.py`). Ringkasnya:

- Volume yang ditandai sama (sekitar 1,5%), tetapi orangnya berbeda: irisan antarmetode hanya 0,14–0,27, kecuali Local Outlier Factor dan kelangkaan gabungan (0,70).
- Tiap metode melihat hal yang berbeda. Di uji sisipan sintetis, Isolation Forest satu-satunya yang menangkap gabungan rujukan janggal, tetapi hanya menangkap 8,8% sesi hari Minggu yang disisipkan; Local Outlier Factor dan kelangkaan gabungan menangkap 73–75%.
- One-Class SVM tidak cocok untuk fitur berbin kasar: di uji antartahun ambangnya tidak bisa dipasang.
- Isolation Forest dipertahankan karena satu-satunya yang menangkap pola rujukan, yaitu pola yang paling jelas tidak terlihat aturan. Gabungan metode (misalnya ATAU dari tiga metode) menangkap lebih banyak jenis, dengan volume panggilan lebih besar (3,7% dibanding 2,75%).
- Tanpa label, metode terbaik tidak bisa dipilih secara objektif. Hasil panggilan yang menentukannya, dan ukuran yang sama bisa dipakai untuk mesin deteksi lain, termasuk milik BPJS.

### Ukuran ketepatan di lapangan (rencana)

Setelah tersambung ke panggilan:

- presisi model = (ditandai model dan berakhir Tidak sesuai) ÷ (ditandai model dan terjawab);
- dibandingkan dengan presisi aturan pada pasien "hanya aturan", dan dengan sampel acak kecil dari pasien yang tidak ditandai sebagai kelompok kontrol.

## 10. Tingkat RS

Isolation Forest kedua, atas **423 kelompok RS sejenis** yang punya minimal 30 bulan-pasien. "Kelompok RS sejenis" = kab/kota + kepemilikan + jenis + tipe, karena data sampel tidak memuat identitas RS.

| Fitur per kelompok (rata-rata tertimbang) | Median nasional |
|---|---|
| Pangsa bulan-pasien terpicu aturan | 0 |
| Rata-rata sesi sebulan | 3,64 |
| Pangsa dengan sesi hari Minggu | 0 |
| Pangsa kunjungan tanpa rujukan FKTP | 0,016 |
| Pangsa dari kab/kota lain | 0,067 |
| Pangsa diagnosis jarang (kode dengan < 1% kunjungan nasional) | 0 |
| Pangsa kode INA-CBG jarang (< 1% kunjungan nasional) | 0 |

Fitur dinormalkan dengan median dan rentang antarkuartil, lalu dinilai 500 pohon. **21 kelompok (5% teratas) ditandai.** Fitur yang paling menyimpang: diagnosis jarang 7, pangsa terpicu aturan 6, kode INA-CBG jarang 5, tanpa rujukan 3.

Hasil ini untuk verifikator di layar Ringkasan RS, bukan untuk memilih pasien. Yang di-commit hanya jumlah. Identitas dan profil per kelompok tidak disimpan.

## 11. Privasi

| Aturan | Cara dipenuhi |
|---|---|
| Data mentah tidak keluar dari laptop | Hanya `train_anomaly_model.py` yang membacanya. Backend tidak pernah membacanya. |
| Tanpa baris per orang | Tabel hanya memuat gabungan dengan minimal 10 bulan-pasien. Semua jumlah di `anomali-nyata.json` minimal 10. |
| Tanpa pohon | Pohon Isolation Forest dibuang setelah ditabelkan. |
| Tanpa nilai minimum atau maksimum | Batas bin ditetapkan tangan. |
| Tanpa identitas kelompok RS | Tingkat RS hanya melaporkan jumlah per fitur. |
| Penjaga otomatis | `assert_privacy_safe_aggregate` menolak kunci identitas. Uji `test_committed_model_is_a_safe_table` dan `test_committed_real_behaviour_reports_only_counts_of_ten_or_more` memeriksa berkas yang di-commit. |

## 12. Batasan dan risiko

- **Tanpa label.** Angka di bagian 9 adalah perilaku, bukan ketepatan. Model bisa menandai pola yang jarang tetapi sah.
- **Tidak biasa tidak sama dengan curang.** Uji luar menunjukkan kelompok yang lebih sakit lebih sering ditandai.
- **Arti `FKP02` kosong belum pasti.** Kunjungan lanjutan di FKRTL bisa memakai surat kontrol RS, bukan rujukan FKTP baru. Kalau begitu, "6+ bulan tanpa rujukan" bisa wajar. Perlu dipastikan bersama verifikator BPJS sebelum dipakai di lapangan.
- **Pola bergeser antartahun.** Validasi antartahun: hanya sekitar dua pertiga yang ditandai sama. Model perlu dilatih ulang berkala, dan persen per bulan (0,9%–3,29%) perlu dipantau.
- **Hanya setengah tahun per berkas.** Januari–Juni tidak dinilai karena riwayat 6 bulannya tidak lengkap.
- **Pohon dibangun tanpa bobot.** Bentuk "umum" yang dipelajari adalah bentuk di sampel, bukan di populasi. Pangsa dan ambang sudah memakai bobot.
- **Tanpa daftar libur nasional.** `ahad_libur` hanya menghitung hari Minggu.
- **Beban panggilan naik.** Dari ≈ 5.800 menjadi ≈ 7.700 tagihan bulanan per bulan secara nasional.
- **Kelompok RS hanya mendekati satu RS.** Satu kelompok bisa memuat beberapa RS.

## 13. Langkah integrasi (belum dikerjakan)

1. Data demo: tambahkan nomor rujukan FKTP dan kab/kota perujuk per kunjungan di `data-uji-konfirmasi`, termasuk beberapa pasien yang hanya ditandai model. Sementara itu simulasi web memakai `data-uji-konfirmasi/tools/anomali_demo.py`: pasien demo dianggap berujukan normal, ditambah dua pasien khusus simulasi (Sari Wulandari, Agus Setiadi) yang hanya ditandai model.
2. Backend: hitung `fitur_anomali` per bulan-pasien. Simpan skor, `ditandai`, dan alasan. Ubah pemilihan antrean menjadi `dipicu OR ditandai`. Spesifikasi lama "skor tidak pernah membuat panggilan" diganti dengan aturan ini.
3. Aplikasi: tampilkan sumber pemilihan ("Aturan", "Model", atau keduanya) dan alasannya di rincian pasien. Tampilkan hasil tingkat RS di Ringkasan RS.
4. Umpan balik: simpan label hasil panggilan per sumber pemilihan untuk mengukur presisi (bagian 9), lalu evaluasi ulang ambang.

## 14. Menjalankan ulang

```bash
cd ai-service
D="../Folder Data Asli"
# hanya di laptop yang punya Folder Data Asli; sekitar 40 detik
uv run --group data python scripts/train_anomaly_model.py \
  --source "$D/Data Sampel 2015-2023/Data Sampel Reguler Edisi 2024/data/202303_fkrtl.dta" \
  --source "$D/2025 2/Data Sampel Reguler Edisi 2025/data/202403_fkrtl.dta" \
  --uji-luar "$D/Data Sampel 2015-2023/Data Sampel Kontekstual Kesehatan Mental Edisi 2024/data/KM20152023_fkrtl.dta" \
  --uji-luar "$D/2025/Data Sampel Kontekstual COVID Edisi 2025/data/COV20152024_fkrtl.dta"
uv run pytest tests/test_anomali_reference.py
```

Skrip menulis ulang ketiga berkas keluaran. Dengan data dan seed yang sama, hasilnya sama.

## 15. Peta berkas

| Berkas | Isi |
|---|---|
| `data-uji-konfirmasi/tools/anomali.py` | Definisi fitur dan bin, penilai tabel, dan alasan. Hanya pustaka standar, dipakai pelatih dan nanti backend. |
| `ai-service/src/vedika_ai/anomali_reference.py` | Pelatihan Isolation Forest, penabelan, ambang, jendela Juli–Desember, validasi antartahun, uji luar, perilaku di data nyata, tingkat RS |
| `ai-service/src/vedika_ai/pola_reference.py` | Pembaca kohort (ditambah kolom rujukan, diagnosis, INA-CBG) |
| `ai-service/scripts/train_anomaly_model.py` | Skrip baris perintah dan pembuat `EVALUASI-ANOMALI.md` |
| `ai-service/tests/test_anomali_reference.py` | Uji bin, jendela, penilai, alasan, penabelan, ambang, dan keamanan berkas yang di-commit |
| `data-uji-konfirmasi/referensi-pola/model-anomali-v1.json` | Model: tahun, batas bin, pangsa per bin, 77 gabungan dengan skor dan pangsa, ambang |
| `ai-service/data/reference/pola-2024/anomali-nyata.json` | Perilaku di data nyata, validasi antartahun, uji luar, dan hasil tingkat RS (agregat) |
| `data-uji-konfirmasi/referensi-pola/EVALUASI-ANOMALI.md` | Laporan evaluasi yang dibuat skrip |
