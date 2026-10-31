# Serah terima ke Zahra: yang perlu dikerjakan dan disambung

Status: sesuai kode di branch `v3-api-konfirmasi` (tiket D-10). Endpoint dan kedua stub sudah ada dan diuji otomatis. Di D-09 (31 Okt 2026) S1, S2, S5, dan S8 didemokan di browser dengan API, stub pembaca, dan stub agen terhadap Supabase: S1 sampai Kartu bukti dan RS Melati menjadi Perlu klarifikasi RS (3 dari 5); S2 Tidak sesuai dengan tanda bahaya tanda tangan; S5 dua kali tidak diangkat lalu chat cadangan (Tidak terhubung); S8 Menolak tanpa rekaman dan transkrip. Mulai ulang demo mengembalikan antrean ke 26 Antre dan 4 Selesai.

Acuan: [prd-v3-konfirmasi-suara.md](prd-v3-konfirmasi-suara.md) bagian 7 (PIC Z dan Z + I), [api-contract-v3.md](api-contract-v3.md) Kontrak B1 dan B2, [rencana-v3.md](rencana-v3.md), [backend/README.md](../backend/README.md) bagian "v3".

## Ringkasnya

Backend, database, dan website sudah dikerjakan Imelda. Supaya demo jalan tanpa menunggu, bagian Zahra diganti dua dummy:

| Bagian Zahra | Dummy sementara (Imelda) | Diganti oleh |
|---|---|---|
| Pembaca jawaban (LLM) | `backend/stub_mesin/main.py`: `POST /v1/baca` mengembalikan `expected_jawaban` dari `skenario_uji.json` menurut id panggilan (S1 sampai S8) | `POST /v1/baca` di `ai-service` |
| Agen suara (Gemini Live) | `backend/scripts/stub_agen.py`: memutar transkrip dan rekaman ElevenLabs lewat endpoint agen | Halaman agen di browser laptop telepon |
| Jalur audio (BlackHole + WA Desktop) | Tidak ada; stub tidak menelepon dan tidak membuka WhatsApp | Setup laptop telepon (Zahra + Richard) |

Menyambung = isi `backend/.env` dengan alamat dan kunci Zahra, matikan stub, jalankan bagian Zahra. Backend dan website tidak perlu diubah.

## Menjalankan semuanya di lokal (untuk melihat perilaku acuan)

Butuh `backend/.env` dari Imelda (database Supabase sudah memuat skema v3 dan seed). Dari folder `backend`:

```bash
.venv/bin/uvicorn stub_mesin.main:app --port 8001      # pembaca jawaban (stub)
.venv/bin/uvicorn app.main:app --port 8000             # API
.venv/bin/python -m scripts.stub_agen --skenario S1    # agen (stub), sekali jalan; tanpa --skenario terus mengambil antrean
python3 -m http.server 8899                            # website, dari akar repo: http://localhost:8899
```

Buka `http://localhost:8899`, masuk, buka Autentik. Catatan: tugas hanya keluar jam 09.00–17.00 WIB dan jeda WA bawaan 1 menit. Untuk demo cepat:

```bash
curl -X PUT localhost:8000/api/v1/pengaturan -H 'Content-Type: application/json' \
  -d '{"jeda_wa_menit": 0, "jeda_percobaan_menit": 0, "jam_mulai": "00:00", "jam_selesai": "23:59"}'
```

Tombol "Mulai ulang demo" di website (atau `POST /api/v1/demo/reset`) mengembalikan panggilan, log, dan keputusan ke keadaan awal.

## 1. Pembaca jawaban (R4.1–R4.3, R4.5)

Tambah endpoint baru di `ai-service` (di samping `/v1/analisis` dan `/v1/bandingkan` v2, biarkan saja):

- `POST /v1/baca`, header `X-Kunci-Layanan` (`AI_SERVICE_KEY`; salah → `401 kunci_salah`). Body dan balasan: Kontrak B2. Body: `{id, transkrip: [{detik, pembicara, teks}], konteks: {sesi_ditagih, tanggal_libur: ["2026-08-16", ...], nama_pasien, bulan}}`.
- Balasan = JSON skema `data-uji-konfirmasi/README.md` ("Skema keluaran pembaca jawaban") + `versi_pembaca`.
- Jangan kirim label, saran, atau skor. Label dihitung backend dengan `tools/aturan.py`.
- Galat: `422 transkrip_kosong` (transkrip kosong selalu ditolak, bukan ditebak), `502 llm_gagal`, `504 batas_waktu`. Bentuk `{"galat": {"kode", "pesan"}}`, sama dengan v2.

Yang dilakukan backend terhadap balasanmu (`backend/app/agen.py`, fungsi `lolos_skema` dan `baca_dengan_ulang`):

- Batas waktu 30 detik. `502`, `504`, timeout, tidak bisa terhubung, atau JSON tidak lolos skema → diulang **1 kali**. `422 transkrip_kosong` tidak diulang. Gagal lagi → label Tidak yakin dan pesan galat disimpan (`galat_pembaca`).
- JSON dianggap tidak lolos skema bila: bukan objek; `status_panggilan` bukan `terjawab`/`tidak_terhubung`/`menolak`; `penerima` bukan `peserta`/`keluarga`/`null`; `keyakinan` bukan `tinggi`/`rendah`/`null`; `hadir` bukan boolean/`null`; `jumlah_min`/`jumlah_maks` bukan bilangan bulat ≥0 atau `null`; `tanda_bahaya` bukan daftar yang isinya hanya `tanda_tangan_tanpa_layanan`, `diminta_membayar`, `layanan_berbeda`. Key yang tidak ada dilengkapi `null` oleh backend.
- `membantah_tanggal_libur` harus `null` bila `tanggal_libur` kosong.

Perilaku stub yang harus ditiru: untuk transkrip skenario S1 sampai S6 dan S8 mengembalikan persis `expected_jawaban`; untuk panggilan lain jawaban Tidak yakin (`keyakinan: "rendah"`, jumlah `null`). Mode `GAGAL=1` (variabel lingkungan stub) membuat `/v1/baca` selalu `502 llm_gagal`, untuk menguji jalur gagal aman.

Selesai bila:

- `python3 data-uji-konfirmasi/tools/uji.py jawaban keluaran.json` LULUS untuk S1–S6 dan S8.
- 20 jawaban tambahan buatan tim (santai, ragu, keluarga, bising) ≥90% field kunci benar (R4.5).
- Transkrip kosong tidak membuat layanan galat 500 (R4.3).

## 2. Agen suara (R3.1–R3.5, R3.7)

Halaman di browser laptop telepon. Bicara ke backend lewat Kontrak B1, **semua** endpoint wajib header `X-Kunci-Agen: <AGEN_KEY>` (kosong atau salah → `401 kunci_salah`). `stub_agen.py` adalah contoh yang urutan dan bentuk body-nya sudah benar; baca `backend/scripts/stub_agen.py` dan `backend/tests/test_stub_agen.py`.

Urutan per panggilan:

1. `POST /api/v1/agen/ambil` tiap 3 detik saat menganggur. `204` = tidak ada tugas (mode otomatis mati atau dijeda dan tidak ada "Telepon sekarang", di luar jam 09.00–17.00 WIB, ada panggilan lain berjalan, antrean kosong, atau percobaan ke-2 belum waktunya). `200` = tugas; panggilan itu langsung terkunci untuk agen. **Kunci lepas sendiri setelah 5 menit tanpa laporan.**
2. Bila `wa.lewati = false`: buka `wa.tautan` di WhatsApp Desktop, operator menekan kirim, lalu `POST /api/v1/panggilan/{id}/status {"laporan": "wa_terkirim"}`. Stub hanya mencetak tautannya.
3. Tunggu `jeda_wa_menit`, lalu telepon `no_tujuan` lewat WA Desktop dan lapor `menelepon`. Terlalu cepat → `409 jeda_belum_lewat`: tunggu lalu ulang (stub mengulang tiap detik).
4. Tidak diangkat → lapor `tidak_diangkat`. Balasan `status: "antre"` dengan `coba_lagi_setelah` (percobaan ke-1, kembali ke langkah 1; di percobaan ke-2 `wa.lewati = true`, langsung `menelepon`). Setelah dua kali gagal balasan `status: "tidak_terhubung"` memuat `chat_cadangan {teks, tautan}`: buka tautannya, operator kirim, lapor `chat_cadangan_terkirim`.
5. Diangkat → lapor `tersambung`, lalu `merekam`.
6. Selama bicara: `POST …/transkrip` `{"baris": [{detik, pembicara: "ai"|"penerima", teks}], "tangkapan_sementara": {...}}` per giliran bicara (balasan `204`). `baris` ditambahkan, bukan diganti. `tangkapan_sementara` opsional dan menggantikan kiriman sebelumnya; hanya key `penerima`, `hubungan`, `hadir`, `jumlah_min`, `jumlah_maks`, `keyakinan`, `membantah_tanggal_libur`, `tanda_bahaya` yang disimpan, hanya untuk panel "Yang ditangkap AI", tidak pernah dasar label.
7. Selesai: `POST …/hasil` multipart: `rekaman` (file audio dua arah, opsional bila penerima menolak sebelum direkam), `transkrip` (JSON string transkrip final lengkap, `[]` sah), `durasi` (detik, bilangan bulat). Balasan `202 {"status": "membaca_jawaban"}`; label muncul beberapa detik kemudian. Rekaman maksimal 10 MB (`413 terlalu_besar`).

Aturan yang diputuskan backend, bukan agen: jeda WA, dua percobaan, kapan chat cadangan, label, retensi (R5.5). Agen **tidak pernah** mengirim label.

Urutan laporan yang sah di `…/status` (selain itu `409 urutan_salah`; laporan di luar daftar `422 laporan_tidak_dikenal`):

| Status panggilan | Laporan yang boleh |
|---|---|
| `antre`, percobaan ke-1 | `wa_terkirim` |
| `antre`, percobaan ke-2 | `menelepon` |
| `wa_terkirim` | `menelepon` |
| `menelepon` | `tersambung`, `tidak_diangkat` |
| `tersambung` | `merekam` |
| `tidak_terhubung` | `chat_cadangan_terkirim` |

Hal yang mudah terlewat:

- **Satu panggilan aktif sekaligus.** Selama ada panggilan berstatus `wa_terkirim`/`menelepon`/`tersambung`/`merekam`/`membaca_jawaban`, `agen/ambil` membalas `204`. Agen harus selalu mengakhiri panggilan dengan `hasil`, atau `tidak_diangkat`; bila halaman agen mati di tengah panggilan, panggilan itu menahan antrean sampai verifikator menekan "Mulai ulang demo" (`POST /demo/reset`).
- Transkrip dan hasil hanya diterima saat status `tersambung` atau `merekam` (`409 bukan_berlangsung`).
- `detik` transkrip dihitung dari saat panggilan tersambung. Stub memakai waktu mulai tiap baris dari `assets/rekaman/waktu.json` supaya layar Panggilan seirama suara.
- Waktu pada laporan boleh dikirim (`waktu`, ISO 8601 berzona); jeda dan percobaan diputuskan dengan jam server.
- Rekaman disimpan di `backend/uploads/rekaman/<id>.<ekstensi>`; ekstensi mengikuti nama berkas kiriman (`.webm`, `.mp3`, `.wav`, `.ogg`, `.m4a`, selain itu `.webm`). Rekaman dan transkrip dibuang otomatis untuk label selain Sesuai dan Tidak sesuai.
- `no_tujuan` prototipe = `NOMOR_PENGUJI` dari `.env`, bukan nomor peserta.

Isi percakapan:

- Skrip dari Lampiran A PRD, variabel diisi dari `skrip` di balasan `agen/ambil`: `nama_penerima`, `sapaan_penerima`, `hubungan`, `nama_pasien`, `sapaan_pasien`, `nama_rs`, `bulan`, `tanggal_libur`. `tanggal_libur` kosong → jangan tanya soal libur (S3).
- Aturan bicara R3.3: mengaku asisten otomatis; satu pertanyaan per giliran; kalimat ≤20 kata; tidak meminta NIK, OTP, rekening, uang; tidak memakai kata curang/fraud; tidak berdebat; mengulang jawaban penting.
- Tujuh cabang di Gambar 3 PRD dan semua `perilaku_ai_wajib` di `skenario_uji.json` (lihat bagian "Cakupan `perilaku_ai_wajib`" di kontrak).
- Batas panggilan `batas_detik` (150 detik).

Selesai bila:

- S1 menyebut "RS Melati Sehat", "Agustus", "16 dan 17 Agustus" (R3.1).
- S1–S8 memenuhi `perilaku_ai_wajib`; transkrip dicek manual terhadap R3.3.
- Rekaman S1 bisa diputar di Kartu bukti (R3.4).
- Status muncul di layar Panggilan tanpa muat ulang (R3.7; website membaca API tiap detik).

Cara menguji tanpa HP: jalankan perintah di bagian "Menjalankan semuanya di lokal", lihat bagaimana `stub_agen.py` memanggil endpoint, lalu ganti stub dengan halaman agen. Cek yang sama dijalankan otomatis di `backend/tests/test_api_v3_agen.py` dan `test_stub_agen.py`.

## 3. Jalur audio (R3.6, Zahra + Richard)

Lampiran C PRD: BlackHole 2ch/16ch, WA Desktop (speaker = BlackHole 2ch, mikrofon = BlackHole 16ch), agen input BlackHole 2ch dan output BlackHole 16ch lewat `setSinkId`, Multi-Output Device supaya tim ikut mendengar, rekam dua arah dengan MediaRecorder (.webm).

Gerbang: 3 panggilan berturut-turut jelas, transkrip ≥90% benar. Cadangan bila gagal: web call di browser.

## 4. Indikator (R1.1, R1.2)

Sudah jalan: seed menghitung indikator Agustus dengan `tools/aturan.py`, `uji.py indikator` LULUS 300/300, dan S7 tidak pernah masuk antrean (diuji otomatis). Zahra cukup mengonfirmasi bahwa aturan ini yang dipakai. Tidak perlu membangun mesin indikator terpisah untuk prototipe.

## 5. Cara menyambung

`backend/.env` (diisi Imelda; contoh nama variabel ada di `backend/.env.example`):

```
MESIN_URL=http://localhost:8001        # ai-service Zahra (ganti dari stub_mesin)
KUNCI_MESIN=<sama dengan AI_SERVICE_KEY di ai-service>
AGEN_KEY=<dibagikan ke Zahra untuk header X-Kunci-Agen>
CORS_ORIGINS=http://localhost:8899,http://localhost:5173   # tambah origin halaman agen
NOMOR_PENGUJI=<nomor HP anggota tim yang memerankan penerima>
NOMOR_PENELEPON=0800-0000-0165         # nomor pengirim yang tampil di teks WA (bawaan)
```

Port lokal: API 8000, website 8899, `ai-service` 8001, halaman agen (usul) 5173. Pembaca dipanggil di alamat `MESIN_URL`; stub dan `ai-service` memakai alamat yang sama, jadi menyambung cukup mengganti isinya.

Stack: backend tetap bisa jalan di Python 3.12 seperti `ai-service`. Format galat dan header kunci antar layanan sama dengan v2.

Perubahan di luar kontrak yang perlu Zahra tahu:

- `GET /api/v1/kesehatan` kini memuat juga `pembaca` dan `versi_aturan`; `mesin` tetap ada (v2). Website memakai API hanya bila `api` dan `db` ok; bila pembaca mati, demo tetap jalan dengan label Tidak yakin.
- `ai-service` harus menjawab `GET /v1/kesehatan` dengan `{"status": "ok"}` (sudah begitu di v2) supaya `pembaca` tampil ok.

## 6. Yang perlu disepakati

Diisi saat push (tiket KT-07).
