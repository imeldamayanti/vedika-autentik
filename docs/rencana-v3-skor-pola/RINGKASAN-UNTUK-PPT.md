# Skor pola Vedika Autentik: ringkasan teknis untuk PPT dan demo

Dua model dibahas di sini. **Bagian 0** menjelaskan model baru `anomali-v1` (tanpa label, ikut memilih siapa ditelepon); penjelasan teknis lengkapnya di `MODEL-ANOMALI.md`. **Bagian 1–15** menjelaskan `pola-v1` (skor urutan) yang masih berjalan di demo. Angka diambil dari berkas yang di-commit (`model-*.json`, `EVALUASI*.md`, `ai-service/data/reference/pola-2024/`). Fakta kolom di bagian 3 dan rincian kasus "hanya aturan" di bagian 0 diukur langsung dari data mentah di laptop dan tidak disimpan di repositori.

**Koreksi 17 November:** semua angka perilaku di data nyata kini hanya memakai **Juli–Desember**. Fitur bulan berturut-turut (dan aturan I3) melihat 6 bulan ke belakang, dan berkas data mulai Januari, jadi Januari–Mei terhitung tanpa riwayat. Angka lama (1,51% terpicu, ≈4.431/bulan, 1,81% pola tidak biasa, ≈5.300/bulan) terkena bias ini dan tidak dipakai lagi.

## Ringkasan satu paragraf

Vedika Autentik menelepon peserta untuk mengonfirmasi jumlah sesi fisioterapi yang ditagih rumah sakit. Pasien ditelepon bila **aturan I1–I4 ATAU model anomali tanpa label** menandainya. Model (Isolation Forest) dilatih dari data sampel reguler BPJS 2023 dan 2024 tanpa diberi tahu mana yang curang, dan mencari tagihan bulanan yang polanya jarang secara nasional. Jawaban peserta tetap menentukan **hasilnya**. Model menambah sekitar **0,68%** tagihan bulanan (≈ **1.900 per bulan** secara nasional) yang tidak terlihat aturan.

---

## 0. Arah baru (17 November): model anomali tanpa label ikut memilih siapa ditelepon

Masukan Richard: mengurutkan antrean kurang berguna bila semua bisa ditelepon sekaligus, dan ML seharusnya menyaring klaim. Kami setuju. Kelemahan `pola-v1` juga jelas: kelas "pelanggaran"-nya dibuat dari manipulasi yang meniru aturan I1–I4, jadi model pada dasarnya mempelajari ulang aturan dan tidak bisa menemukan pola di luar aturan.

**Alur baru:** pasien ditelepon bila **aturan ATAU model anomali** menandainya. Jawaban peserta tetap menentukan hasil. Status: model sudah dilatih dan dievaluasi di data nyata (`anomali-v1`). Web dalam mode simulasi sudah menampilkannya: kolom "Dipilih oleh" (Aturan, Model, Aturan + model) dan bagian "Mengapa dipilih" di kartu bukti, dengan dua pasien demo yang hanya dipilih model. Backend belum, jadi mode API masih memilih dengan aturan saja.

**Model:** Isolation Forest **tanpa label (unsupervised)**, 1.000 pohon, dilatih pada **40.650 bulan-pasien** fisioterapi nyata: Juli–Desember 2023 (18.193) dan Juli–Desember 2024 (22.457), dari data sampel reguler BPJS. Januari–Juni hanya dipakai sebagai riwayat. Model mencari tagihan bulanan yang polanya jarang dibanding seluruh tagihan nasional. Model **tidak** menandai tagihan karena tidak terkena aturan: hampir semua tagihan tidak terkena aturan dan itu normal.

**Data yang dipakai:** berkas kunjungan RS reguler hanya ada untuk 2023 dan 2024. Data sampel kontekstual (Kesehatan Mental 2015–2023, COVID 2015–2024, DM, TB, KIA) memuat peserta yang dipilih karena penyakit tertentu, jadi tidak dipakai melatih; Kesehatan Mental dan COVID dipakai sebagai uji luar.

**Fitur tingkat pasien**, hanya hal yang bisa dikonfirmasi peserta lewat telepon:

- jumlah sesi sebulan, sesi terbanyak dalam satu minggu, sesi hari Minggu, bulan berturut-turut;
- **baru:** pangsa kunjungan tanpa nomor rujukan FKTP, pangsa yang dirujuk dari kab/kota lain.

Kode diagnosis dan INA-CBG tidak dipakai di tingkat pasien karena peserta tidak bisa mengonfirmasinya. Keduanya dipakai di **tingkat RS**. Biaya tidak dipakai: biaya ditagih mengikuti tarif INA-CBG yang tetap, jadi tidak ada variasi untuk dipelajari.

**Privasi:** model disimpan sebagai tabel, bukan pohon. Isinya satu skor per gabungan bin yang muncul pada minimal 10 bulan-pasien (77 gabungan, 99,3% bobot nasional). Gabungan yang lebih jarang dianggap tidak biasa. Batas bin ditetapkan tangan. Penilainya Python murni (`data-uji-konfirmasi/tools/anomali.py`), jadi backend tetap tanpa numpy atau scikit-learn.

**Hasil di data nyata** (Juli–Desember 2023 dan 2024; bobot sampel; "per bulan" = perkiraan nasional; sumber `EVALUASI-ANOMALI.md`):

| Kelompok | Bulan-pasien | Kunjungan | Bobot nasional | ≈ per bulan |
|---|---|---|---|---|
| Ditandai model | 714 | 5.766 | 1,53% | 4.345 |
| Dipicu aturan | 890 | 8.178 | 2,05% | 5.809 |
| Keduanya | 415 | 4.027 | 0,85% | 2.425 |
| **Hanya model (tidak terlihat aturan)** | **299** | **1.739** | **0,68%** | **1.921** |
| Hanya aturan | 475 | 4.151 | 1,19% | 3.384 |
| Ditelepon: aturan ATAU model | 1.189 | 9.917 | 2,72% | 7.729 |

- Pola "hanya model" paling sering (61 bulan-pasien): 5–8 sesi sebulan, 6 bulan atau lebih berturut-turut, **semua kunjungan tanpa rujukan FKTP dan semua dirujuk dari kab/kota lain**. Aturan tidak melihat pola ini sama sekali.
- Kasus "hanya aturan" (475) kebanyakan I1+I2 (233): lebih dari 8 sesi sebulan dengan tepat 3 sesi seminggu. Cukup umum secara nasional, jadi model tidak menandainya. Dengan ATAU, mereka tetap ditelepon.
- **Validasi antartahun:** model yang dilatih hanya dari 2023 menandai 1,41% tagihan 2024 (model 2024 sendiri 1,51%). Besarnya stabil, tetapi hanya sekitar dua pertiga orangnya sama (Jaccard 0,65), jadi model perlu dilatih ulang berkala.
- **Uji luar:** di kelompok Kesehatan Mental dan COVID, model menandai 3,59% dan 5,37% (aturan 3,34% dan 2,52%). Kelompok yang lebih sakit tampak lebih tidak biasa: **tidak biasa tidak sama dengan curang**.
- Stabil antar-seed: Jaccard 0,81–0,94. Terkonsentrasi: 10% kelompok RS sejenis memuat 80,2% yang ditandai; 272 dari 423 kelompok tanpa satu pun. Per bulan 0,9%–3,29% ditandai.

**Perbandingan metode (`BANDING-METODE.md`):** Isolation Forest dibandingkan dengan Local Outlier Factor, One-Class SVM, dan kelangkaan gabungan pada data yang sama. Volume yang ditandai sama (≈ 1,5%), tetapi orangnya berbeda (irisan 0,14–0,27), dan tiap metode menangkap jenis pola yang berbeda. One-Class SVM tidak stabil untuk data ini. Isolation Forest dipilih karena satu-satunya yang menangkap pola rujukan janggal. Tanpa label, yang bisa menentukan metode terbaik hanyalah hasil panggilan, dan itu yang dihasilkan Vedika: **kami bisa menjadi tolok ukur (benchmark) untuk mesin deteksi apa pun, termasuk milik BPJS.**

**Tingkat RS:** Isolation Forest kedua atas 423 kelompok RS sejenis menandai 21 kelompok (5%). Penyimpangan utamanya diagnosis jarang (7), pangsa terpicu aturan (6), kode INA-CBG jarang (5), dan tanpa rujukan (3). Ini untuk verifikator di Ringkasan RS, bukan untuk menelepon.

**Batasan (sampaikan bila ditanya):**

- Tidak ada label fraud, jadi angka di atas adalah perilaku, bukan ketepatan. Ketepatan diukur dari hasil panggilan: berapa yang ditandai model berakhir Tidak sesuai.
- Nomor rujukan FKTP kosong bisa berarti kunjungan kontrol dengan surat kontrol RS. Arti sinyal ini perlu dipastikan bersama verifikator BPJS.
- Volume panggilan naik dari ≈5.800 menjadi ≈7.700 per bulan nasional.

**Kalimat untuk slide:**

- "Aturan menangkap yang sudah kita kenal. Model tanpa label menangkap yang belum: 0,68% tagihan bulanan, sekitar 1.900 per bulan secara nasional, yang tidak terlihat aturan."
- "Model belajar dari 40.650 tagihan bulanan nyata 2023–2024 tanpa diberi tahu mana yang curang, lalu peserta sendiri yang mengonfirmasi lewat telepon."
- "Dilatih di 2023, diuji di 2024: model tetap menandai sekitar 1,4–1,5% tagihan."
- "Kami membandingkan empat metode tanpa label di data nyata BPJS. Volumenya sama, orangnya berbeda. Tanpa label, hanya konfirmasi peserta yang bisa memutuskan mana yang benar, dan Vedika menghasilkan konfirmasi itu."
- "Tidak ada data per orang yang keluar dari laptop: model disimpan sebagai tabel gabungan yang masing-masing muncul minimal 10 kali."

Bagian 1–15 di bawah menjelaskan `pola-v1` (skor urutan) yang masih berjalan di demo.

---

## 1. Arsitektur dan peran AI

```
klaim_sesi ──► aturan I1–I4 (aturan.py) ──► siapa ditelepon (≥ 2 indikator aktif)
                      │
                      ▼
            [1] skor pola (pola-v1) ──► urutan antrean + "Alasan prioritas"
                      │
                      ▼
pesan WA ──► [2] agen suara Gemini Live ──► transkrip
                      │
                      ▼
            [3] pembaca jawaban (LLM) ──► jawaban terstruktur (JSON)
                      │
                      ▼
            aturan.py ──► label (Sesuai / Tidak sesuai / Tidak yakin / ...) ──► keputusan verifikator
```

| # | Komponen | Model | Tugas | Jalan di | Kapan |
|---|---|---|---|---|---|
| 1 | Skor pola | Regresi logistik, 29 koefisien + intersep | Urutan antrean dan alasan prioritas | Dilatih offline (scikit-learn); dievaluasi Python murni di backend | Sekali saat seed (`terapkan_v3`), hasil disimpan di DB |
| 2 | Agen suara | `gemini-3.8-live`, suara "Kore", temperature 0,4 | Percakapan telepon Bahasa Indonesia dengan naskah tetap | Chrome di laptop stasiun + HP Android | Langsung, tiap panggilan |
| 3 | Pembaca jawaban | `gemini-3.5-flash-lite`, temperature 0, skema JSON tetap | Mengubah transkrip menjadi isian (hadir, jumlah sesi min/maks, keyakinan, tanda bahaya, kutipan) | `ai-service` `POST /v1/baca` | Sekali, setelah panggilan |

Yang **bukan** model: label dan status RS, dan pembanding RS sejenis (statistik nasional, bukan prediksi). Label dihitung `aturan.py` dari isian pembaca:

- **Tidak terhubung**: tidak diangkat 2 kali. **Menolak**: penerima tidak bersedia menjawab.
- **Tidak sesuai** bila salah satu: penerima menyatakan tidak pernah menjalani layanan, ada tanda bahaya (mis. tanda tangan tanpa layanan), atau ditagih − jumlah maksimal menurut penerima > 2 sesi.
- **Tidak yakin**: jumlah tidak diingat atau keyakinan rendah. Juga dipakai bila pembaca jawaban gagal (gagal aman).
- Selain itu **Sesuai**.
- RS berstatus **Perlu klarifikasi RS** bila ≥ 3 Tidak sesuai dan ≥ 10% dari yang terjawab (Sesuai + Tidak sesuai).

---

## 2. Data sumber dan kohort

| | |
|---|---|
| Berkas | `202403_fkrtl.dta`, Data Sampel Reguler Edisi 2025 (kunjungan FKRTL tahun 2024) |
| Kolom yang dibaca | `PSTV01` (nomor peserta, hanya untuk mengelompokkan), `PSTV15` (bobot sampel), `FKL03` (tanggal), `FKL06`–`FKL09` (kab/kota, kepemilikan, jenis, tipe RS), `FKL10` (tingkat layanan), `FKL11` (poli), `FKL18A` (diagnosis), `FKL30` (prosedur) |
| Filter kohort | Rawat jalan (`FKL10 = 1`), poli FIS atau IRM (`FKL11`, dari value label), dan diagnosis/prosedur mengandung pola fisioterapi (physical therap, physiotherap, fisioterap, musculoskeletal exercise, heat therapy, diathermy, electrotherap, manual therap) |
| Hasil | **149.997 kunjungan**, **13.172 peserta**, **41.905 bulan-pasien**, bobot nasional **3.521.010** bulan-pasien |
| Prevalensi indikator (berbobot, seluruh 12 bulan 2024) | I1 1,88% · I2 3,14% · I3 11,49% · I4 0,45% (Minggu saja). Terlalu rendah untuk I3 karena Januari–Mei tanpa riwayat. Di Juli–Desember 2024, terpicu (≥ 2) **1,88%**. |
| Kelompok RS sejenis | 951 kelompok (kab/kota + kepemilikan + jenis + tipe); 426 dengan ≥ 30 bulan-pasien |

Data sampel tidak memuat identitas RS, jadi "kelompok RS sejenis" hanya mendekati satu RS. Tidak ada daftar libur 2024, jadi I4 di data nyata hanya menghitung hari Minggu. Bulan sebelum Januari 2024 tidak ada di berkas, jadi I3 di Januari–Mei tidak bisa menyala. Karena itu histogram pelatihan dan semua angka perilaku memakai Juli–Desember saja.

---

## 3. Fitur

Satu baris = satu peserta di satu bulan (dan satu RS di data demo). Definisi tunggal di `data-uji-konfirmasi/tools/pola.py`, dipakai builder, trainer, backend, dan uji.

| Fitur | Definisi | Bin | Kaitan aturan |
|---|---|---|---|
| `sesi` | Jumlah sesi dalam bulan itu | 1 … 12, 13+ | I1: > 8 |
| `maks_minggu` | Sesi terbanyak dalam satu minggu Senin–Minggu | 1 … 5, 6+ | I2: ≥ 3 |
| `ahad_libur` | Sesi pada hari Minggu atau libur nasional | 0, 1, 2+ | I4: > 0 |
| `episode` | Bulan berturut-turut dengan ≥ 1 sesi, sampai bulan ini | 1 … 6, 7+ | I3: ≥ 6 |

Fitur dibuat **one-hot** per bin: 13 + 6 + 3 + 7 = **29 kolom**. Bin yang belum pernah terlihat diberi koefisien 0. Uji `uji_pola.py` memastikan fitur sama persis dengan `aturan.py` di 300 bulan-pasien demo.

Fitur yang diperiksa tetapi **tidak dipakai** karena tidak informatif di data asli (diukur di 149.997 kunjungan kohort): biaya ditagih (`FKL47`) sama dengan biaya diverifikasi (`FKL48`) pada 99,999% baris; tidak ada satu pun peserta dengan dua kunjungan fisioterapi di tanggal yang sama; 20,1% kunjungan tanpa nomor rujukan FKTP (`FKP02` kosong), terlalu umum untuk menjadi sinyal.

---

## 4. Privasi: dari data mentah ke model

```
Folder Data Asli (laptop, tidak di-commit)
   │  prepare_pattern_reference.py
   ▼
ai-service/data/reference/pola-2024/     agregat, tiap sel ≥ 10 baris
   │  train_pattern_model.py (hanya membaca berkas yang di-commit)
   ▼
data-uji-konfirmasi/referensi-pola/      koefisien + referensi nasional
   │  backend/app/pola_v3.py (Python murni)
   ▼
indikator_bulanan.skor_pola / logit_pola / alasan_pola / pola_tinggi
```

- **Tidak ada data per orang yang keluar dari laptop.** Nomor peserta hanya dipakai sesaat untuk mengelompokkan kunjungan.
- **Histogram bertingkat** (Juli–Desember 2024, 22.457 bulan-pasien): sel di bawah 10 baris digabung ke rentang lebih kasar. Batas rentang tepat di ambang aturan (sesi 8|9, seminggu 2|3, Minggu 0|1, episode 5|6), jadi indikator tetap pasti di tiap sel.
  - Tingkat 0: bin halus (119 sel).
  - Tingkat 1: sesi 1-2/3-4/5-6/7-8/9-12/13+, seminggu 1/2/3/4+, Minggu 0/1/2+, episode 1/2-3/4-5/6/7+ (4 sel).
  - Tingkat 2: sesi 1-4/5-8/9+, seminggu 1-2/3+, Minggu 0/1+, episode 1-5/6+ (9 sel).
  - Sisa yang tetap < 10 baris disembunyikan: **30 bulan-pasien, 0,10% bobot**.
- **Kombinasi indikator** dengan < 10 baris hanya ditulis batas atasnya (`prevalensi_maks`, "kurang dari 0,03%").
- **Pembanding per tipe RS**: tipe dengan < 100 bulan-pasien tidak ditulis; tipe yang > 50% bulan-pasiennya dari satu kelompok RS tidak ditulis (aturan dominansi, 2 tipe); persentil antar kelompok hanya bila ≥ 20 kelompok; tidak ada nilai maksimum atau minimum.
- Uji otomatis (`ai-service/tests/test_pola_reference.py`) memeriksa semua berkas yang di-commit: tidak ada kolom identitas, semua hitungan ≥ 10, checksum manifest cocok.

---

## 5. Pelatihan (weak supervision)

Data BPJS tidak punya label fraud. Model dilatih membedakan dua kelas buatan:

| Kelas | Ukuran | Asal |
|---|---|---|
| Normal (0) | 50.000 | Diambil dari histogram nasional, peluang ∝ bobot `PSTV15`. Sel kasar dipecah ke bin halus memakai marginal nasional (fitur dianggap saling bebas di dalam sel). |
| Pelanggaran (1) | 50.000 | Sampel normal yang diberi 1–2 manipulasi acak, meniru penyisipan di data uji dan aturan I1–I4 |

Manipulasi:

| Kode | Manipulasi | Rumus |
|---|---|---|
| V1 | Tambah sesi | `sesi += acak(2..6)`; `maks_minggu = max(maks_minggu, ⌈sesi/4⌉ + acak(0..1))` |
| V2 | Sesi hari libur | `ahad_libur += acak(1..2)`; `sesi += 1` |
| V3 | Pemadatan | `maks_minggu = max(maks_minggu, acak(3..5))`; `sesi = max(sesi, maks_minggu)` |
| V4 | Perpanjangan episode (hanya bersama manipulasi lain) | `episode = min(7, episode + acak(3..6))` |

- Model: `LogisticRegression(C=1.0, max_iter=1000, random_state=2026)` pada 29 kolom one-hot. Deterministik (benih 2026).
- **Ambang "pola tidak biasa"** = persentil berbobot ke-98,5 skor atas histogram nasional = **0,898**, supaya proporsinya setara dengan tingkat pemicu aturan (≈ 1,5%).
- Cek kecocokan fitur sebelum melatih: bila porsi bin teratas di RS demo jujur > 3× nasional, fitur dibuang. Hasil: **tidak ada fitur dibuang**.

---

## 6. Skor, logit, dan alasan

```
z    = intersep + Σ koefisien(bin aktif tiap fitur)        # logit
skor = 1 / (1 + e^(−z)), dibulatkan 3 desimal
pola tidak biasa ⇔ skor ≥ 0,898
```

Contoh dengan koefisien sebenarnya:

| | sesi | maks/minggu | Minggu/libur | episode | z | skor |
|---|---|---|---|---|---|---|
| Andi Pratama (S1) | 11 → +0,902 | 4 → +4,832 | 2+ → +3,999 | 3 → −0,037 | 4,054 + 9,696 = **13,75** | **1,00** |
| Yuni Setiawan (P0003) | 9 → +0,167 | 3 → +0,376 | 0 → −3,827 | 3 → −0,037 | 4,054 − 3,321 = **0,73** | **0,675** |

**Alasan prioritas** = dua fitur dengan sumbangan positif terbesar dibanding rata-rata nasional:

```
sumbangan(f) = koef(bin f pasien) − Σ_b p_nasional(b) · koef(b)
```

Karena modelnya linear, sumbangan ini eksak (tidak perlu SHAP). Persentil nasional dihitung dari marginal berbobot. Contoh teks untuk S1: "4 sesi dalam satu minggu, lebih padat dari 99,9% tagihan bulanan fisioterapi nasional." dan "2 sesi pada hari Minggu atau libur. Hanya 0,4% tagihan bulanan nasional memuat sesi seperti ini."

**Urutan antrean**: Dahulukan → **logit** tertinggi → nomor. Logit dipakai karena skor di atas 0,999 tampil sama (1,00), padahal logitnya masih berbeda (di demo 7,8 sampai 14,7).

### Koefisien `pola-v1` (intersep 4,0541)

| Fitur | Koefisien per bin |
|---|---|
| `sesi` | 1: −5,84 · 2: −1,21 · 3: 0,77 · 4: 0,93 · 5: 0,80 · 6: 1,28 · 7: 1,91 · 8: 2,14 · 9: 0,17 · 10: 0,61 · 11: 0,90 · 12: 0,75 · 13+: 0,31 |
| `maks_minggu` | 1: −4,03 · 2: −3,62 · 3: 0,38 · 4: 4,83 · 5: 5,80 · 6+: 0,15 |
| `ahad_libur` | 0: −3,83 · 1: 3,35 · 2+: 4,00 |
| `episode` | 1: 0,29 · 2: −0,16 · 3: −0,04 · 4: 0,48 · 5: 0,77 · 6: 1,27 · 7+: 0,91 |

Cara membaca: kepadatan mingguan (≥ 4 sesi seminggu) dan sesi hari Minggu adalah sinyal terkuat. Koefisien `sesi` tidak naik terus: 9–13 sesi lebih rendah dari 7–8 sesi. Ini belum diteliti; dugaan kami, sesi yang banyak hampir selalu datang bersama minggu yang padat, sehingga model memberi bobotnya ke `maks_minggu`. Koefisien satu fitur karena itu jangan dibaca terpisah dari fitur lain.

---

## 7. Evaluasi (per tingkat bukti, tidak digabung)

**Tier A: data asli BPJS, Juli–Desember 2024 (perilaku, bukan akurasi; 22.457 bulan-pasien)**

| Ukuran | Nilai |
|---|---|
| Pola tidak biasa | **1,82%** berbobot |
| Terpicu aturan | 1,88% (446 bulan-pasien) |
| Keduanya | 168 bulan-pasien |
| Terpicu tapi skor di bawah ambang | 278 |
| Pola tidak biasa tanpa pemicu aturan | 270 (200 hanya I2 = minggu padat, 70 hanya I4 = sesi hari Minggu) |
| Stabilitas per bulan | 1,6% sampai 2,3% |
| Konsentrasi | 10% kelompok RS memuat **66%** pola tidak biasa; 143 dari 216 kelompok (≥ 30 bulan-pasien) tidak punya satu pun |
| Terpicu yang tampil 1,00 | 11 dari 446 |

Rata-rata skor per kombinasi aturan (histogram nasional): tanpa indikator 0,065 · I1 0,042 · I3 0,144 · I1+I3 0,095 · I4 0,833 · I1+I2 0,744 · I2 0,869 · I1+I2+I3 0,882 · I3+I4 0,909 · I2+I3 0,946.

**Tier B: sintetis (hanya uji kewajaran metode)**

| Ukuran | Nilai |
|---|---|
| AUC normal vs pelanggaran buatan (20% data tahan) | 0,978 |
| Data demo (300 bulan-pasien, 25 digelembungkan): AUC skor pola | 0,997 |
| AUC jumlah indikator (pembanding) | 0,996 |
| Pemicu aturan: presisi / recall | 0,833 / 1,000 |
| Presisi@30 skor pola | 0,833 |
| Skor ≥ ambang | 22, di antaranya 21 digelembungkan |

AUC sintetis tinggi karena kelas pelanggaran dibuat dari aturan yang sama; itu bukan akurasi deteksi. **Akurasi nyata belum bisa diukur** karena belum ada label nyata.

---

## 8. Contoh data tanpa label

Satu baris per pasien per bulan (data demo, struktur sama dengan klaim BPJS):

| peserta | bulan | sesi | maks/minggu | Minggu/libur | episode | **fraud?** |
|---|---|---|---|---|---|---|
| P0003 | 2026-08 | 9 | 3 | 0 | 3 | **?** |
| P0012 | 2026-08 | 9 | 2 | 0 | 6 | **?** |
| P0001 | 2026-08 | 5 | 2 | 0 | 3 | **?** |

Model hanya memberi skor: P0003 = 0,675 · P0012 = 0,124 · P0001 = 0,067.

Data asli yang dipakai melatih (agregat, tiap baris = kelompok tagihan berpola sama):

| tingkat | sesi | maks/minggu | Minggu/libur | episode | jumlah bulan-pasien | bobot nasional |
|---|---|---|---|---|---|---|
| 0 | 1 | 1 | 0 | 1 | 2.126 | 174.534 |
| 0 | 11 | 3 | 0 | 2 | 14 | 767 |
| 0 | 12 | 3 | 0 | 7+ | 19 | 1.170 |
| 2 | 1–4 | 1–2 | 1+ | 1–5 | 47 | 4.111 |

**41.905 bulan-pasien, tidak satu pun berlabel fraud.**

---

## 9. Dari mana labelnya: umpan balik panggilan

| peserta | sesi | maks/minggu | ditagih | menurut peserta | **label** |
|---|---|---|---|---|---|
| P0003 | 9 | 3 | 9 | 3 | **1 (Tidak sesuai)** |
| P0012 | 9 | 2 | 9 | 8–10 | **0 (Sesuai)** |

1. `backend/scripts/ekspor_label_pola.py` mengekspor panggilan berlabel Sesuai/Tidak sesuai: hanya fitur yang sudah dibin + label, tanpa nama, nomor, atau ID.
2. `train_pattern_model.py --label-panggilan <berkas>` menambahkan label itu sebagai sampel berlabel dengan **bobot 5** di atas sampel sintetis, dan menulis `model-pola-v2.json`.
3. `pola-v1` tetap bawaan; backend memakai versi di `pengaturan.versi_pola`. Setelah ganti versi, jalankan `scripts.terapkan_v3` supaya skor dihitung ulang.

Dengan ratusan panggilan nyata di pilot, model bergeser dari *weakly supervised* ke *supervised*, dan akurasinya bisa diukur.

---

## 10. Di aplikasi

**Database** (`indikator_bulanan`): `skor_pola real`, `logit_pola real`, `alasan_pola jsonb`, `pola_tinggi boolean`; versi di `pengaturan.versi_pola`. Diisi untuk semua 300 pasien aktif, tidak hanya yang terpicu.

**API (Kontrak A)**:
- `GET /antrean`: tiap baris `skor_pola`, `pola_tinggi`. Urutan antre = Dahulukan → logit → nomor; agen (`POST /agen/ambil`) memakai urutan yang sama.
- `GET /panggilan/{id}`: `pola { skor, tinggi, ambang, alasan[2], kombinasi { kunci, teks }, versi }`.
- `GET /ringkasan-rs`: per RS `pembanding { tipe, persen_terpicu_nasional, sesi_rata_nasional, terpicu_p95_kelompok, posisi }` (posisi: `di_atas_p95`, `di_atas_p90`, `wajar`, `tidak_ada_pembanding`), `pola_tinggi_tidak_terpicu`; di tingkat atas `kinerja_pola` (rata-rata skor pada Sesuai vs Tidak sesuai).

**Pembanding RS di demo** (terhadap tipe RS yang sama secara nasional):

| RS demo | Terpicu | Tipe pembanding | Rata-rata tipe | Batas 95% kelompok | Posisi |
|---|---|---|---|---|---|
| RS Melati Sehat | 39,7% | RS Swasta Setara Type C | 1,48% | 8,2% | **Di atas 95%** |
| RSU Bakti Mulia | 1,5% | RS Kelas B | 1,12% | 14,8% | Wajar |
| RS Cempaka Asri | 1,7% | RS Swasta Setara Type C | 1,48% | 8,2% | Wajar |
| RSU Nusa Sejahtera | 0,0% | RS Kelas C | 1,06% | 6,7% | Wajar |
| RS Kenanga Medika | 1,8% | RS Swasta Setara Type B | 0,94% | 3,3% | Wajar |

**Yang tidak pernah diubah skor**: siapa ditelepon (`dipicu`), label, saran, status RS. Istilah di UI/API: "Skor pola" dan "Pola tidak biasa", tanpa kata fraud/curang.

---

## 11. Cara membangun ulang

```bash
cd ai-service
# 1. agregat dari data mentah (hanya di laptop yang punya Folder Data Asli)
uv run --group data python scripts/prepare_pattern_reference.py \
  --source "../Folder Data Asli/2025 2/Data Sampel Reguler Edisi 2025/data/202403_fkrtl.dta" \
  --output data/reference/pola-2024
# 2. model, referensi, skor demo, EVALUASI.md (hanya membaca berkas yang di-commit)
uv run --group data python scripts/train_pattern_model.py
# 3. perilaku di data nyata (agregat ke perilaku-nyata.json), lalu ulangi langkah 2
uv run --group data python scripts/check_pattern_real_data.py \
  --source "../Folder Data Asli/2025 2/Data Sampel Reguler Edisi 2025/data/202403_fkrtl.dta"
# 4. isi skor ke database
cd ../backend && .venv/bin/python -m scripts.terapkan_v3
```

Uji: `python3 data-uji-konfirmasi/tools/uji_pola.py` · `cd ai-service && uv run pytest` (212) · `cd backend && .venv/bin/pytest` (329) · `node tests/alur-v3.test.js`.

---

## 12. Batasan (sampaikan bila ditanya juri)

- **Bukan peluang fraud.** Skor berarti "mirip pola manipulasi yang dikenal, dibanding pola nasional 2024".
- **Kelas pelanggaran buatan** berasal dari aturan yang sama dengan pemicu; di data demo skor dan aturan hampir sama. Di data nyata keduanya berbeda cukup jauh (lihat bagian 7).
- **Kelas normal bisa memuat fraud** yang tidak terdeteksi, karena diambil apa adanya.
- **Hanya 4 fitur.** Biaya, diagnosis, prosedur, dan riwayat RS belum dipakai.
- **I4 di data nyata hanya hari Minggu**; I3 terhitung rendah di awal 2024.
- **Akurasi belum terukur**; perlu label panggilan nyata dari pilot.

**Sudah dikerjakan (bagian 0):** model anomali tanpa label tingkat pasien dan tingkat RS (Isolation Forest), dengan fitur rujukan, diagnosis, dan INA-CBG dari data asli.

---

## 13. Kalimat siap pakai untuk slide

- "Data klaim BPJS tidak punya label fraud. Vedika membuat labelnya sendiri: setiap panggilan konfirmasi menghasilkan satu data berlabel untuk melatih ulang model."
- "Aturan menentukan siapa ditelepon, skor pola menentukan siapa duluan, jawaban peserta menentukan hasilnya."
- "Model yang bisa dijelaskan: setiap prioritas disertai alasan yang bisa diperiksa verifikator."
- "Pola tidak biasa mengumpul: 10% kelompok rumah sakit memuat 80% tagihan yang ditandai model anomali."

**Jangan dipakai:** "model mendeteksi X kasus fraud", "akurasi model sekian persen" (belum ada label nyata untuk mengukurnya).

---

## 14. Catatan untuk skenario demo

- Urutan antrean dari skor pola: yang pertama ditelepon otomatis **S6 (Slamet Riyadi)**, lalu P0037, lalu **S1 (Andi Pratama)**. Untuk demo S1, tekan **Dahulukan** di baris Andi Pratama.
- Situs langsung membuka **Antrean konfirmasi** (tidak ada layar masuk dan Beranda).
- **Per 16 November malam, `vedika-autentik.vercel.app` masih menampilkan versi lama (v2).** Versi terbaru dari `main` sudah ter-build tetapi belum dipromosikan ke production. Imelda perlu *Promote to Production* di Vercel sebelum rekam video. Backend (`vedika-autentik-backend.vercel.app`) sudah versi terbaru.
- Panggilan telepon nyata hanya jalan dari laptop stasiun (pembaca jawaban berjalan lokal di `ai-service`). Situs saja tidak bisa menyelesaikan panggilan.
- Data produksi berisi hasil uji HP Richard (S1–S8 selesai). "Mulai ulang demo" menghapusnya; putuskan dulu sebelum rekam.

---

## 15. Peta berkas

| Berkas | Isi |
|---|---|
| `data-uji-konfirmasi/tools/pola.py` | Definisi fitur, bin, skor, logit, alasan (satu sumber) |
| `ai-service/src/vedika_ai/pola_reference.py`, `scripts/prepare_pattern_reference.py` | Builder agregat dari data mentah |
| `ai-service/data/reference/pola-2024/` | Histogram bertingkat, marginal, kombinasi, pembanding tipe, perilaku nyata, manifest |
| `ai-service/scripts/train_pattern_model.py` | Pelatih, evaluasi, `EVALUASI.md`, opsi `--label-panggilan` |
| `ai-service/scripts/check_pattern_real_data.py` | Perilaku model di semua bulan-pasien nyata |
| `data-uji-konfirmasi/referensi-pola/` | `model-pola-v1.json`, `referensi.json`, `skor_demo.json`, `EVALUASI.md` |
| `backend/app/pola_v3.py` | Pemuat model dan referensi, teks kombinasi, pembanding RS |
| `backend/scripts/seed_v3.py`, `ekspor_label_pola.py` | Mengisi skor ke DB, mengekspor label panggilan |
| `docs/rencana-v3-skor-pola/SKOR-POLA.md` | Penjelasan untuk tim |
| `docs/api-contract-v3.md` | Kontrak API termasuk field skor pola |
