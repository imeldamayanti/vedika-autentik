# Skor pola

Skor pola adalah angka 0–1 untuk tiap bulan-pasien fisioterapi. Angka ini menunjukkan seberapa mirip pola tagihan bulan itu dengan pola manipulasi yang dikenal, dibanding pola nasional data sampel BPJS 2024.

## Apa yang dilakukan dan tidak dilakukan

| Skor pola | Tetap tugas aturan (`tools/aturan.py`) |
|---|---|
| Mengurutkan antrean panggilan | Menentukan siapa yang ditelepon (≥ 2 indikator I1–I4) |
| Menjelaskan mengapa satu panggilan didahulukan | Memberi label dari jawaban penerima |
| Memberi pembanding nasional per tipe RS | Memberi saran dan status RS |

Skor tidak pernah membuat panggilan, label, saran, atau status RS. Skor bukan peluang kecurangan dan bukan putusan. Istilah di layar dan API: "Skor pola" dan "Pola tidak biasa".

## Jalur data dan privasi

```
Folder Data Asli (laptop, tidak di-commit)
   │  ai-service/scripts/prepare_pattern_reference.py
   ▼
ai-service/data/reference/pola-2024/      agregat, tiap sel ≥ 10 baris
   │  ai-service/scripts/train_pattern_model.py
   ▼
data-uji-konfirmasi/referensi-pola/       koefisien model + referensi nasional
   │  backend/app/pola_v3.py (Python murni, tanpa numpy/sklearn)
   ▼
indikator_bulanan.skor_pola → antrean, kartu bukti, Ringkasan RS
```

- Data mentah hanya dibaca pembangun referensi di laptop. Backend tidak pernah membacanya, dan tidak membaca `kunci_kebenaran_*`.
- Yang di-commit hanya agregat: tanpa nomor peserta, keluarga, atau kunjungan; tanpa baris per orang; tanpa nilai maksimum atau minimum; sel di bawah 10 baris disembunyikan.
- Model dilatih dari histogram agregat, bukan dari baris mentah, jadi pelatihan bisa diulang tanpa folder data asli.
- Data sampel tidak memuat identitas RS. "Kelompok RS sejenis" = kab/kota + kepemilikan + jenis + tipe, dan hanya mendekati satu RS.

## Cara kerja

1. **Fitur** (`tools/pola.py`, satu definisi untuk semua pemakai): `sesi` (jumlah sesi sebulan), `maks_minggu` (sesi terbanyak dalam satu minggu Senin–Minggu), `ahad_libur` (sesi di hari Minggu atau libur), `episode` (bulan berturut-turut, maksimal 7). Tiap fitur dibagi ke dalam bin.
2. **Kelas normal**: 50.000 bulan-pasien yang diambil dari histogram nasional Juli–Desember 2024.
3. **Kelas pelanggaran**: 50.000 bulan-pasien normal yang diubah dengan 1–2 manipulasi yang meniru aturan (tambah sesi, sesi hari libur, pemadatan dalam seminggu, perpanjangan episode). Metode ini disebut supervisi lemah berpandu pengetahuan (mengikuti CleverCatch, arXiv 2510.13205).
4. **Model**: regresi logistik atas bin. Hasilnya tabel koefisien di `model-pola-v1.json`. Skor = logistik(intersep + jumlah koefisien bin yang aktif).
5. **Ambang** `ambang_tinggi` = persentil 98,5 skor nasional, supaya "Pola tidak biasa" menyala pada kira-kira 1,5% bulan-pasien nasional, setara dengan tingkat pemicu aturan.
6. **Alasan**: dua fitur dengan sumbangan terbesar terhadap skor, dibanding rata-rata nasional. Sumbangannya eksak karena modelnya linear.

## Membaca layar

- **Antrean.** Chip `Pola 0,93` dengan batang tipis. Chip berwarna merah bila skor ≥ ambang. Urutan antre: Dahulukan, lalu skor tertinggi, lalu id. Agen mengambil tugas dengan urutan yang sama.
- **Kartu bukti, "Mengapa diprioritaskan".** Dua alasan, lalu satu kalimat tentang seberapa jarang kombinasi indikatornya di data nasional. Kombinasi yang muncul kurang dari 10 kali di data sampel hanya punya batas atas ("kurang dari 0,03%").
- **Ringkasan RS.** Satu baris per RS: persen terpicu RS ini, rata-rata RS sejenis nasional, dan batas 95% kelompok RS sejenis. Lencana "Di atas 95% RS sejenis" bila RS melewati batas itu. Kartu "Skor pola vs hasil panggilan" membandingkan skor dengan label Sesuai dan Tidak sesuai.

Di data demo, RS Melati Sehat (39,7% terpicu) berada di atas 95% RS Swasta Setara Type C (batas 8,2%). Empat RS lain berposisi wajar.

## Tingkat bukti

Angka selalu dilaporkan per tingkat dan tidak digabung. Rinciannya di `data-uji-konfirmasi/referensi-pola/EVALUASI.md`.

| Tingkat | Isi | Arti |
|---|---|---|
| A | Agregat data sampel BPJS 2024: prevalensi indikator, marginal, pembanding per tipe, pangsa nasional di atas ambang | Nyata |
| B | AUC normal vs pelanggaran buatan; evaluasi di data demo terhadap kunci kebenaran; label panggilan demo | Sintetis. Menguji metode, bukan kinerja di lapangan |

## Membangun dan melatih ulang

```bash
cd ai-service
# 1. agregat dari data mentah (hanya di laptop yang punya Folder Data Asli)
uv run --group data python scripts/prepare_pattern_reference.py \
  --source "../Folder Data Asli/2025 2/Data Sampel Reguler Edisi 2025/data/202403_fkrtl.dta" \
  --output data/reference/pola-2024
# 2. model, referensi, skor demo, dan EVALUASI.md (hanya membaca berkas yang di-commit)
uv run --group data python scripts/train_pattern_model.py
# 3. isi skor ke database (tanpa --reset cukup untuk database yang sudah berjalan)
cd ../backend && .venv/bin/python -m scripts.terapkan_v3
```

Setelah langkah 2, salin nilai baru ke tabel `POLA` di `data-v3.js` bila skor demo berubah (uji mandiri di konsol dan `tests/alur-v3.test.js` akan menandainya).

### Belajar dari hasil panggilan

```bash
cd backend && .venv/bin/python -m scripts.ekspor_label_pola        # backend/uploads/label-panggilan.json
cd ../ai-service && uv run --group data python scripts/train_pattern_model.py \
  --label-panggilan ../backend/uploads/label-panggilan.json        # menulis model-pola-v2.json
```

Ekspor hanya berisi fitur yang sudah dibin dan label (1 = Tidak sesuai) dari panggilan berlabel Sesuai atau Tidak sesuai. Label panggilan diberi bobot 5. `pola-v1` tetap bawaan; backend memakai versi di `pengaturan.versi_pola`. Untuk berpindah: commit `model-pola-v2.json`, ubah `versi_pola` menjadi `"pola-v2"`, lalu jalankan `scripts.terapkan_v3` supaya skor dihitung ulang. Di demo label panggilannya sintetis, jadi langkah ini hanya menunjukkan alurnya.

## Batasan

- Kelas pelanggaran dibuat dari aturan yang sama dengan aturan pemicu. Skor karena itu sangat sejalan dengan aturan dan belum menemukan pola baru. Di data demo tidak ada kasus yang lolos aturan tetapi berskor tinggi.
- Di data nyata, semua sel yang memuat sesi hari Minggu berisi kurang dari 10 baris dan disembunyikan. Kelas normal jadi tidak punya sesi hari Minggu, dan model memberi skor hampir 1,00 pada setiap bulan-pasien yang punya sesi Minggu atau libur. Di antrean demo, 19 dari 26 panggilan berskor 1,00 dan urutannya ditentukan id.
- Koefisien `sesi` tidak naik terus: 9–13 sesi berkoefisien lebih rendah dari 7–8 sesi, dan bulan-pasien yang hanya melanggar I1 berskor rendah. Model membaca "banyak sesi tetapi tersebar rata" sebagai pola nyata yang wajar.
- Pangsa nasional di atas ambang (1,56%) dihitung dari sel yang tidak disembunyikan. Dengan sel tersembunyi, nilainya antara kira-kira 1,5% dan 3,1%.
- Data 2024 tidak punya daftar libur, jadi `ahad_libur` dan I4 di data nyata hanya hari Minggu. Bulan sebelum Januari 2024 tidak ada, jadi I3 di prevalensi semua bulan terhitung lebih rendah; histogram hanya memakai Juli–Desember.
- Kelas normal adalah data nyata apa adanya dan bisa memuat manipulasi yang tidak terdeteksi.
- Pembanding per tipe wajib dibaca dalam tipenya. Contoh: RS Khusus Bedah punya tingkat terpicu jauh lebih tinggi, kemungkinan karena rehabilitasi pascabedah yang sah.
