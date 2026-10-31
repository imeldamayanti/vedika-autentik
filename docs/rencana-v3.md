# Rencana v3 Vedika Autentik: konfirmasi suara

Acuan: [prd-v3-konfirmasi-suara.md](prd-v3-konfirmasi-suara.md). Wireframe: [prd-v3/](prd-v3/).
PIC seluruh tiket di dokumen ini: Imelda, kecuali disebut lain.

## Prinsip

- Fokus pertama: prototipe website v3 sampai jadi dan stabil. Video demo paling akhir.
- Tetap di shell VEDIKA (sidebar, header verifikator, banner). Menu Autentik dan mark Veritas tetap; PRD tidak menyebut Veritas.
- v2 tidak dihapus dan tidak disentuh. File v3 terpisah: `app-v3.js`, `data-v3.js`, `app-v3.css` (menumpang `app.css`). `index.html` memuat v3, `v2.html` memuat v2 apa adanya. Ganti root = tukar isi `index.html`.
- Tampilan hi-fi langsung di web, perilaku UI mengikuti v2 (chip label, kartu angka, tabel bisa diklik, toast, localStorage). Wireframe hanya acuan tata letak.
- Data demo (data contoh untuk website) ditulis tangan di `data-v3.js`, bukan dihitung dari dataset. Label per skenario ditulis langsung.
- Semua layar berlabel "Simulasi" (R5.6). Tidak ada logo resmi BPJS sebagai penelepon.
- Uji di lokal dulu, deploy belakangan.

## Branch

| Branch | Isi | Dicabang dari | Merge ke |
|---|---|---|---|
| `v3-ui-konfirmasi` | Bagian A | `feat/konfirmasi-suara` | `feat/konfirmasi-suara` |
| `v3-db-konfirmasi` | Bagian B, paralel dengan A | `feat/konfirmasi-suara` | `feat/konfirmasi-suara` |
| `v3-kontrak-api` | Bagian C, setelah B | `feat/konfirmasi-suara` | `feat/konfirmasi-suara` |
| `v3-api-konfirmasi` | Bagian D, setelah C | `feat/konfirmasi-suara` | `feat/konfirmasi-suara` |

`main` tetap v2.

## Urutan

```
A. UI (v3-ui-konfirmasi)  ─┐
B. DB (v3-db-konfirmasi)  ─┴─> C. Kontrak ─> D. Endpoint + sambung FE (dummy agen/pembaca) ─> F. Akhir (retensi, deploy, video)
SR. Suara ElevenLabs (v3-ui-konfirmasi, kapan saja sebelum D-06)
E. Uji S1–S8 sungguhan: ditunda sampai bagian Zahra siap
```

---

## A. UI (`v3-ui-konfirmasi`)

### UI-01 Kerangka v3

- `index.html` memuat `data-v3.js`, `app-v3.js`, `app.css` + `app-v3.css`. `v2.html` = salinan `index.html` lama (memuat `data.js`, `api.js`, `app.js`).
- Shell sama dengan v2: merek VEDIKA, header verifikator, sidebar. Menu Autentik punya sub-menu: Antrean konfirmasi, Ringkasan RS.
- Rute: `#/beranda`, `#/autentik` (antrean), `#/panggilan/:id`, `#/kartu/:id`, `#/ringkasan-rs`, `#/riwayat`.
- Lencana "Simulasi" terlihat di header semua layar.
- Panduan demo/tur v2 tidak dibawa.

Kriteria terima: `index.html` membuka v3 tanpa galat konsol; `v2.html` tetap berjalan seperti sebelumnya; semua rute bisa dibuka dari sidebar atau tautan.

### UI-02 Data demo (`data-v3.js`)

Ditulis tangan, angka mengikuti PRD dan `data-uji-konfirmasi` supaya cerita konsisten:

- Verifikator: pakai verifikator v2 yang sudah ada.
- 5 RS: RS Melati Sehat, RSU Bakti Mulia, RS Cempaka Asri, RSU Nusa Sejahtera, RS Kenanga Medika, dengan pasien aktif dan terpicu (RS Melati 39,7%, RS lain 0–1,8%).
- Antrean ±12 baris: S1, S2, S3, S4, S5, S6, S8 (S7 tidak masuk), 4 riwayat berstatus Selesai, beberapa baris Antre. Per baris: pasien, umur, RS, sesi ditagih, indikator aktif (I1–I4), penerima (Peserta / nama + hubungan), status.
- Per skenario: daftar tanggal sesi ditagih (tandai Minggu/libur), tanggal libur, jawaban hasil pembaca (skema README data uji), label, langkah yang disarankan, kutipan kunci, transkrip bertanda waktu (salin dari `data-uji-konfirmasi/transkrip_uji/S*.txt`).
- Ringkasan RS dua keadaan: sebelum S1 (RS Melati Normal, 2 tidak sesuai dari 4 terjawab) dan sesudah S1 (Perlu klarifikasi RS, 3 dari 5).
- Teks WA Lampiran B (pemberitahuan dan chat cadangan) dengan placeholder terisi.

Kriteria terima: S1 = 11 ditagih, 3 versi peserta, selisih 8, label Tidak sesuai; label S1–S8 sama dengan tabel skenario PRD.

### UI-03 Antrean konfirmasi (Gambar 4, R1.4, R1.5)

- Judul "Antrean konfirmasi · layanan Agustus 2026" dan keterangan pemicu (≥2 indikator, jam 09.00–17.00).
- 4 kartu angka: pasien terpicu dari 300 aktif, sudah ditelepon, tidak sesuai, RS perlu klarifikasi.
- Filter RS dan status.
- Tombol "Panggilan otomatis: AKTIF/NONAKTIF" dan "Jeda".
- Tabel: pasien + umur, RS, sesi ditagih, chip indikator (Melebihi 8, 3x seminggu, 6 bulan, Libur), penerima telepon, status (Antre, WA terkirim, Menelepon, Selesai, Tidak terhubung), tombol Lihat.
- Baris berstatus Selesai membuka Kartu bukti; baris sedang berjalan membuka Panggilan; baris Antre non-skenario menampilkan "Belum ditelepon".

Kriteria terima: mengaktifkan mode otomatis memulai S1 tanpa klik tambahan; status baris berubah mengikuti simulasi.

### UI-04 Panggilan berlangsung + simulasi (Gambar 5, R5.1, R3.7)

- Kepala: pasien, RS, bulan, sesi ditagih, indikator, tanggal libur.
- Kolom Progres: Pesan WA terkirim → Panggilan tersambung → Merekam → Membaca jawaban → Kartu bukti, dengan jam.
- Kolom Transkrip langsung: baris AI dan penerima muncul bertahap sesuai cap waktu.
- Kolom Yang ditangkap AI: penerima, hadir, jumlah sesi, keyakinan, tanggal libur, tanda bahaya; terisi bertahap.
- Durasi dipadatkan ±45 detik. Pintasan keyboard tersembunyi untuk lompat ke akhir.
- Selesai → otomatis pindah ke Kartu bukti.
- S2 bisa dijalankan dari barisnya (tombol "Telepon sekarang").
- S5: dua percobaan gagal → status Tidak terhubung, tampilkan chat cadangan (UI-05).

Kriteria terima: S1 berjalan dari Antre sampai Kartu bukti tanpa muat ulang; lompat ke akhir menghasilkan keadaan akhir yang sama.

### UI-05 Mockup WA (F2, Lampiran B)

- Pakai ulang komponen ponsel WA dari v2.
- Saat status WA terkirim: tampilkan pesan pemberitahuan Lampiran B (panel samping atau modal sebentar).
- S5: tampilkan chat cadangan dengan pilihan 1–6.
- Pengiriman `wa.me` sungguhan tidak di sini (lihat F).

Kriteria terima: teks pesan sama dengan Lampiran B; tidak berisi tautan.

### UI-06 Kartu bukti (Gambar 6, R5.2, R5.6)

- Kepala: pasien, RS, layanan, waktu panggilan, durasi, penerima; chip label (Tidak sesuai, Sesuai, Tidak yakin, Tidak terhubung, Menolak).
- 3 kartu: Ditagih rumah sakit (daftar tanggal, Minggu/libur ditandai), Versi peserta (dan bantahan tanggal libur), Selisih (toleransi salah ingat 2 sesi).
- Kutipan kunci, pemutar rekaman (audio placeholder di `assets/rekaman/`), tautan transkrip lengkap.
- Langkah yang disarankan sesuai tabel label PRD, plus konteks RS ("RS ini 3 jawaban tidak sesuai dari 5 terjawab").
- Tanda bahaya tampil untuk S2 (tanda tangan tanpa layanan).
- Catatan: rekaman disimpan terenkripsi sampai klarifikasi; identitas penerima tidak dibagikan ke RS.

Kriteria terima: kartu S1 menampilkan 11 vs 3, selisih 8, Tidak sesuai, saran Minta klarifikasi RS.

### UI-07 Keputusan (R5.3)

- "Setujui saran" atau "Pilih tindakan lain": Tutup kasus, Minta klarifikasi RS, Teruskan ke Tim PK-JKN.
- Tindakan lain wajib alasan; tombol simpan mati tanpa alasan.
- Simpan siapa, kapan, apa, alasan di localStorage. Toast setelah simpan.

Kriteria terima: tindakan lain tanpa alasan tidak bisa disimpan; keputusan muncul di Riwayat.

### UI-08 Ringkasan RS (Gambar 7, R5.4)

- Tabel: RS, pasien aktif, terpicu (%), terjawab, tidak sesuai, status (Normal / Perlu klarifikasi RS), tombol Lihat kartu.
- Keterangan aturan: satu jawaban belum cukup; Perlu klarifikasi jika ≥3 jawaban tidak sesuai DAN ≥10% dari terjawab; Tidak yakin, Tidak terhubung, Menolak tidak dihitung.
- Keadaan berganti dari "sebelum S1" ke "sesudah S1" setelah S1 selesai.

Kriteria terima: RS Melati Normal (2/4) sebelum S1 dan Perlu klarifikasi RS (3/5) sesudah S1; RS lain tetap Normal.

### UI-09 Beranda v3

- Banner dan foto v2 tetap.
- Kartu angka v2 diganti angka v3 (pasien terpicu, sudah ditelepon, tidak sesuai, RS perlu klarifikasi) dan tautan ke Antrean dan Ringkasan RS.

### UI-10 Riwayat keputusan v3

- Pakai ulang tata letak Riwayat v2 untuk keputusan panggilan: waktu, pasien, RS, label, tindakan, ikut saran atau tidak, alasan, verifikator.

### UI-11 Mulai ulang demo

- Tombol di sidebar seperti v2: kosongkan state v3 di localStorage, kembalikan antrean dan ringkasan RS ke keadaan awal.

Kriteria terima: setelah S1 dan keputusan, mulai ulang mengembalikan RS Melati ke Normal dan S1 ke Antre.

---

## B. DB (`v3-db-konfirmasi`)

Kondisi awal (31 Okt): Supabase sudah di-restore dan bisa diakses; isinya hanya tabel v2 (`berkas`, `hasil_cek`, `label`, `konfirmasi`, `keputusan`, `akses_log`, `job`), belum ada bucket storage. Draft `backend/db/schema_v3.sql` dan `backend/scripts/seed_v3.py` ada di working tree, belum di-commit (seed `--dry-run` lolos).

Keputusan:

- Tabel v3 ditambahkan di database yang sama; tabel v2 tidak disentuh.
- Aturan label dan status RS dihitung di Python dengan `data-uji-konfirmasi/tools/aturan.py`, bukan view SQL. DB hanya menyimpan hasil.
- Rekaman disimpan di disk lokal lewat `Penyimpanan` (`backend/uploads/rekaman/`). `rekaman_path` relatif. Pindah ke bucket privat Supabase `rekaman` di bagian F.
- Tidak ada `psql`/Docker di laptop; skema diterapkan lewat skrip psycopg.

### DB-01 Skema v3 idempoten (`backend/db/schema_v3.sql`)

- Semua `create table` / `create index` memakai `if not exists`; `insert` pengaturan tetap `on conflict do nothing`.
- Tambah kolom di `panggilan`:
  - `no_tujuan text`: nomor yang ditelepon (prototipe: `NOMOR_PENGUJI` dari `.env`).
  - `chat_cadangan_terkirim boolean not null default false`, `jawaban_chat text`: R3.5, S5.
  - `galat_pembaca text`: R4.3, JSON pembaca tidak valid.
  - `klarifikasi_selesai_pada timestamptz`: pemicu hapus label Tidak sesuai (R5.5).
  - `coba_lagi_setelah timestamptz`: percobaan ke-2 baru boleh diambil agen setelah waktu ini (R3.5).
  - `prioritas boolean not null default false`: "Telepon sekarang", diambil agen walau mode otomatis mati (R1.5).
- Tambah tabel `panggilan_log` (id identity, `panggilan_id` FK cascade, `status` dengan check enum yang sama dengan `panggilan.status`, `waktu timestamptz default now()`, `percobaan int`, `catatan text`) + index (`panggilan_id`, `waktu`). Dipakai untuk R2.2 (jeda WA tercatat), R3.5 (percobaan), R3.7 (status bertahap, jam di layar Panggilan).
- RLS aktif tanpa policy untuk tabel baru (sama dengan tabel v3 lain).

Kriteria terima: file bisa dijalankan dua kali berturut-turut tanpa galat.

### DB-02 Seed v3 (`backend/scripts/seed_v3.py`)

- Tetap mengisi: 5 RS, 408 peserta, 4.913 klaim, libur, 300 indikator Agustus (via `aturan.py`), 4 panggilan riwayat (`sumber = sintetis-riwayat`, status `selesai`).
- Tambah: baris `panggilan` berstatus `antre` untuk setiap pasien `dipicu` yang belum punya riwayat (30 − 4 = 26). Isi `penerima`, `nama_penerima`, `hubungan` sesuai R1.3 (`hubungi_keluarga` → keluarga, selain itu peserta), `sesi_ditagih` dari indikator. ID mudah dibaca (mis. `CALL-<id_peserta>-2026-08`).
- `--reset`: truncate tabel v3 (termasuk `panggilan_log`), lalu isi ulang → keadaan awal demo (4 Selesai, 26 Antre, keputusan dan log kosong). Dipakai nanti oleh "Mulai ulang demo" saat FE tersambung ke API.
- `kunci_kebenaran_2026-08.csv` tetap tidak dibaca.
- Pisahkan fungsi konversi (baris CSV → tuple, penentuan penerima, `hapus_pada`) dari I/O supaya bisa diuji tanpa DB.

Kriteria terima: `--dry-run` mencetak 26 baris antre baru; S7 (Rina Marlina) tidak menghasilkan baris panggilan.

### DB-03 Skrip terapkan (`backend/scripts/terapkan_v3.py`)

- Baca `backend/db/schema_v3.sql`, jalankan dalam satu transaksi lewat psycopg (`DATABASE_URL` dari `backend/.env`), lalu panggil seed.
- Opsi `--reset` diteruskan ke seed; `--skema-saja` untuk menerapkan skema tanpa seed.
- Galat koneksi dicetak satu baris yang jelas (contoh: "DATABASE_URL salah atau project Supabase di-pause").

### DB-04 Verifikasi (`backend/scripts/cek_v3.py` + pytest)

`cek_v3.py` (read-only) mencetak LULUS/GAGAL per butir:

- Jumlah: 5 RS, 408 peserta, 4.913 klaim, 300 indikator Agustus, 30 dipicu, 30 baris panggilan (4 `selesai`, 26 `antre`).
- S7 tidak ada di `panggilan`; S1–S6 dan S8 ada berstatus `antre` dengan penerima benar (S2, S4 keluarga; S1 peserta).
- Ringkasan RS awal (dihitung dengan `aturan.py` dari isi DB) sama dengan `expected_ringkasan_rs.json` bagian sebelum skenario: RS Melati Normal, 2 tidak sesuai dari 4 terjawab; persen dipicu per RS sama.

Pytest (`backend/tests/test_seed_v3.py`, tanpa DB): konversi peserta/klaim, penentuan penerima R1.3, `hapus_pada` per label, pembentukan baris antre.

Kriteria terima: `pytest` hijau; `cek_v3.py` semua LULUS setelah DB-05.

### DB-05 Penerapan (Imelda)

1. `cd backend && .venv/bin/python -m scripts.terapkan_v3 --reset`
2. `.venv/bin/python -m scripts.cek_v3` → semua LULUS.
3. Commit di `v3-db-konfirmasi` (tanpa `.env`, `.pptx`, `videos/`, `backend/uploads/`).

---

## C. Kontrak API v3 (`v3-kontrak-api`)

Dikerjakan setelah B selesai dan UI-02 (`data-v3.js`) ada. Hasil: file baru `docs/api-contract-v3.md`. `docs/api-contract.md` (v2) tidak disentuh.

### Keputusan

- PRD/kontrak v3 jadi acuan. Bila stack beda, backend menyesuaikan kebutuhan Zahra: kode backend tetap jalan di Python 3.12, header antar layanan `X-Kunci-Layanan`.
- Path tetap `/api/v1` dan `/v1` (endpoint v3 tidak bentrok dengan `/berkas` v2).
- Konvensi v2 disalin: field `snake_case` bahasa Indonesia, waktu ISO 8601 dengan zona, galat `{"galat": {"kode", "pesan"}}`, penerima mengabaikan field tak dikenal.
- Enum memakai nilai DB dan `aturan.py` apa adanya. Status: `antre`, `wa_terkirim`, `menelepon`, `tersambung`, `merekam`, `membaca_jawaban`, `selesai`, `tidak_terhubung`. Label: `Sesuai`, `Tidak sesuai`, `Tidak yakin`, `Tidak terhubung`, `Menolak`. Tindakan: `tutup_kasus`, `minta_klarifikasi_rs`, `teruskan_pk_jkn`.
- Label dan status RS hanya dihitung di API (`tools/aturan.py`). Agen dan pembaca tidak pernah mengirim label.
- Bentuk objek Kontrak A = bentuk di `data-v3.js`, supaya sambung FE cukup mengganti sumber data. API yang menyesuaikan dari bentuk DB.
- Real-time = FE polling 1 detik. Tanpa SSE/WebSocket.
- Autentikasi prototipe: FE tanpa login; endpoint agen dan hasil wajib `X-Kunci-Agen`; API → pembaca memakai `X-Kunci-Layanan`. Ditandai "produksi: login Supabase dan token per perangkat".
- Mode otomatis dikendalikan verifikator (tombol AKTIF/Jeda di FE). Agen hanya menarik tugas; API memberi tugas jika mode AKTIF (atau ada permintaan "Telepon sekarang"), jam 09.00–17.00, dan tidak ada panggilan aktif lain.
- Aturan percobaan (R3.5) dan jeda (R2.2) diputuskan API, bukan agen.
- Pembaca jawaban dipanggil API (bukan agen), sebagai endpoint baru `/v1/baca` di `ai-service` Zahra.
- Halaman agen berjalan di origin sendiri (mis. `http://localhost:5173`); origin itu masuk `CORS_ORIGINS`.
- Skema JSON pembaca mengacu ke `data-uji-konfirmasi/README.md`, tidak ditulis ulang.
- Kontrak A memakai kode `data-v3.js`: label `tidak_sesuai`, `sesuai`, `tidak_yakin`, `tidak_terhubung`, `menolak`; tindakan `pantau`, `tutup`, `klarifikasi`, `teruskan`. API memetakan ke nilai DB. (Menggantikan butir "enum memakai nilai DB" untuk label dan tindakan.)
- Transkrip di semua kontrak dan DB: objek `{detik, pembicara: "ai"|"penerima", teks}`. Tanggal sesi: ISO (`2026-08-16`) + `tanda_tanggal`. FE memakai adaptor kecil.
- `tidak_diangkat` dan `chat_cadangan_terkirim` tidak menambah nilai status DB: dicatat lewat `catatan` di `panggilan_log` dan kolom `chat_cadangan_terkirim`.
- Perubahan skema untuk bagian D: `keputusan_panggilan.tindakan` mengizinkan `pantau`; kolom `panggilan.diambil_pada` untuk kunci ambil agen (lepas setelah 5 menit).
- Hasil: `docs/api-contract-v3.md` di branch `v3-kontrak-api` (worktree `../pramana-v3-kontrak`).

### Kontrak A: FE ↔ API (`/api/v1`)

| Endpoint | Fungsi | Requirement |
|---|---|---|
| `GET /antrean?bulan=&id_rs=&status=` | Kartu angka + baris antrean (pasien, umur, RS, sesi ditagih, indikator, penerima, status) | R1.3, R1.4 |
| `GET /panggilan/{id}` | Detail panggilan: kepala, log status bertanda waktu, transkrip terkini, `tangkapan_sementara` (opsional), jawaban, label, saran, tanggal sesi (Minggu/libur ditandai), selisih, rekaman, konteks RS, keputusan. Dipakai layar Panggilan (polling 1 detik) dan Kartu bukti | R3.7, R5.1, R5.2 |
| `GET /panggilan/{id}/rekaman` | Audio rekaman (stream) | R3.4, R5.2 |
| `POST /panggilan/{id}/mulai` | "Telepon sekarang": tandai prioritas, diambil agen di giliran berikutnya walau mode otomatis mati | R1.5 |
| `POST /panggilan/{id}/keputusan` | `{ikut_saran, tindakan, alasan}`. Alasan wajib bila `ikut_saran=false` → `422 alasan_wajib` | R5.3 |
| `GET /ringkasan-rs?bulan=` | Per RS: pasien aktif, terpicu (%), terjawab, tidak sesuai, status | R5.4 |
| `GET /keputusan` | Riwayat keputusan | R5.3 |
| `GET /pengaturan`, `PUT /pengaturan` | `mode_otomatis`, `jam_mulai`, `jam_selesai`, `jeda_wa_menit`, `jeda_percobaan_menit` | R1.5, R2.2 |
| `POST /demo/reset` | Kembalikan panggilan, log, keputusan ke keadaan awal (logika `seed_v3 --reset`, data master tidak disentuh) | UI-11 |
| `GET /kesehatan` | API, DB, pembaca ok/tidak | — |

### Kontrak B1: agen suara ↔ API (`/api/v1`, header `X-Kunci-Agen`)

| Endpoint | Fungsi | Requirement |
|---|---|---|
| `POST /agen/ambil` | `200` tugas berikutnya atau `204` bila tidak ada. Isi tugas: id panggilan, percobaan ke-, `no_tujuan`, data skrip (nama penerima, hubungan, nama pasien, RS, bulan, tanggal libur), teks WA Lampiran B terisi + tautan `wa.me`, `jeda_wa_menit` | R1.5, R2.1–R2.3, R3.1 |
| `POST /panggilan/{id}/status` | `{status, waktu, catatan}`; status: `wa_terkirim`, `menelepon`, `tersambung`, `merekam`, `tidak_diangkat`, `chat_cadangan_terkirim`. API menulis `panggilan_log` | R2.2, R3.7 |
| `POST /panggilan/{id}/transkrip` | Tambah baris transkrip selama panggilan `[{waktu, pembicara, teks}]`; opsional `tangkapan_sementara` | R3.7, R5.1 |
| `POST /panggilan/{id}/hasil` | Multipart: `rekaman` (.webm) + `transkrip` final. `202`, status `membaca_jawaban`; API memanggil pembaca di latar, menghitung label + `hapus_pada`, lalu `selesai` | R3.4, R4.4, R5.5 |

Aturan `tidak_diangkat` (diputuskan API): percobaan ke-1 → kembali `antre` dengan `coba_lagi_setelah` = sekarang + `jeda_percobaan_menit`; percobaan ke-2 → `tidak_terhubung`, label `Tidak terhubung`, balasan berisi teks chat cadangan Lampiran B + tautan `wa.me`.

### Kontrak B2: API ↔ pembaca jawaban (`ai-service`, `/v1`, header `X-Kunci-Layanan`)

| Endpoint | Fungsi | Requirement |
|---|---|---|
| `POST /v1/baca` | Body `{transkrip, konteks: {sesi_ditagih, tanggal_libur, nama_pasien, bulan}}`. Balasan = JSON skema README data uji | R4.1, R4.2 |

Batas waktu 30 detik. JSON tidak valid atau galat → API ulang 1 kali; tetap gagal → label `Tidak yakin`, galat disimpan di `galat_pembaca` (R4.3).

### Isi `docs/api-contract-v3.md`

1. Diagram tiga sambungan (FE, agen, pembaca) dan pemilik tiap kontrak.
2. Prinsip dan konvensi (dari keputusan di atas).
3. Enum.
4. Kontrak A, B1, B2: per endpoint contoh request/response JSON, kode galat, requirement PRD yang dipenuhi. Contoh memakai data S1 (11 ditagih, 3 versi peserta).
5. Alur ujung ke ujung S1: verifikator AKTIF → agen ambil → WA → telepon → transkrip → hasil → pembaca → label → kartu bukti → keputusan → ringkasan RS.
6. Alur S5 (tidak diangkat 2x → chat cadangan) dan S8 (menolak).
7. Tabel pemetaan field kontrak ↔ kolom DB (`schema_v3.sql`). Catatan: `coba_lagi_setelah` dan penanda prioritas "Telepon sekarang" belum ada di skema; tambahkan ke DB-01 bila B belum selesai, atau sebagai migrasi kecil di D.
8. Mode cadangan: pembaca mati → `Tidak yakin`, demo tetap jalan.
9. "Yang perlu disepakati dengan Zahra": ditulis saat push.

Kriteria terima: setiap requirement PIC I dan Z+I di PRD bagian 7 punya endpoint atau aturan di kontrak; setiap field di `data-v3.js` punya sumber di Kontrak A; contoh JSON valid.

### Tiket

| Tiket | Isi | Status |
|---|---|---|
| KT-01 | Prinsip, konvensi, enum, objek bersama (transkrip, jawaban pembaca) | Selesai (`957db66`) |
| KT-02 | Kontrak A: 10 endpoint FE ↔ API dengan contoh S1 | Selesai (`957db66`) |
| KT-03 | Kontrak B1: `agen/ambil`, `status`, `transkrip`, `hasil`, aturan percobaan dan chat cadangan | Selesai (`957db66`) |
| KT-04 | Kontrak B2: `/v1/baca`, batas waktu, ulang, gagal aman | Selesai (`957db66`) |
| KT-05 | Alur S1/S5/S8, pemetaan kontrak ↔ DB, mode cadangan, jejak requirement | Selesai (`957db66`) |
| KT-06 | Review silang: setiap field yang dipakai `app-v3.js`/`data-v3.js` punya sumber di Kontrak A (mis. `waktu` panggilan di kepala Kartu bukti, nama tampilan indikator/label/tindakan, teks retensi, `TIDAK_DIPICU`); setiap kolom kontrak punya sumber di `schema_v3.sql` branch `v3-db-konfirmasi`; setiap `perilaku_ai_wajib` di `skenario_uji.json` yang butuh data dari API tercakup di `skrip`. Tambal celah di kontrak | Belum |
| KT-07 | "Yang perlu disepakati dengan Zahra" | Saat push |

---

## Prinsip D–F: jalan tanpa menunggu Zahra

Bagian milik Zahra (agen suara asli, pembaca jawaban LLM, jalur audio BlackHole) diganti dummy dulu, seperti `backend/stub_mesin` di v2. Seluruh alur bisa didemokan di lokal hanya dengan backend Imelda. Saat bagian Zahra siap, cukup ganti alamat di `.env` dan jalankan agen asli sebagai pengganti stub. Yang harus dikerjakan dan disambung Zahra ditulis di [serah-terima-zahra.md](serah-terima-zahra.md).

---

## SR. Suara rekaman ElevenLabs (`v3-ui-konfirmasi`)

Mengganti placeholder 4 detik (`assets/rekaman/S1/S2/S3/S6.wav`) dengan percakapan bersuara dari transkrip, supaya layar Panggilan dan Kartu bukti terdengar seperti panggilan sungguhan. Bisa dikerjakan sekarang, terpisah dari D.

Keputusan:

- Hanya skenario yang ada percakapannya: S1, S2, S3, S4, S6, S8. S5 (tidak diangkat) dan riwayat R1–R4 (tanpa transkrip) tidak.
- S4 dan S8 hanya diputar di layar Panggilan. Kartu bukti tetap tanpa pemutar untuk Tidak yakin dan Menolak (R5.5).
- Tiga suara dari akun ElevenLabs, model `eleven_multilingual_v2`:
  - AI: Arunika (`o5s6XRBkPSTD4syv6mZg`), wanita, bahasa Indonesia, profesional.
  - Penerima wanita (Dewi): Velora (`TrU3igk19A4aIUi2GAA2`), wanita, bahasa Indonesia, santai.
  - Penerima pria (Andi, Budi, Bayu, Slamet, Hendra): Chris (`iP95p4xoKVk53GoZ742B`), pria, santai. Akun belum punya suara pria Indonesia, jadi logat bisa kurang lokal; bisa diganti nanti lewat env tanpa ubah kode.
- Panjang audio asli menentukan `detik` tiap baris transkrip; durasi simulasi ikut panjang rekaman.
- Filter suara telepon ringan (ffmpeg `highpass=f=300,lowpass=f=3400`) untuk AI dan penerima.
- Kunci dan ID suara dibaca dari `backend/.env`, tidak pernah ditulis ke file atau log.

Env (`backend/.env`, sudah ada `ELEVENLABS_API_KEY`):

```
ELEVENLABS_VOICE_AI=o5s6XRBkPSTD4syv6mZg
ELEVENLABS_VOICE_WANITA=TrU3igk19A4aIUi2GAA2
ELEVENLABS_VOICE_PRIA=iP95p4xoKVk53GoZ742B
```

### SR-01 Skrip pembuat suara (`tools/suara/buat_rekaman.py`)

- Baca transkrip S1, S2, S3, S4, S6, S8 dari `data-v3.js` (pembicara `A` = AI, `P` = penerima; suara penerima dipilih dari jenis kelamin penerima).
- Satu panggilan TTS per baris (pakai pola `videos/v2/tools/gen_vo.py`: endpoint `/with-timestamps`, trim awal-akhir), filter telepon, simpan `assets/rekaman/<S>/<nn>.mp3`.
- Sambung semua baris dengan jeda alami (±0,6 dtk) menjadi `assets/rekaman/<S>.mp3`.
- Tulis `assets/rekaman/waktu.json`: per skenario, `detik` mulai tiap baris dan durasi total.
- Opsi `--skenario S1` untuk membuat ulang satu skenario; baris yang sudah ada tidak dibuat ulang kecuali `--paksa` (hemat kuota).

Kriteria terima: enam `.mp3` utuh + potongan per baris; `waktu.json` cocok dengan durasi file (ffprobe).

### SR-02 Sambungkan ke layar

- `data-v3.js`: `detik` tiap baris dan `durasi` mengikuti `waktu.json`; `rekaman` menunjuk `.mp3`; S4 dan S8 punya `suara_langsung` (untuk layar Panggilan) tetapi `rekaman: null` (Kartu bukti).
- Layar Panggilan: saat baris muncul, putar potongan baris itu; transkrip dan suara berjalan bersama. Tombol bisukan suara. Pintasan lompat ke akhir menghentikan suara.
- Kartu bukti: pemutar memutar rekaman utuh.
- Hapus placeholder `.wav`.
- Perhatikan kebijakan autoplay browser: suara mulai setelah klik verifikator (tombol AKTIF atau Telepon sekarang sudah merupakan klik).

Kriteria terima: S1 dari AKTIF sampai Kartu bukti terdengar utuh dan transkrip pas dengan suara; tidak ada galat konsol; `v2.html` tetap jalan.

---

## D. Endpoint + sambung FE (`v3-api-konfirmasi`)

Dicabang dari `feat/konfirmasi-suara` setelah `v3-ui-konfirmasi`, `v3-db-konfirmasi`, dan `v3-kontrak-api` di-merge ke sana. Acuan utama: `docs/api-contract-v3.md`.

### D-01 Perubahan skema kecil

- `keputusan_panggilan.tindakan` mengizinkan `pantau`.
- Kolom `panggilan.diambil_pada timestamptz` (kunci ambil agen, lepas setelah 5 menit).
- Plus perubahan skema lain yang dicatat KT-06 di kontrak. Tetap idempoten di `schema_v3.sql`; `cek_v3.py` tetap lulus.

### D-02 Endpoint baca untuk FE

`GET /antrean`, `GET /panggilan/{id}`, `GET /ringkasan-rs`, `GET /keputusan`, `GET /pengaturan`, `GET /kesehatan`. Pemetaan DB → kontrak (label `Tidak sesuai` → `tidak_sesuai`, tindakan, transkrip objek, tanggal ISO + tanda). Ringkasan RS dan `konteks_rs` dihitung dengan `aturan.py`.

Kriteria terima: pytest per endpoint; `GET /ringkasan-rs` setelah seed = `expected_ringkasan_rs.json` sebelum skenario; S7 tidak ada di antrean.

### D-03 Endpoint tulis untuk FE

`PUT /pengaturan`, `POST /panggilan/{id}/mulai`, `POST /panggilan/{id}/keputusan` (alasan wajib → `422 alasan_wajib`), `GET /panggilan/{id}/rekaman`, `POST /demo/reset`.

### D-04 Endpoint agen + label

`POST /agen/ambil` (mode otomatis, jam, prioritas, satu panggilan aktif, `coba_lagi_setelah`, kunci `diambil_pada`), `POST …/status` (urutan, jeda WA, aturan `tidak_diangkat` dan chat cadangan), `POST …/transkrip`, `POST …/hasil` (simpan rekaman, panggil pembaca di latar, ulang 1 kali, label via `aturan.py`, `hapus_pada`). Header `X-Kunci-Agen`; origin agen di `CORS_ORIGINS`.

Kriteria terima: pytest untuk tiap aturan (jeda belum lewat, percobaan ke-2, alasan wajib, pembaca gagal → `tidak_yakin`).

### D-05 Stub pembaca (`backend/stub_mesin/`)

Tambah `POST /v1/baca` di stub yang sudah ada: kembalikan `expected_jawaban` dari `skenario_uji.json` berdasarkan `id` panggilan (S1–S8); panggilan lain → jawaban `tidak_yakin` sederhana. Mode `GAGAL=1` untuk menguji jalur gagal aman.

### D-06 Stub agen (`backend/scripts/stub_agen.py`)

Berpura-pura jadi agen Zahra lewat Kontrak B1:

- Loop `agen/ambil` tiap 3 detik.
- Cetak `wa.tautan` (tidak membuka WhatsApp), lapor `wa_terkirim`, tunggu jeda, lapor `menelepon → tersambung → merekam`.
- Kirim transkrip baris demi baris memakai `detik` dari `assets/rekaman/waktu.json` (hasil SR) supaya layar bergerak seirama suara.
- Kirim `hasil` dengan rekaman `assets/rekaman/<S>.mp3` dari SR.
- S5: dua kali `tidak_diangkat`, cetak tautan chat cadangan, lapor `chat_cadangan_terkirim`.
- Opsi `--skenario S1` (sekali jalan) atau tanpa opsi (terus mengambil antrean).

Kriteria terima: dengan API + stub pembaca + stub agen, S1 berjalan dari AKTIF di FE sampai Kartu bukti dan RS Melati menjadi Perlu klarifikasi RS.

### D-07 Klien API di FE (`api-v3.js`)

Klien untuk semua endpoint Kontrak A, adaptor ke bentuk yang dipakai `app-v3.js` (transkrip objek → bentuk lama, tanggal ISO → angka hari), dan cek `GET /kesehatan` di awal.

### D-08 Ganti sumber data layar

- Antrean, Kartu bukti, Ringkasan RS, Riwayat, Beranda membaca API.
- Layar Panggilan: timer simulasi diganti polling `GET /panggilan/{id}` tiap 1 detik; suara diputar dari `rekaman` setelah selesai (suara langsung saat panggilan tetap dari potongan SR selama memakai stub).
- Tombol AKTIF/Jeda, Telepon sekarang, keputusan, Mulai ulang demo memanggil API.
- Jalur cadangan: bila `GET /kesehatan` gagal, FE kembali ke `data-v3.js` dan simulasinya. `data-v3.js` tidak dihapus.

Kriteria terima: alur S1 sama seperti versi simulasi, tetapi data dari DB; matikan API → website tetap jalan dengan simulasi.

### D-09 Cek demo dengan dummy (pengganti E untuk sementara)

Jalankan API + stub pembaca + stub agen, lalu demokan S1, S2, S5, S8 di browser. Bukan uji formal; cukup memastikan demo jalan dan ringkasan RS berubah setelah S1.

### D-10 Serah terima Zahra

Perbarui [serah-terima-zahra.md](serah-terima-zahra.md) supaya sesuai kode yang sudah jalan (alamat, env, cara uji, perilaku stub yang harus ditiru).

---

## E. Uji ujung ke ujung (ditunda)

Uji formal S1–S8 dengan panggilan sungguhan ke HP penguji (Definisi selesai PRD no. 3) baru bisa setelah agen dan pembaca Zahra jalan. Sementara diganti D-09 (demo biasa dengan dummy). Saat bagian Zahra siap: jalankan S1–S8, cocokkan label dengan `skenario_uji.json` dan ringkasan RS dengan `expected_ringkasan_rs.json` setelah S1 dan setelah semua skenario.

---

## F. Akhir

### F-01 Retensi (R5.5)

Skrip/endpoint pembersih: hapus rekaman dan transkrip `sesuai` yang lewat `hapus_pada`; `tidak_sesuai` dihapus setelah `klarifikasi_selesai_pada` terisi; label lain sejak awal hanya status. Kriteria: `hapus_pada` benar per label, rekaman lewat batas tidak bisa diputar.

### F-02 Deploy

Backend + FE ke Railway/Vercel yang sudah ada, rekaman pindah ke bucket privat Supabase `rekaman`, env produksi, CORS. `ai-service` dideploy Zahra.

### F-03 Persiapan video demo

Checklist untuk Richard: urutan klik, reset demo, suara aktif, mode cadangan bila API bermasalah. Paling akhir, setelah prototipe stabil.

Catatan: membuka `wa.me` dan menekan kirim (R2.1, R3.5) terjadi di halaman agen Zahra, jadi tidak ada panel operator di sisi Imelda. Stub agen hanya mencetak tautannya.
