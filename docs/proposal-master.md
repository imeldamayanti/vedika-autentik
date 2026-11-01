# Dokumen Induk Proposal — Vedika Autentik dan PRAMANA

**Nama produk:** Vedika Autentik  
**Mesin analisis:** PRAMANA  
**Slogan:** *Lengkap belum tentu asli.*  
**Kategori:** Efisiensi Risiko pada Fasilitas Kesehatan  
**Status dokumen:** Proposal-ready v1.0; menunggu persetujuan tim dan validasi BPJS  
**Tanggal:** 10 Oktober 2026

## 1. Fungsi dokumen

Dokumen ini adalah sumber utama untuk menyusun proposal, pitch deck, dan penjelasan teknis.
Ia menggabungkan masalah produk, ruang lingkup, data, arsitektur AI, status implementasi,
metrik, roadmap, kebutuhan sumber daya, serta risiko dalam satu narasi.

Dokumen ini membedakan tiga status secara tegas:

- **Terimplementasi:** tersedia di repositori dan diuji otomatis.
- **Tervalidasi:** sudah diukur pada dataset yang disebutkan secara eksplisit.
- **Direncanakan:** belum boleh ditulis sebagai kemampuan produk yang sudah tersedia.

## 2. Ringkasan eksekutif

Vedika Autentik adalah fitur pendukung verifikasi klaim yang memeriksa **keaslian dan
konsistensi bukti pelayanan fisioterapi**. Fitur ini dirancang masuk ke alur Vedika/JKN Drive,
bukan menjadi aplikasi baru bagi rumah sakit.

PRAMANA menganalisis dokumen yang sudah diunggah untuk:

1. memastikan scan cukup baik untuk diperiksa;
2. membaca isi penting dan jumlah sesi;
3. membandingkan isi dokumen dengan data klaim;
4. mencari dokumen atau bagian dokumen yang dipakai ulang;
5. menunjukkan indikasi penyuntingan beserta lokasinya;
6. memprioritaskan kasus dengan bukti yang dapat diperiksa manusia.

Sistem tidak menyatakan fraud dan tidak menolak klaim. PRAMANA menghasilkan bukti; backend
menerapkan aturan prioritas; verifikator tetap mengambil keputusan.

Versi yang sudah tersedia adalah baseline CPU berbasis FastAPI, OpenCV, Tesseract, template
dokumen, dan fingerprint. Versi lanjutan akan menambahkan VLM, model forensik visual,
analisis riwayat klaim, serta ringkasan LLM yang dibatasi oleh bukti terstruktur.

## 3. Masalah dan urgensi

Alur verifikasi dapat memastikan dokumen ada dan isinya terbaca, tetapi pemeriksaan manual
lintas ribuan dokumen sulit menemukan bahwa:

- lembar yang sama dipakai untuk pasien atau periode berbeda;
- tanda tangan, stempel, atau baris layanan disalin;
- jumlah sesi, tanggal, atau nilai diubah setelah pelayanan;
- isi dokumen tidak konsisten dengan klaim terstruktur;
- dokumen dibuat ulang secara digital agar tampak seperti hasil scan.

Konteks resmi yang mendukung fokus ini:

- Itjen Kemenkes melaporkan hasil pemeriksaan layanan periode Juli 2017–Juni 2018 pada tiga
  rumah sakit: dari 4.341 tagihan fisioterapi, 1.072 memiliki catatan rekam medis dan 3.269
  atau 75,3% diduga fiktif, dengan nilai Rp501,27 juta. Angka ini adalah hasil pemeriksaan
  kasus tertentu, bukan estimasi prevalensi nasional saat ini.
- Kajian KPK juga mencatat frekuensi fisioterapi yang mencapai 16–19 kali per bulan pada
  lokasi piloting, sehingga pola kunjungan merupakan sinyal telaah yang relevan tetapi tidak
  dapat menjadi vonis tanpa konteks klinis.
- Permenkes Nomor 16 Tahun 2019 tentang pencegahan dan penanganan fraud JKN masih berstatus
  berlaku pada basis JDIH Kementerian Kesehatan ketika dokumen ini disusun.

Nilai utama produk adalah mengubah pencarian manual menjadi **triase berbasis bukti**:
verifikator melihat kasus paling relevan lebih dahulu dan dapat memahami alasannya tanpa
menafsirkan skor model yang tidak transparan.

## 4. Pengguna dan nilai produk

| Pengguna | Masalah | Nilai yang diberikan |
|---|---|---|
| Verifikator klaim | Volume dokumen tinggi dan perbandingan lintas berkas sulit | Antrean terurut dan bukti visual per temuan |
| Tim PK-JKN/auditor | Membutuhkan bukti yang dapat ditelusuri | Hash, versi mesin, pasangan dokumen, region, dan riwayat keputusan |
| Peserta JKN | Identitas dapat disalahgunakan untuk klaim | Mekanisme konfirmasi netral, jika disetujui BPJS |
| Rumah sakit | Klaim wajar dapat tertahan oleh sinyal yang keliru | Pemisahan scan buruk dari indikasi manipulasi dan hak klarifikasi |

## 5. Posisi produk

Vedika Autentik dirancang sebagai kemampuan tambahan pada sistem yang sudah ada:

| Sistem | Peran yang diusulkan |
|---|---|
| V-Claim | Sumber identitas klaim dan SEP, sesuai akses yang disetujui |
| E-Klaim | Sumber sesi, diagnosis, tindakan, dan nilai klaim terstruktur |
| JKN Drive | Sumber/pemicu dokumen yang sudah diunggah rumah sakit |
| Vedika | Tempat antrean, bukti, tindakan, dan keputusan verifikator |
| PANDAWA | Kandidat kanal konfirmasi peserta; perlu persetujuan proses dan kewenangan BPJS |

Integrasi produksi di atas adalah rancangan, bukan integrasi yang sudah tersedia di prototipe.

### Nilai kebaruan

- Menggabungkan forensik dokumen dan pola klaim; bukan sekadar OCR atau skor fraud tabular.
- Menunjukkan region dan pasangan dokumen yang mendasari temuan, bukan hanya skor model.
- Memisahkan scan buruk dari manipulasi agar kualitas input tidak berubah menjadi tuduhan.
- Menempatkan AI sebagai penghasil bukti dan manusia sebagai pengambil keputusan.
- Dapat dimulai dengan CPU dan menambah GPU tanpa mengubah alur backend/frontend.

## 6. Ruang lingkup

### 6.1 Masuk lingkup awal

- Fisioterapi/rehabilitasi medik rawat jalan.
- PDF, JPG, dan PNG satu sampai beberapa halaman.
- Scan berkualitas baik maupun buruk.
- Formulir bukti pelayanan dengan sesi, tanggal, dan tanda tangan.
- Pemeriksaan kualitas, ekstraksi, kecocokan klaim, reuse, copy-paste, metadata, dan bukti
  penyuntingan yang telah melewati evaluasi.
- Analisis pola klaim sebagai sinyal prioritas, bukan penilaian kebutuhan medis.

### 6.2 Di luar lingkup awal

- Keputusan fraud atau penolakan pembayaran otomatis.
- Identifikasi pemilik/penulis tanda tangan.
- Penilaian kebutuhan medis atau diagnosis klinis.
- Pelatihan foundation model dari nol.
- Semua jenis dokumen dan semua layanan kesehatan sekaligus.
- Pengiriman dokumen klaim ke API AI publik tanpa persetujuan privasi dan residensi data.
- Klaim bahwa detektor “gambar AI” dapat menjadi bukti tunggal.

## 7. Alur produk

```text
Rumah sakit mengunggah berkas
              │
              ▼
       cek kualitas scan
       ├── buruk ───────────────► Scan ulang
       └── layak
              │
              ▼
       baca dan normalisasi isi
              │
              ├── cocokkan dengan klaim dan riwayat
              ├── cari reuse/copy-paste
              └── periksa bukti penyuntingan
                              │
                              ▼
                    bukti terstruktur
                              │
                              ▼
                  aturan prioritas backend
                              │
                              ▼
                   keputusan verifikator
```

Prinsip gagal aman:

- scan buruk menjadi `Scan ulang`, bukan indikasi kecurangan;
- kegagalan analisis tidak boleh menghasilkan `Lolos`;
- sinyal lemah tidak dapat sendirian menjadi `Prioritas`;
- setiap temuan harus memiliki alasan dan asal bukti.

## 8. Sistem AI yang dibangun

### 8.1 Enam pemeriksaan dan bukti prototipe

| Pemeriksaan | Modus yang dijawab | Fixture utama | Status mesin saat ini |
|---|---|---|---|
| 1. Isi berkas tidak cocok dengan klaim | Phantom billing; tindakan ditagih melebihi bukti | `VA-DST-01`, `VA-DST-02` | Terimplementasi untuk jumlah sesi, periode, dan SEP yang berhasil dibaca |
| 2. Berkas dipakai ulang | Cloning lintas pasien atau periode | `VA-KMB-01`–`03`, dibandingkan dengan `VA-KMB-00`/`VA-ASL-02` | Terimplementasi melalui masked fingerprint dan pair confirmation |
| 3. Copy-paste dalam satu berkas | Penambahan sesi/bukti yang tidak berasal dari kejadian terpisah | `VA-DST-02`, `VA-AI-02` | Terimplementasi baseline untuk baris dan tanda tangan berulang |
| 4. Tempelan dari berkas lain | Cloning bagian tanda tangan, stempel, atau baris | `VA-KMB-01`–`03` beserta dokumen sumbernya | Terimplementasi bila backend menemukan kandidat pasangan |
| 5. Angka atau teks disunting | Penambahan sesi atau perubahan periode/identitas | `VA-DST-01`, `VA-DST-03`, seri `VA-KMB` | Parsial; fixture recall saat ini 0,40 dan belum production-ready |
| 6. Berkas buatan AI/rekayasa digital | Pembuatan bukti digital untuk mendukung cloning/phantom billing | `VA-AI-01`–`03` | Metadata dan integritas template tersedia sebagai sinyal pendukung; bukan detektor definitif |

Semua fixture di atas mempunyai PDF/JPG, ground truth JSON, dan region bukti. Fixture AI
tertentu juga mempunyai PNG. Seluruh identitasnya fiktif.

Empat label juga terwakili:

| Label | Fixture contoh |
|---|---|
| Lolos | `VA-ASL-01`–`04`, `VA-KMB-00` |
| Scan ulang | `VA-BRM-01`–`03` |
| Perlu dicek | `VA-DST-03`, `VA-AI-01`, `VA-AI-03` |
| Prioritas | `VA-KMB-01`–`03`, `VA-DST-01`, `VA-DST-02`, `VA-AI-02` |

### 8.2 Kemampuan inti

| Sistem | Masukan | Keluaran | Status |
|---|---|---|---|
| Quality gate | PDF/gambar | Ketajaman, kemiringan, pencahayaan, status scan | Terimplementasi; validasi nyata belum selesai |
| Normalisasi dokumen | PDF/gambar | Halaman kanonik dan koreksi perspektif | Terimplementasi |
| Ekstraksi berbasis template | Halaman kanonik | SEP, periode, baris, tanggal, total | Terimplementasi baseline |
| Kecocokan klaim | Ekstraksi + konteks klaim | Field cocok/tidak cocok | Terimplementasi untuk konteks terbatas |
| Copy-paste internal | Region baris/tanda tangan | Region berulang dan kemiripan | Terimplementasi baseline |
| Fingerprint dan perbandingan pasangan | Dokumen A dan B | Kemiripan dan region bersama | Terimplementasi |
| Metadata/provenance | PDF/EXIF | Sinyal editor atau integritas template | Terimplementasi sebagai bukti pendukung |
| Referensi klaim terstruktur | Sampel FKRTL | Distribusi diagnosis, tindakan, biaya, frekuensi | Phase 0 terimplementasi |
| VLM document understanding | Dokumen multi-halaman | JSON ter-grounding ke halaman/region | Direncanakan; perlu benchmark |
| Model lokalisasi edit | Piksel dokumen | Peta region dan reliabilitas | Direncanakan; perlu data berlabel |
| Anomali riwayat klaim | Klaim + histori terbatas | Frekuensi, kronologi, kombinasi, biaya | Direncanakan |
| Evidence fusion | Seluruh sinyal | Skor risiko terkalibrasi | Direncanakan setelah label reviewer cukup |
| LLM reviewer brief | Bukti terstruktur | Ringkasan bahasa Indonesia dengan evidence ID | Direncanakan; tidak mengubah skor/label |

### 8.3 Peran VLM dan LLM

VLM digunakan untuk membaca layout kompleks, tulisan, tabel, dokumen multi-halaman, dan
memberikan lokasi field. Kandidat awal adalah Qwen3-VL-8B-Instruct dengan 4B sebagai fallback.
Pemilihan akhir bergantung pada benchmark formulir Indonesia, bukan klaim benchmark umum.

LLM/VLM tidak:

- menetapkan fraud;
- menghasilkan skor risiko secara bebas;
- menambahkan temuan yang tidak ada dalam evidence JSON;
- menggantikan pemeriksaan piksel khusus untuk lokalisasi manipulasi.

Ringkasan LLM bersifat opsional. Template kalimat deterministik tetap tersedia.

### 8.4 Analisis klaim terstruktur

Fitur yang akan dihitung secara bertahap:

- jumlah kunjungan per hari/minggu/bulan;
- klaim pada tanggal yang sama atau sangat berdekatan;
- urutan rujukan dan layanan yang tidak konsisten;
- diagnosis–prosedur yang jarang muncul bersama;
- biaya di luar distribusi pembanding yang sesuai;
- perubahan mendadak pada pola longitudinal;
- kemiripan klaim lintas peserta atau penyedia.

Tahap awal menggunakan aturan, persentil robust, dan Isolation Forest. Model urutan dalam atau
graph neural network hanya dipertimbangkan bila baseline gagal pada target yang terukur dan
identifier produksi yang diperlukan tersedia.

## 9. Data

### 9.1 Dataset dokumen sintetis

Repositori memiliki 17 formulir fisioterapi sintetis:

- 4 dokumen asli;
- 4 keluarga dokumen kembar/reuse;
- 3 dokumen dengan angka atau baris disunting;
- 3 dokumen buatan AI/aplikasi desain;
- 3 scan buruk.

Setiap sampel memiliki PDF/JPG, JSON ground truth, tipe manipulasi, dan region. Dataset ini
cukup untuk regresi perangkat lunak, tetapi terlalu kecil dan terlalu sintetis untuk membuktikan
akurasi produksi.

### 9.2 Sampel klaim terstruktur

`Folder Data Asli` berisi sekitar 6,4 GB sampel administratif:

- 115 file Stata `.dta`;
- 40 workbook metadata/kode;
- 43 skrip Stata;
- periode data sekitar 2015–2024;
- kepesertaan, FKTP kapitasi, FKTP non-kapitasi, FKRTL, diagnosis sekunder, dan subset penyakit.

Ekstraksi privacy-safe 2024 menghasilkan:

| Ukuran | Hasil |
|---|---:|
| Seluruh baris FKRTL | 1.699.219 |
| Rawat jalan | 1.503.675 |
| Rehabilitasi rawat jalan | 174.026 |
| Referensi spesifik fisioterapi | 149.997 |
| Peserta unik dalam agregasi | 13.172 |
| Participant-month | 41.905 |

Tidak ada identifier peserta, identifier kunjungan, atau baris klaim yang diekspor ke artefak
repositori. Sel kategori di bawah 10 disembunyikan. Dataset ini mendukung pola klaim dan
pembuatan data fiktif, bukan OCR, deteksi manipulasi piksel, atau supervised fraud model.

### 9.3 Data yang masih diperlukan

- Formulir dari 20–30 relawan dengan persetujuan, identitas fiktif, dan tulisan nyata.
- Hasil scan dan foto ponsel dengan variasi perangkat/pencahayaan.
- Edit terkendali dengan mask dan log perubahan.
- Split berdasarkan relawan/base document, bukan berdasarkan turunan gambar.
- Untuk kalibrasi produksi: hasil keputusan reviewer yang sudah melalui tata kelola BPJS.

Dokumen relawan tidak boleh masuk repositori publik.

## 10. Arsitektur dan batas tanggung jawab

```text
Frontend
   │
   ▼
backend/
  autentikasi, storage, database, antrean, retry,
  pencarian kandidat, aturan label, keputusan reviewer
   │
   ▼
ai-service/
  render, quality gate, OCR/VLM, fingerprint,
  perbandingan, forensik, claim intelligence, evidence
   │
   ├── CPU baseline
   └── GPU opsional
```

| Tanggung jawab | Pemilik |
|---|---|
| Upload, autentikasi, file, database, antrean | Backend |
| Lookup E-Klaim/JKN Drive | Backend |
| Rendering, ekstraksi, model, region bukti | AI service |
| Pencarian kandidat fingerprint dalam arsip | Backend |
| Konfirmasi pasangan dokumen | AI service |
| Label, saran tindakan, dan keputusan final | Backend/verifikator |
| Evaluasi model, data card, model card | Tim AI |

AI service tetap stateless dan tidak mengakses database produksi secara langsung.

## 11. Kontrak layanan

Endpoint saat ini:

| Endpoint | Fungsi |
|---|---|
| `GET /v1/kesehatan` | Readiness dan versi model |
| `POST /v1/analisis` | Analisis satu dokumen dan konteks klaim |
| `POST /v1/bandingkan` | Konfirmasi dua kandidat dokumen |

Endpoint yang direncanakan:

| Endpoint | Fungsi |
|---|---|
| `POST /v1/analisis-klaim` | Analisis current claim dan histori terbatas dari backend |

Perubahan kontrak bersifat additive pada `/v1`. Perubahan yang merusak kompatibilitas harus
menjadi `/v2`.

## 12. Status implementasi saat ini

| Area | Bukti saat ini | Batasan |
|---|---|---|
| API AI | FastAPI, Pydantic, service-key, Docker, tiga endpoint | Belum memakai GPU |
| Kualitas dan normalisasi | Unit, regression, perspective robustness | Belum diuji pada blind volunteer set |
| Ekstraksi | Session count tepat 14/14 pada fixture terbaca | Coverage field tulisan tangan masih rendah |
| Tanggal sesi | 6/14 dikembalikan dan 6/6 tepat | Coverage belum cukup |
| Name/card/SEP/period | 3/14, 5/14, 3/14, 11/14 dikembalikan; yang dikembalikan tepat | Dataset hanya sintetis |
| Duplicate/pair | 6/6 pasangan regresi tepat | Skala arsip nyata belum diuji |
| Temuan edit | Precision 1,00 dan recall 0,40 pada fixture | Belum layak menjadi klaim akurasi nyata |
| Latensi CPU | p95 1,34 detik per satu halaman pada regression lokal | Bukan benchmark deployment |
| Claim reference | Pipeline deterministik dan agregat 2024 tersedia | Tidak memiliki label fraud |
| Test suite | 58 test AI service lulus | Ada satu peringatan deprecasi Starlette/httpx |

Angka di atas hanya hasil dataset sintetis/repositori. Proposal tidak boleh menyebutnya sebagai
akurasi data BPJS atau kinerja produksi.

## 13. Strategi model dan tools

| Bagian | Pilihan |
|---|---|
| Environment | Python 3.12, `uv` |
| API/schema | FastAPI, Uvicorn, Pydantic |
| Logging | Loguru tanpa PII/OCR text |
| PDF/image | pypdfium2, pypdf, Pillow, OpenCV, NumPy |
| OCR baseline | Tesseract 5 |
| Ingest Stata offline | pyreadstat + pandas chunking |
| VLM kandidat | Qwen3-VL-8B-Instruct; 4B fallback |
| VLM runtime awal | PyTorch + Transformers |
| Anomali tabular | Robust statistics + scikit-learn Isolation Forest |
| Kalibrasi | Logistic regression setelah label cukup |
| Tracking | Manifest JSON/CSV/Parquet berversi |
| Similarity | pHash saat ini; vector search hanya bila ada kebutuhan terukur |

TruFor hanya boleh menjadi benchmark riset karena repositori resminya membatasi penggunaan
untuk tujuan informasi dan nonprofit. Produksi membutuhkan model/weights dengan lisensi yang
sesuai dan hasil blind evaluation pada domain dokumen ini.

## 14. Evaluasi dan release gates

### 14.1 Metrik utama

| Lapisan | Metrik/gate |
|---|---|
| Ekstraksi | Schema valid 100%; identifier tepat ≥98% ketika dikembalikan; tanggal dan sesi ≥95% |
| VLM safety | Incorrect confident values ≤2%; coverage mengungguli baseline tanpa menurunkan precision |
| Duplicate | Recall kandidat dan precision setelah pair verification |
| Forensik | Edited-region recall ≥70% dengan precision dilaporkan |
| End-to-end | Dokumen asli salah menjadi Prioritas ≤5% |
| Scan buruk | Salah menjadi indikasi manipulasi = 0 |
| Reviewer brief | Semua kalimat terhubung ke evidence ID; unsupported statement = 0 setelah validasi |
| Operasional | p50/p95 latency, throughput, GPU memory, timeout, dan failure rate |

### 14.2 Protokol

1. Pisahkan data berdasarkan relawan/base document: 70% development, 30% blind test.
2. Setel threshold hanya pada development split.
3. Bekukan versi mesin, template, model, prompt, dan threshold.
4. Jalankan blind split satu kali dan laporkan false positive serta miss.
5. Laporkan hasil synthetic, development, blind, dan shadow production secara terpisah.
6. Jangan menggabungkan semuanya menjadi satu angka “akurasi AI”.

Model baru masuk produksi hanya bila mengungguli baseline relevan dan lolos gate privasi,
lisensi, akurasi, serta operasional.

## 15. Roadmap pelaksanaan

| Fase | Isi | Status/gate |
|---|---|---|
| Baseline | Contract B, CPU OCR, kualitas, template, fingerprint, pair comparison | Terimplementasi |
| 0. Data safety | Ignore raw data, agregasi FKRTL, dictionary, manifest, privacy tests | Selesai |
| 1. VLM benchmark | Adapter OCR/VLM, grounding, multi-page, 4B vs 8B | Berikutnya; perlu volunteer set/GPU |
| 2. Claim intelligence | Endpoint klaim, frekuensi, duplikat, kronologi, biaya | Setelah schema dan evaluation cases siap |
| 3. Synthetic factory | ≥1.000 original/edit pairs dengan mask | Setelah data distribution disetujui |
| 4. Visual forensics | Satu model lokalisasi yang license-compatible | Hanya bila blind gate tercapai |
| 5. Fusion + brief | Kalibrasi dan ringkasan evidence-grounded | Setelah reviewer labels cukup |
| 6. Shadow rollout | CPU/GPU profile, pinned weights, shadow comparison | Sebelum hasil model terlihat reviewer |

Setiap fase dapat dihentikan tanpa merusak baseline. Fitur yang gagal gate tetap dimatikan.

Urutan ini adalah work breakdown, bukan janji tanggal. Jadwal pilot baru dapat dibekukan setelah
akses data, jumlah template, ketersediaan relawan/verifikator, dan infrastruktur GPU disetujui.

## 16. Deployment dan sumber daya

### 16.1 Komputasi

- Baseline berjalan pada CPU dan harus selalu tersedia sebagai fallback.
- Benchmark VLM dimulai pada satu GPU NVIDIA 24 GB untuk kandidat 8B.
- Kapasitas final dipilih dari pengukuran latency, throughput, peak memory, dan concurrency.
- Bobot model dipin berdasarkan revision dan checksum; tidak ada download saat startup.
- AI service tidak membutuhkan GPU untuk aturan klaim, fingerprint, atau quality gate.

Angka 24 GB adalah konfigurasi uji awal, bukan kebutuhan final yang sudah dibuktikan.

### 16.2 Peran minimum

| Peran | Tanggung jawab |
|---|---|
| AI engineer | Data pipeline, OCR/VLM, forensik, claim intelligence, evaluasi |
| Backend engineer | Storage, DB, antrean, integrasi, label, audit trail |
| Frontend/product | Antrean dan penyajian bukti yang mudah dipahami |
| Verifikator/domain expert | Label ambigu, workflow, threshold operasional |
| Privacy/security reviewer | Dasar pemrosesan, akses, retensi, threat review |

### 16.3 Artefak AI yang wajib

- source code dan lockfile;
- data dictionary dan dataset manifest;
- model card/prompt card;
- versioned evaluation report;
- threshold/configuration version;
- daftar lisensi dependency dan weights;
- rollback/fallback procedure.

## 17. Privasi, keamanan, dan tata kelola

Data kesehatan termasuk data pribadi spesifik dalam UU Nomor 27 Tahun 2022. Rancangan harus
menerapkan sekurang-kurangnya:

- pemrosesan di lingkungan yang disetujui BPJS;
- enkripsi saat transit dan tersimpan;
- least privilege dan akses berbasis peran;
- audit log akses dan keputusan;
- retensi dan penghapusan yang ditetapkan;
- pemisahan data development, blind evaluation, dan produksi;
- larangan PII, OCR text, gambar, filename, atau payload dalam log;
- masking identitas sebelum similarity search lintas dokumen;
- human review, alasan keputusan, dan kanal klarifikasi;
- evaluasi bias dan false-positive menurut kelompok yang relevan sebelum produksi.

Penggunaan PANDAWA untuk pesan proaktif verifikasi klaim adalah usulan proses dan memerlukan
persetujuan BPJS. Sumber publik saat ini mengonfirmasi PANDAWA sebagai kanal administrasi,
bukan otomatis sebagai otorisasi use case konfirmasi klaim ini.

## 18. Risiko dan mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| VLM berhalusinasi | Field salah tampak meyakinkan | JSON schema, cross-check OCR, nullable output, gate incorrect-confident |
| Scan buruk dianggap manipulasi | Rumah sakit dirugikan | Quality gate menghentikan pemeriksaan keaslian |
| Pola langka dianggap fraud | False positive | Sinyal review saja, subgroup audit, alasan fitur |
| Synthetic-to-real gap | Metrik demo tidak bertahan | Volunteer blind set dan shadow rollout |
| Model/lisensi tidak cocok produksi | Tidak dapat dideploy | License review sebelum integrasi dan weights pinning |
| GPU mati/mahal | Analisis tertunda | CPU fallback, bounded concurrency, timeout |
| Pelaku beradaptasi | Recall menurun | Drift monitoring dan evaluasi berkala |
| Data bocor melalui log/artefak | Risiko hukum dan peserta | Allowlist logging, automated privacy tests, private storage |
| Beban reviewer meningkat | Nilai produk negatif | Kalibrasi threshold terhadap kapasitas dan precision |
| Model dianggap pengambil keputusan | Risiko tata kelola | Backend/verifikator tetap pemilik label dan tindakan |

## 19. Pengukuran keberhasilan produk

Target teknis tidak cukup. Pilot juga harus mengukur:

- waktu median verifikator memahami satu kartu bukti;
- jumlah dokumen manual yang perlu dibuka per klaim;
- precision kasus yang dinaikkan untuk telaah;
- proporsi scan ulang yang berhasil diperbaiki;
- kesepakatan antarverifikator sebelum dan sesudah bantuan sistem;
- override rate terhadap rekomendasi sistem;
- jumlah kasus yang selesai tanpa tambahan langkah rumah sakit;
- latency dan availability layanan.

Nilai finansial atau penghematan belum boleh diklaim sebelum volume pilot, baseline proses,
dan outcome verifikator tersedia.

## 20. Skenario demo

1. Unggah dokumen asli; tampilkan quality gate dan hasil yang tidak memiliki temuan.
2. Unggah dokumen kembar; tampilkan pasangan berdampingan setelah identitas dimasking.
3. Unggah dokumen 5 sesi yang ditagih 8; tampilkan mismatch dan region baris kosong.
4. Unggah scan buruk; tunjukkan bahwa sistem meminta scan ulang tanpa tuduhan manipulasi.
5. Tampilkan ringkasan riwayat klaim sintetis dan alasan frekuensi masuk review.
6. Verifikator memilih tindakan dan laporan menyimpan versi mesin serta bukti.

Kemampuan VLM, forensik learned, dan LLM hanya didemonstrasikan sebagai “sudah tersedia” bila
fase terkait telah lolos gate. Jika belum, tampilkan sebagai roadmap atau hasil eksperimen.

## 21. Keputusan yang dibutuhkan dari BPJS

1. Format dan API JKN Drive/E-Klaim yang dapat digunakan untuk pilot.
2. Template rumah sakit dan variasi dokumen prioritas.
3. Dasar pemrosesan, lokasi deployment, retensi, dan akses data.
4. Kapasitas review per kantor cabang untuk kalibrasi threshold.
5. Definisi outcome pilot dan siapa yang memberi ground truth.
6. Apakah PANDAWA dapat digunakan untuk pesan keluar pada use case ini.
7. Batas penggunaan identifier untuk pencarian reuse dan analisis longitudinal.
8. Mekanisme klarifikasi rumah sakit dan audit keputusan.

## 22. Pernyataan proposal yang aman

Gunakan formulasi berikut:

> Vedika Autentik membantu verifikator memprioritaskan bukti pelayanan fisioterapi yang perlu
> diperiksa, dengan menunjukkan ketidaksesuaian klaim, reuse dokumen, dan region mencurigakan.
> Keputusan tetap berada pada verifikator.

Hindari formulasi berikut sebelum ada pilot produksi:

- “AI kami mendeteksi fraud dengan akurasi X%.”
- “Sistem menjamin dokumen asli.”
- “Model mendeteksi semua dokumen buatan AI.”
- “Sistem menghemat RpX miliar.”
- “PANDAWA siap dipakai untuk konfirmasi klaim.”

## 23. Sumber dan dokumen pendukung

### Sumber eksternal utama

- [Itjen Kemenkes — tindak lanjut dugaan klaim fiktif di tiga RS](https://itjen.kemkes.go.id/berita/detail/tindaklanjut-dan-pemberian-sanksi-atas-dugaan-klaim-fiktif-di-3-rs-swasta)
- [KPK — ringkasan kajian penanganan kecurangan JKN](https://cms.kpk.go.id/storage/4152/Buku_Ringkasan_Litbang_Unduh.pdf)
- [JDIH Kemenkes — Permenkes Nomor 16 Tahun 2019](https://jdih.kemkes.go.id/documents/peraturan-menteri-kesehatan-nomor-16-tahun-2019)
- [BPK — UU Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi](https://peraturan.bpk.go.id/Details/229798/uu-no-27-)
- [BPJS Kesehatan — informasi kanal PANDAWA](https://bpjs-kesehatan.go.id/haldownload-3.html)
- [Qwen3-VL official repository](https://github.com/QwenLM/Qwen3-VL)
- [Qwen3-VL-8B-Instruct model card](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct)
- [TruFor official repository and license notice](https://github.com/grip-unina/TruFor)

### Dokumen internal

- Product PRD: [`../ai-service/PRD_Vedika_Autentik_PRAMANA.md`](../ai-service/PRD_Vedika_Autentik_PRAMANA.md)
- Technical PRD: [`ai-technical-prd.md`](ai-technical-prd.md)
- Advanced AI plan: [`ai-advanced-plan.md`](ai-advanced-plan.md)
- AI validation protocol: [`ai-validation-protocol.md`](ai-validation-protocol.md)
- API contract: [`api-contract.md`](api-contract.md)
- Backend plan: [`rencana-be.md`](rencana-be.md)
- Synthetic dataset guide: [`../dataset/README.md`](../dataset/README.md)
- Claim reference: [`../ai-service/data/reference/README.md`](../ai-service/data/reference/README.md)

## 24. Isian yang wajib dilengkapi sebelum proposal dikirim

Dokumen teknis ini sudah dapat menjadi sumber proposal. Bagian berikut masih memerlukan input
organisasi dan tidak boleh ditebak oleh tim AI:

- nama, profil, dan pembagian peran anggota tim;
- format dan batas halaman proposal resmi;
- target serta durasi pilot yang disepakati;
- angka anggaran SDM, GPU, storage, dan operasional;
- pilihan hosting/on-premise dan penanggung jawab keamanan;
- surat atau bukti hak penggunaan dataset;
- rumah sakit/kantor cabang calon lokasi pilot;
- persetujuan penggunaan PANDAWA dan sumber data produksi;
- hasil blind volunteer evaluation setelah Phase 1–4 dijalankan.
