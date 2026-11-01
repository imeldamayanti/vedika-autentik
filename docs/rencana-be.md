# Rencana Backend Vedika Autentik

Status: draft untuk dibahas dengan Zahra (AI engineering). Kontrak lengkap ada di [api-contract.md](api-contract.md).

## 1. Tujuan

Mengganti data hardcode di `dataset/manifest.js` dengan pemeriksaan yang benar-benar berjalan (PRD bagian 12, 16), tanpa membuat demo berisiko mati di depan juri.

| Target | Isi |
|---|---|
| **Besok (aman)** | Kontrak A dan B disepakati. API berjalan dengan stub mesin AI. FE tersambung ke API dengan jalur cadangan. Deploy `veritas` di Vercel. |
| **Bonus besok** | Mesin AI nyata untuk tiga pemeriksaan termudah, supaya momen juri (PRD bagian 17 no. 7) jalan. |
| **Setelah lomba** | Sisa pemeriksaan, uji metrik PRD bagian 13, uji beban, privasi dan peran. |

Di luar lingkup: melatih model dari nol, memakai LLM untuk memutuskan label, blockchain, integrasi JKN Drive/PANDAWA produksi.

## 2. Arsitektur

```
FE (Vercel, statis)
   │  /api/*  (rewrite Vercel → API, tanpa CORS)
   ▼
API FastAPI ──── Postgres-backed job queue ──── Worker (proses sama atau terpisah)
   │                                                  │
   │  Supabase: Postgres, Storage, Auth                │  Kontrak B
   ▼                                                  ▼
 DB / file                                  Mesin AI PRAMANA (container, tanpa state)
```

| Komponen | Pilihan | Alasan |
|---|---|---|
| FE | Tetap statis di Vercel | Sudah jadi dan teruji |
| API | FastAPI (Python), satu container | Satu bahasa dengan mesin AI, OpenAPI otomatis di `/docs` untuk Zahra |
| Antrean | Tabel `job` di Postgres, ambil dengan `FOR UPDATE SKIP LOCKED` | Tanpa Redis. Cukup untuk skala uji dan mudah ditambah worker. |
| DB | Supabase Postgres | Sesuai PRD, gratis, sudah ada konektornya |
| File | Supabase Storage (bucket privat, URL bertanda tangan) | Berkas tidak publik |
| Auth | Supabase Auth, peran `verifikator`/`admin` | Memenuhi akses menurut peran (PRD bagian 14) |
| Mesin AI | Container Docker terpisah, endpoint Kontrak B | Berat, tidak cocok di serverless |
| Hosting API + mesin | Railway/Render (container) | Tanpa batas timeout Vercel |

Vercel hanya untuk FE: fungsi serverless tidak cocok untuk OCR dan model gambar (batas ukuran, timeout, tanpa GPU).

### Prinsip desain

1. FE tidak tahu mesin AI ada.
2. Label dihitung di API dengan aturan PRD bagian 9, bukan di mesin AI dan bukan di FE.
3. Mesin AI tanpa state: berkas masuk, sinyal keluar.
4. Asinkron: upload langsung `202 diproses`, FE polling.
5. Gagal aman: gagal diproses menjadi Perlu dicek, tidak pernah Lolos. Scan jelek menjadi Scan ulang.
6. Satu sumber kebenaran enum dan aturan label, dipakai bersama oleh FE, API, dan uji.

## 3. Pembagian kerja

| Siapa | Tanggung jawab |
|---|---|
| **Imelda** | API, DB, antrean, hitung label, keputusan, laporan PDF, sambungan FE, deploy, uji fitur dan beban |
| **Zahra** | Mesin AI (Kontrak B), uji kemampuan AI terhadap metrik PRD bagian 13, review dokumen dataset |
| **Bersama** | Menyepakati Kontrak B (koordinat, fingerprint, ambang, template) |
| **Richard** | Pemilik logo/desain Veritas, FE awal. Konfirmasi sebelum mengubah logo. |

## 4. Rencana kerja

### Fase 0: sepakati kontrak (malam ini, ±1 jam)
- [ ] Kirim `api-contract.md` ke Zahra, tinjau bersama.
- [ ] Putuskan lima hal terbuka di bagian akhir kontrak (DPI, template, fingerprint, prioritas fitur, hosting).
- [ ] Bekukan Kontrak B versi `v1`. Setelah itu hanya boleh menambah field.

### Fase 1: kerangka API (malam ini, ±3 jam)
Struktur folder usulan:

```
backend/
  app/
    main.py            # FastAPI, rute /api/v1
    config.py          # URL mesin, kunci, Supabase
    db.py              # koneksi, model
    label.py           # hitungLabel (port dari data.js) + uji
    mesin.py           # klien Kontrak B + fallback stub
    worker.py          # ambil job, panggil mesin, simpan hasil
    rute/              # berkas, keputusan, konfirmasi, laporan, ringkasan, kesehatan
  stub_mesin/          # pelayan Kontrak B dari dataset/manifest.json
  tests/               # uji label (17 berkas), uji kontrak
  Dockerfile
  docker-compose.yml   # api + stub + postgres lokal
```

- [ ] Skema Supabase (6 tabel di kontrak) + migrasi.
- [ ] `label.py`: port `hitungLabel`, uji terhadap `label_diharapkan` 17 berkas. Ini uji pertama dan harus hijau.
- [ ] `stub_mesin`: menyajikan Kontrak B dari `dataset/manifest.json` berdasarkan nama file. Zahra bisa membuka `/docs` untuk melihat bentuknya.
- [ ] Endpoint: upload, detail, antrean, keputusan, jejak, ringkasan, kesehatan.
- [ ] Worker dengan antrean Postgres.

### Fase 2: sambungkan FE (besok pagi, ±3 jam)
- [ ] `api.js`: satu fungsi `analisis(file, faskes)` yang memakai API bila `/kesehatan` ok, jatuh ke `manifest.js` bila tidak.
- [ ] Tampilan status `diproses` dan `gagal` yang asli untuk berkas luar dataset (ganti animasi simulasi).
- [ ] Berkas pembanding untuk semua jenis temuan, bukan hanya kembar/tempelan.
- [ ] `vercel.json` rewrite `/api/*` ke URL API.
- [ ] Laporan PDF dari server (`/laporan`), bukan cetak browser.

### Fase 3: deploy (besok siang, ±1 jam)
- [ ] Project Vercel `veritas` dari repo ini.
- [ ] Container API + stub di Railway/Render, variabel lingkungan Supabase.
- [ ] Hangatkan layanan sebelum tampil (container gratis bisa tidur).
- [ ] Ganti URL di `README.md` dan `TARGET_URL` uji.

### Fase 4: mesin AI nyata (paralel, Zahra)
Urutan prioritas, dari yang paling mungkin selesai:

| # | Fitur | Teknik | Alasan didahulukan |
|---|---|---|---|
| 1 | Baca jumlah sesi (F3, F4) | OCR + template kolom | Menentukan kecocokan klaim, temuan paling kuat dan mudah dijelaskan |
| 2 | Copy-paste tanda tangan (F6) | Potong per template, SSIM/korelasi | Inti momen juri |
| 3 | Berkas kembar (F5) | pHash + simhash teks, identitas ditutup | Inti demo kedua |
| 4 | Kualitas scan (F2) | OpenCV: ketajaman, miring, terpotong | Mencegah salah tangkap |
| 5 | Metadata (F7 sebagian) | exiftool, pypdf | Murah, sinyal lemah |
| 6 | Suntingan, tanda AI (F7) | ELA, TruFor, detektor AI | Paling berat, hasil dilaporkan apa adanya |

Setiap fitur yang selesai langsung menggantikan padanannya di stub tanpa mengubah FE atau API.

### Fase 5: pengujian

**Fitur**
- Uji alur `tests/alur.test.js` (Playwright) terhadap URL deploy.
- Uji label: 17 berkas, label hitungan = label diharapkan.
- Uji kontrak: respons API divalidasi terhadap skema (OpenAPI/pydantic), respons mesin divalidasi terhadap Kontrak B.
- Uji gagal aman: file rusak, PDF kosong, ukuran > 10 MB, tipe salah, mesin mati → tidak pernah `lolos`.
- Uji peran: verifikator lain tidak melihat berkas cabang lain.

**Kemampuan AI** (Zahra, buta terhadap label, PRD bagian 13)

| Metrik | Target |
|---|---|
| Berkas kembar tertangkap | ≥ 95% |
| Tempelan tertangkap | ≥ 90% |
| Angka/teks disunting tertangkap | ≥ 70% |
| Jumlah sesi terbaca benar | ≥ 95% |
| Berkas asli salah jadi Prioritas | ≤ 5% |
| Berkas asli jelek jadi Prioritas | 0 |

**Skalabilitas** (usulan angka, sesuaikan)

| Skenario | Target |
|---|---|
| 1 berkas, 1 halaman, CPU biasa | < 10 detik (PRD) |
| 50 unggahan hampir bersamaan | Semua `selesai` tanpa galat, antrean tidak hilang saat restart |
| Antrean 1.000 berkas | Daftar `GET /berkas` < 500 ms dengan filter dan halaman |
| Pencarian kembar di 5.000 sidik jari | < 2 detik |
| Menambah worker dari 1 ke 3 | Waktu total turun mendekati linear |

Alat: `locust` atau `k6` untuk beban, data uji dari dataset yang digandakan dengan variasi.

## 5. Risiko

| Risiko | Mitigasi |
|---|---|
| Mesin AI belum jadi besok | Stub menyajikan Kontrak B. FE dan API tidak berubah saat mesin nyata masuk. |
| Mesin atau API mati saat demo | `/kesehatan` memicu jalur cadangan ke data manifest. Siapkan rekaman video demo. |
| Container gratis tidur | Hangatkan 5 menit sebelum tampil, atau pakai layanan berbayar kecil untuk hari-H. |
| Koordinat sorotan meleset | Satu ukuran JPG ternormalisasi (`[1240, 1754]`), disepakati tertulis di kontrak. |
| Berkas juri berisi data nyata | Banner "seluruh data sintetis", batas ukuran dan tipe, bersihkan otomatis tiap sesi. |
| Kontrak berubah di tengah jalan | Versi `/v1`, hanya boleh menambah field. Perubahan merusak = `/v2`. |
| Scope membengkak | Fase 1–3 hanya butuh stub. Fase 4 tidak menghalangi demo. |

## 6. Keputusan terbuka

1. Hosting API + mesin: Railway atau Render? Zahra punya preferensi?
2. Template letak kolom: satu format dulu (rumah sakit percontohan) atau tiga?
3. Ambang kembar awal: 0.90 oke?
4. Demo juri: berkas hasil foto HP juga harus Lolos, atau cukup hasil pindai?
5. Siapa yang mengurus akun Supabase dan Vercel (satu akun bersama)?

## 7. Definisi selesai untuk besok

- [ ] Zahra dan Imelda sama-sama menyetujui `api-contract.md` v1.
- [ ] `https://veritas.vercel.app` bisa dibuka dan demo lima berkas berjalan lewat API.
- [ ] API mati → demo tetap jalan lewat jalur cadangan.
- [ ] Label 17 berkas sesuai ground truth, diuji otomatis.
- [ ] Uji alur Playwright hijau terhadap URL deploy.
- [ ] README dan URL terbarui.
