# Model anomali `anomali-v2`: penjelasan teknis

Model **tanpa label** yang ikut memilih tagihan fisioterapi mana yang dikonfirmasi lewat telepon. Dilatih 17 November 2026 dari data sampel reguler BPJS 2023 dan 2024. Angka model dan evaluasi berasal dari berkas yang dibuat skrip:

- `data-uji-konfirmasi/referensi-pola/model-anomali-v2.json` (model)
- `data-uji-konfirmasi/referensi-pola/EVALUASI-ANOMALI.md` dan `ai-service/data/reference/anomali/anomali-nyata.json` (perilaku di data nyata)
- `data-uji-konfirmasi/referensi-pola/BANDING-METODE.md` dan `ai-service/data/reference/anomali/banding-metode.json` (perbandingan dengan v1)

Pengecualian, diukur sekali dari data mentah di laptop dan tidak disimpan: tabel "Diperiksa, tidak memberi sinyal" di bagian 3 dan angka "tanpa φ" di bagian 11.

Status: model sudah dilatih, diuji, dan dievaluasi di data nyata, dan tersambung ke backend dan web (mode API dan simulasi): antrean berisi pasien yang dipilih aturan ATAU model, kolom "Dipilih oleh", bagian "Mengapa dipilih", baris corong dan kartu "sumber pemilihan dan hasil panggilan" di Ringkasan RS. Data uji punya dua pasien yang hanya dipilih model (M1, M2).

`anomali-v1` (Isolation Forest) digantikan. Kode dan laporannya ada di commit `d646541`; tabelnya (`model-anomali-v1.json`) disimpan sebagai pembanding.

---

## 1. Peran model dalam alur

```
Klaim fisioterapi bulan ini (per pasien per bulan)
   │
   ├── Aturan I1–I4: ≥ 2 indikator aktif ──┐
   │                                       ├── ATAU ──► ditelepon agen AI ──► jawaban peserta ──► label (aturan.py)
   └── Model: pola jarang di antara        ┘
       pasien seusia

Urutan antrean: Dahulukan, lalu pola paling jarang (langka dulu, lalu skor tertinggi), lalu id.

Per RS: jumlah pasien dipilih dibanding harapan menurut umur pasiennya (corong) ──► Ringkasan RS
```

Model tidak memberi label, tidak memberi saran tindakan, dan tidak mengubah status RS. Hasil tetap dari jawaban peserta.

## 2. Mengapa v1 diganti

Isolation Forest dilatih pada nomor bin berurutan (0, 1, 2). Belahan acaknya mudah mengisolasi nilai di ujung, tetapi sulit mengisolasi nilai di **tengah**. Di tabel v1, setiap pola tersimpan yang memuat nilai tengah (tepat 1 sesi hari Minggu, *sebagian* kunjungan tanpa rujukan, *sebagian* dari kab/kota lain) berskor di bawah ambang (17 dari 17 pola), walaupun termasuk pola paling jarang (0,017–0,097% bobot). Pohon v1 juga dibangun tanpa bobot sampel.

Data ini kecil dan berbentuk tabel: enam fitur berbin membentuk paling banyak 972 pola, dan 77 pola sudah menutup 99,27% bobot nasional. Untuk data seperti ini, cara langsung adalah menghitung seberapa sering tiap pola muncul (berbobot), bukan memperkirakannya lewat pohon acak.

## 3. Data

| | |
|---|---|
| Sumber latih | `202303_fkrtl.dta` (2023) dan `202403_fkrtl.dta` (2024), data sampel reguler BPJS. Umur dari `2015202301_kepesertaan.dta` dan `2015202401_kepesertaan.dta`. Diagnosis sekunder (`202305_` / `202405_diagnosissekunder.dta`) hanya dipakai untuk memilih kelompok pembanding (bagian 5). |
| Kohort | rawat jalan (`FKL10 = 1`), poli FIS/IRM (`FKL11`), teks fisioterapi di `FKL18A`/`FKL30` |
| Jendela | **Juli–Desember** tiap tahun; Januari–Juni hanya riwayat untuk fitur bulan berturut-turut |
| Ukuran | **40.650 bulan-pasien**: 18.193 (2023) + 22.457 (2024) |
| Bobot | `PSTV15` |

Berkas tiap tahun tidak digabung per peserta. Data sampel kontekstual (Kesehatan Mental, COVID) hanya dipakai sebagai uji luar.

**Diperiksa, tidak memberi sinyal di data ini** (2024, 149.997 kunjungan fisioterapi):

| Pemeriksaan | Hasil |
|---|---|
| Nomor rujukan `FKP02` dicocokkan ke kunjungan FKTP | 80% kunjungan punya nomor; 100% ditemukan, peserta sama, umur rujukan ≤ 90 hari, tujuan rujukan = kab/kota RS |
| Tahun meninggal (`PSTV18`) | 0 kunjungan setelah tahun meninggal |
| Diagnosis primer `FKL17A` | 94% bobot Z50 (perawatan rehabilitasi) atau Z09 (kontrol): tidak menggambarkan kondisi |

## 4. Fitur (sama dengan v1)

Hanya hal yang bisa dikonfirmasi peserta lewat telepon. Batas bin ditetapkan tangan (ambang aturan dan angka bulat).

| Fitur | Definisi | Bin |
|---|---|---|
| `sesi` | kunjungan dalam bulan itu | 1–4 · 5–8 · 9–12 · 13+ |
| `maks_minggu` | kunjungan terbanyak dalam satu minggu Senin–Minggu | ≤ 2 · 3 · ≥ 4 |
| `ahad_libur` | kunjungan hari Minggu (tanpa daftar libur nasional) | 0 · 1 · 2+ |
| `episode` | bulan berturut-turut dengan kunjungan | 1–2 · 3–5 · 6+ |
| `tanpa_rujukan` | pangsa kunjungan tanpa nomor rujukan FKTP | 0 · sebagian · semua |
| `lintas_wilayah` | pangsa kunjungan dari perujuk kab/kota lain | 0 · sebagian · semua |

## 5. Memilih kelompok pembanding

"Jarang" dinilai di antara pasien yang sebanding. Tiga pilihan diuji dengan data **tahun lain**: model dilatih satu tahun, lalu dihitung rata-rata log-peluang berbobot pada tahun lainnya (makin tinggi, makin baik model memperkirakan pola yang belum dilihatnya).

| Kelompok | Latih 2023, uji 2024 | Latih 2024, uji 2023 |
|---|---|---|
| Nasional (tanpa kelompok) | −2,5997 | −2,8026 |
| Kelompok umur (4 kelompok), alfa terbaik | −2,5851 | −2,789 |
| Diagnosis sekunder (12 kelompok), alfa terbaik | −2,5976 | −2,8014 |

- Umur lebih baik dari nasional di kedua arah (+0,0146 dan +0,0136).
- Diagnosis sekunder hampir tidak berbeda dari nasional (+0,0021 dan +0,0012), dan selisih itu hanya muncul pada penghalusan terkuat, saat model hampir sama dengan nasional. Sebaran "lebih dari 8 sesi" antar-diagnosis di satu tahun tidak memperkirakan tahun berikutnya.

Model memakai **kelompok umur**: di bawah 18, 18–39, 40–59, 60 ke atas.

## 6. Model

Untuk satu bulan-pasien dengan pola `x` di kelompok umur `g` (berisi `n` bulan-pasien):

```
s = pangsa berbobot pola x di kelompok g
    (pola dengan < 10 bulan-pasien di kelompok g: sisa pangsa kelompok, dibagi menurut pangsa nasional)
p = (n · s + α · pangsa nasional x) / (n + α)
skor = −ln p
```

| Parameter | Nilai | Asal |
|---|---|---|
| α (penghalusan ke nasional) | 1.000 | log-peluang tertinggi di kedua arah dari pilihan 10, 50, 200, 1.000 |
| Ambang skor | 7,4504 (p < 0,058%) | sekitar 1,5% bobot nasional ditandai, setara aturan |
| Pola nasional di tabel | 77 (99,27% bobot) | sel dengan minimal 10 bulan-pasien |
| Pola di luar tabel | 0,73% bobot | selalu ditandai |

Yang ditandai (1,53% bobot) terdiri dari pola di luar tabel (0,73%) ditambah pola di tabel dengan skor ≥ ambang. Unsur umur kecil: dengan α = 1.000, peluang kelompok ditarik ke nasional dengan bobot α / (n + α), yaitu 18,5% untuk kelompok terkecil (18–39 tahun, 4.398 bulan-pasien) dan 5,5% untuk yang terbesar (40–59 tahun, 17.192). Di perbandingan, himpunan yang ditandai v2 dan kelangkaan nasional tanpa kelompok beririsan 0,793 (Jaccard).

Penilai: `data-uji-konfirmasi/tools/anomali.py`, hanya pustaka standar. Pelatih: `ai-service/src/vedika_ai/ml/anomaly_model.py`.

## 7. Alasan untuk verifikator

Dari tabel yang sama, tanpa model tambahan (`anomali.reasons`):

1. Sampai dua bin yang dimiliki kurang dari 10% tagihan bulanan pasien seusia, paling jarang dulu.
2. Satu kalimat pola: bagian yang bukan bin terbanyak, dan seberapa sering pola itu muncul di kelompok umur.

Contoh (pasien demo M2, 41 tahun): "2 sesi atau lebih hari Minggu: hanya 0,2% tagihan bulanan pasien 40–59 tahun." dan "Gabungan 5–8 sesi sebulan dan 2 sesi atau lebih hari Minggu muncul pada kurang dari 0,1% tagihan bulanan fisioterapi pasien 40–59 tahun di data sampel BPJS 2023–2024." Teks tidak pernah memakai kata "fraud" atau "curang".

## 8. Perilaku di data nyata (Juli–Desember 2023 dan 2024)

| Kelompok | Bulan-pasien | Bobot nasional | ≈ per bulan |
|---|---|---|---|
| Ditandai model | 772 | 1,53% | 4.331 |
| Dipicu aturan (≥ 2 indikator) | 890 | 2,05% | 5.809 |
| Keduanya | 272 | 0,47% | 1.345 |
| **Hanya model** | **500** | **1,05%** | **2.985** |
| Hanya aturan | 618 | 1,57% | 4.463 |
| **Ditelepon: aturan ATAU model** | **1.390** | **3,1%** | **8.794** |

- Dibanding v1 (0,68% hanya model, 2,72% ditelepon), v2 menambah lebih banyak tagihan di luar aturan dan lebih sedikit tumpang tindih dengan aturan.
- Persen ditandai per bulan (tanpa bobot): 1,35% sampai 2,72%.
- Per kelompok umur: di bawah 18 dan 18–39 masing-masing 1,88%, 40–59 1,59%, 60 ke atas 1,26%.
- Alasan pertama pada kasus hanya model: sesi terbanyak seminggu 118, tanpa rujukan FKTP 112, dari kab/kota lain 104, sesi hari Minggu 102, sesi sebulan 64.

## 9. Validasi antartahun dan uji luar

Model dilatih hanya dari 2023, lalu dipakai pada 2024:

| Ukuran | Hasil |
|---|---|
| Ditandai di 2024 oleh model 2023 / model 2024 | 1,34% / 1,51% |
| Irisan (Jaccard) | 0,669 |
| Bobot 2024 pada pola yang tidak ada di tabel 2023 | 1,34% |

Model 2023 saja (18.193 bulan-pasien) sudah punya lebih dari 1,5% bobot di pola yang terlalu jarang untuk disimpan. Akibatnya semua tandanya di 2024 berasal dari pola yang tidak dikenalnya (1,34% = 1,34%). Satu tahun data terlalu tipis; model akhir dilatih dari dua tahun dan perlu dilatih ulang tiap tahun.

Uji luar (data sampel kontekstual, bobot mewakili kelompok penyakit itu):

| Sampel | Bulan-pasien | Ditandai model | Dipicu aturan | Hanya model |
|---|---|---|---|---|
| Kesehatan Mental 2015–2023 | 27.062 | 3,7% | 3,34% | 2,2% |
| COVID 2015–2024 | 8.910 | 5,73% | 2,52% | 3,89% |

Kelompok yang lebih sakit lebih sering ditandai. **Tidak biasa tidak sama dengan curang**: karena itu model hanya memilih siapa ditelepon.

## 10. Perbandingan dengan v1 (`BANDING-METODE.md`)

| Metode | Ditandai | Hanya model | Aturan ATAU model |
|---|---|---|---|
| anomali-v1 (Isolation Forest) | 1,53% | 0,68% | 2,72% |
| Kelangkaan nasional (tanpa kelompok) | 1,53% | 1,05% | 3,09% |
| anomali-v2 (umur) | 1,53% | 1,05% | 3,1% |

Uji sisipan: 2.000 bulan-pasien biasa 2024 diubah dengan satu manipulasi rancangan kami sendiri (menunjukkan apa yang bisa dilihat tiap metode, bukan kinerja di lapangan):

| Manipulasi | Aturan | v1 | Kelangkaan nasional | v2 |
|---|---|---|---|---|
| Pemadatan seminggu | 27% | 40,5% | 66,3% | 57% |
| Sesi hari Minggu | 24% | 26,4% | 75% | 63,3% |
| Tagihan digelembungkan (+5 sesi) | 11,7% | 8,2% | 11,1% | 10,7% |
| Sebagian tanpa rujukan (nilai tengah) | 0% | 17,5% | 34,4% | 49,5% |
| Rujukan janggal (meniru temuan utama v1) | 2,1% | 100% | 2,1% | 36,7% |

Cara membaca:

- v2 menangkap jauh lebih banyak pemadatan, sesi hari Minggu, dan nilai tengah daripada v1. v1 hanya unggul pada pola yang memang temuan utamanya sendiri.
- Antara v2 dan kelangkaan nasional tidak ada pemenang mutlak: kelangkaan nasional lebih banyak menangkap sesi hari Minggu dan pemadatan, v2 lebih banyak menangkap pola rujukan. v2 dipilih karena memperkirakan tahun lain lebih baik (bagian 5), bukan karena uji sisipan.
- Tagihan yang hanya digelembungkan jumlah sesinya hampir tidak tertangkap metode mana pun: sesi lebih banyak dalam batas biasa tidak membuat pola jarang. Ini batas pendekatan berbasis pola.

## 11. Tingkat RS: corong (funnel plot)

Untuk tiap kelompok RS sejenis (kab/kota + kepemilikan + jenis + tipe; data sampel tidak memuat identitas RS) dengan minimal 30 bulan-pasien:

```
harapan = Σ laju dipilih (aturan ATAU model) di kelompok umur tiap bulan-pasien
z       = (dipilih − harapan) / √(Σ p(1 − p) · φ)
```

φ = faktor overdispersi (Spiegelhalter, penyesuaian multiplikatif): rata-rata z² setelah z dipangkas di persentil 10 dan 90, minimal 1. Hasilnya **φ = 2,54**: RS jauh lebih beragam daripada yang dijelaskan umur pasien saja. Tanpa φ, 44 dari 423 kelompok melewati batas 99,8% (harapan kebetulan 0,4). Dengan φ:

| Ukuran | Hasil |
|---|---|
| Kelompok RS sejenis dinilai | 423 |
| Di atas batas 95% (z > 1,96) | 44 |
| Di atas batas 99,8% (z > 3,09) | 27 |
| Pangsa pasien dipilih yang berada di 27 kelompok itu | 43,3% |

Pasien yang dipilih mengumpul di sedikit kelompok RS. Hanya jumlah yang di-commit; identitas kelompok tidak disimpan. Di demo, RS Melati Sehat (RS yang disisipi pola curang) dipilih 27 bulan-pasien dibanding harapan 2,3 (z = 10,34, di atas batas 99,8%); empat RS lain di dalam batas.

## 12. Privasi

| Aturan | Cara dipenuhi |
|---|---|
| Data mentah tidak keluar dari laptop | Hanya skrip di `ai-service/scripts` yang membacanya |
| Tanpa baris per orang | Model hanya memuat pangsa sel dengan minimal 10 bulan-pasien; kelompok umur minimal 300 |
| Tanpa nilai minimum atau maksimum | Batas bin ditetapkan tangan |
| Tanpa identitas kelompok RS | Tingkat RS hanya melaporkan jumlah |
| Penjaga otomatis | `assert_privacy_safe` menolak kunci identitas; uji di `ai-service/tests/test_anomaly_model.py` memeriksa berkas yang di-commit |

## 13. Batasan

- **Tanpa label.** Angka di atas adalah perilaku, bukan ketepatan. Ketepatan diukur dari hasil panggilan: berapa yang ditandai model berakhir Tidak sesuai.
- **Jarang tidak sama dengan curang.** Kelompok yang lebih sakit lebih sering ditandai.
- **Tagihan yang hanya digelembungkan** (lebih banyak sesi dalam batas biasa) hampir tidak terlihat dari pola.
- **Arti `FKP02` kosong belum pasti**: bisa kunjungan kontrol dengan surat kontrol RS. Perlu dipastikan bersama verifikator BPJS.
- **Pola bergeser antartahun** (Jaccard 0,669). Latih ulang tiap tahun dengan minimal dua tahun data.
- **Tanpa daftar libur nasional**: `ahad_libur` hanya menghitung hari Minggu.
- **Beban panggilan naik**: dari ≈ 5.800 menjadi ≈ 8.800 tagihan bulanan per bulan secara nasional.
- **Kelompok RS hanya mendekati satu RS.** Corong di produksi perlu identitas RS asli.

## 14. Integrasi

Sudah:

1. Backend (`backend/app/anomali_v3.py`, `scripts/seed_v3.py`): `seed_v3` menilai semua bulan-pasien aktif dengan `tools/anomali.py`, umur dari `peserta.umur`, rujukan dari `klaim_sesi.rujukan_fktp` dan `.perujuk_luar_wilayah`. Hasil di `indikator_bulanan.skor_anomali`, `.anomali_ditandai`, `.anomali_langka`, `.alasan_anomali`. Antrean = `dipicu OR anomali_ditandai`, diurutkan pola paling jarang dulu (menggantikan skor pola `pola-v1`, yang dipensiunkan).
2. API (`docs/api-contract-v3.md`, perubahan 2026-11-17): `dipilih` di antrean dan detail, objek `anomali`, `funnel` per RS, `kinerja_model`.
3. Web mode API membaca field yang sama dengan mode simulasi.

Belum:

1. Kelompok kontrol: telepon sampel acak kecil pasien yang tidak dipilih. Tanpa itu, hanya presisi yang bisa diukur, bukan yang terlewat.
2. Data klaim nyata perlu kolom rujukan per kunjungan (nomor rujukan FKTP dan kab/kota perujuk). Tanpa kolom itu, semua kunjungan dianggap dirujuk FKTP setempat.

## 15. Menjalankan ulang

```bash
cd ai-service
D="../Folder Data Asli"
R23="$D/Data Sampel 2015-2023/Data Sampel Reguler Edisi 2024/data"
A="$D/2025 2/Data Sampel Reguler Edisi 2025/data"
B="$D/2025/Data Sampel Reguler Edisi 2025/data"
KM="$D/Data Sampel 2015-2023/Data Sampel Kontekstual Kesehatan Mental Edisi 2024/data"
COV="$D/2025/Data Sampel Kontekstual COVID Edisi 2025/data"
ARGS=(--sample "$R23/202303_fkrtl.dta" "$R23/2015202301_kepesertaan.dta" "$R23/202305_diagnosissekunder.dta"
      --sample "$A/202403_fkrtl.dta" "$B/2015202401_kepesertaan.dta" "$B/202405_diagnosissekunder.dta"
      --outside "$KM/KM20152023_fkrtl.dta" "$KM/KM2023_kepesertaan.dta"
      --outside "$COV/COV20152024_fkrtl.dta" "$COV/COV2024_kepesertaan.dta")
uv run --group data python scripts/train_anomaly_model.py "${ARGS[@]}"    # sekitar 50 detik
uv run --group data python scripts/compare_anomaly_models.py "${ARGS[@]}"
python3 ../data-uji-konfirmasi/tools/anomali_demo.py                       # lalu salin ke data-v3.js
uv run pytest tests/test_anomaly_model.py
```

Dengan data yang sama, hasilnya sama (tanpa unsur acak, kecuali sampel uji sisipan yang memakai seed tetap).

## 16. Peta berkas

| Berkas | Isi |
|---|---|
| `data-uji-konfirmasi/tools/anomali.py` | Fitur, bin, penilai, alasan, corong RS. Pustaka standar. |
| `data-uji-konfirmasi/tools/anomali_demo.py` | Hasil model untuk data demo (`anomali_demo.json`) |
| `ai-service/src/vedika_ai/ml/cohort.py` | Pembaca kohort dari data mentah (kunjungan, diagnosis sekunder, umur) |
| `ai-service/src/vedika_ai/ml/anomaly_model.py` | Pelatihan: pangsa, penghalusan, ambang, overdispersi, pemilihan kelompok |
| `ai-service/src/vedika_ai/ml/anomaly_evaluation.py` | Perilaku, validasi antartahun, uji luar, ringkasan corong |
| `ai-service/scripts/train_anomaly_model.py` | CLI dan `EVALUASI-ANOMALI.md` |
| `ai-service/scripts/compare_anomaly_models.py` | CLI dan `BANDING-METODE.md` |
| `ai-service/tests/test_anomaly_model.py` | Uji bin, penghalusan, ambang, nilai tengah, corong, privasi berkas yang di-commit |
