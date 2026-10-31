# Kontrak API Vedika Autentik v3: konfirmasi suara

Acuan: `docs/prd-v3-konfirmasi-suara.md` (PRD v3.0) dan `docs/rencana-v3.md` bagian C. Kontrak v2 (`docs/api-contract.md`, pemeriksaan berkas PDF) tetap berlaku untuk `/api/v1/berkas` dan tidak diubah oleh dokumen ini.

Tiga sambungan, satu kontrak di tiap sambungan:

```
FE verifikator (statis)                Agen suara (browser, laptop telepon)
   │  Kontrak A: /api/v1                  │  Kontrak B1: /api/v1/agen, /api/v1/panggilan/{id}/*
   │  (siap tampil, polling 1 detik)      │  (tarik tugas, lapor status, kirim hasil)
   ▼                                      ▼
                 API (FastAPI) ──── Supabase (Postgres) + disk lokal (rekaman)
                    │  Kontrak B2: /v1/baca
                    ▼
        Pembaca jawaban (ai-service, LLM, tanpa state)
```

| Kontrak | Pemilik | Pihak lain |
|---|---|---|
| A: FE ↔ API | Imelda | FE (Imelda) |
| B1: agen suara ↔ API | Imelda (API) | Zahra (agen) |
| B2: API ↔ pembaca jawaban | Zahra (pembaca) | Imelda (API) |

## Prinsip

1. **FE tidak tahu agen dan pembaca ada.** FE hanya bicara ke API.
2. **Label dan status RS hanya dihitung di API** dengan `data-uji-konfirmasi/tools/aturan.py` (PRD R4.4). Agen dan pembaca tidak pernah mengirim label atau saran.
3. **Verifikator yang menyalakan.** Mode otomatis dinyalakan dan dijeda dari FE. Agen hanya menarik tugas; API memberi tugas bila mode AKTIF atau ada permintaan "Telepon sekarang", di jam 09.00–17.00, dan tidak ada panggilan lain yang sedang berjalan (prototipe: satu panggilan aktif).
4. **Aturan waktu dan percobaan di API.** Jeda WA ke telepon (R2.2) dan dua percobaan (R3.5) diputuskan API, agen hanya melapor.
5. **Pembaca tanpa state.** Transkrip masuk, JSON keluar. API yang menyimpan, mengulang, dan memberi label.
6. **Gagal aman.** Pembaca gagal dua kali → label `tidak_yakin`, tidak pernah `tidak_sesuai` atau `sesuai`. Tidak menjawab, menolak, atau tidak ingat tidak pernah dihitung (PRD bagian 10).
7. **Bentuk Kontrak A = bentuk `data-v3.js`**, supaya FE cukup mengganti sumber data. Pengecualian kecil yang ditangani adaptor FE: transkrip berupa objek dan tanggal berupa ISO.

## Konvensi

- Field `snake_case` bahasa Indonesia. Penerima wajib mengabaikan field yang tidak dikenal; menambah field tidak menaikkan versi.
- Waktu ISO 8601 dengan zona, mis. `2026-10-06T09:14:00+07:00`. Tanggal layanan ISO tanpa jam, mis. `2026-08-16`. Bulan layanan `YYYY-MM`.
- Galat selalu `{ "galat": { "kode": "…", "pesan": "…" } }` dengan status HTTP yang sesuai (sama dengan v2 dan `ai-service`).
- `204` berarti tidak ada isi (mis. tidak ada tugas untuk agen).
- ID panggilan: `CALL-<id_peserta>-<bulan>`, mis. `CALL-P-S1-2026-08`.

### Enum

| Nama | Nilai | Catatan |
|---|---|---|
| `status` panggilan | `antre`, `wa_terkirim`, `menelepon`, `tersambung`, `merekam`, `membaca_jawaban`, `selesai`, `tidak_terhubung` | Sama dengan DB |
| `label` | `sesuai`, `tidak_sesuai`, `tidak_yakin`, `tidak_terhubung`, `menolak` | DB menyimpan teks `aturan.py` (`Tidak sesuai`, …); API memetakan |
| `tindakan` | `pantau`, `tutup`, `klarifikasi`, `teruskan` | DB: `pantau`, `tutup_kasus`, `minta_klarifikasi_rs`, `teruskan_pk_jkn`; API memetakan. `pantau` hanya muncul sebagai saran |
| `indikator` | `I1`, `I2`, `I3`, `I4` | PRD F1 |
| `penerima.hubungan` | `peserta`, `anak`, `orang tua`, `pasangan` | `peserta` = pasien sendiri |
| `pembicara` | `ai`, `penerima` | Transkrip |
| `status_rs` | `Normal`, `Perlu klarifikasi RS` | R5.4 |
| `laporan` agen | `wa_terkirim`, `menelepon`, `tersambung`, `merekam`, `tidak_diangkat`, `chat_cadangan_terkirim` | Kontrak B1 |

Saran per label (PRD tabel F4): `sesuai → tutup`, `tidak_sesuai → klarifikasi`, `tidak_yakin → pantau`, `tidak_terhubung → pantau`, `menolak → pantau`.

### Objek bersama

**Transkrip** (dipakai A, B1, dan DB):

```json
[
  { "detik": 0, "pembicara": "ai", "teks": "Selamat siang, saya asisten otomatis dari BPJS Kesehatan. Panggilan ini direkam untuk konfirmasi layanan." },
  { "detik": 17, "pembicara": "penerima", "teks": "Iya, saya sendiri." }
]
```

`detik` dihitung dari awal panggilan tersambung.

**Jawaban pembaca**: skema di `data-uji-konfirmasi/README.md` bagian "Skema keluaran pembaca jawaban" (`status_panggilan`, `penerima`, `hubungan`, `hadir`, `jumlah_min`, `jumlah_maks`, `keyakinan`, `tanda_bahaya`, `membantah_tanggal_libur`, `kutipan_kunci`, `ringkasan`). Tidak ditulis ulang di sini.

---

# Kontrak A: FE ↔ API (`/api/v1`)

Autentikasi prototipe: tanpa login (produksi: login Supabase, peran `verifikator`). Verifikator diambil dari konfigurasi API (`R. Santoso`).

## `GET /api/v1/antrean`

Query opsional: `bulan` (bawaan `2026-08`), `rs` (mis. `RS01`), `status`.

```json
{
  "bulan": "2026-08",
  "angka": { "pasien_aktif": 300, "terpicu": 30, "sudah_ditelepon": 4, "tidak_sesuai": 2, "rs_perlu_klarifikasi": 0 },
  "pengaturan": { "mode_otomatis": false, "jam_mulai": "09:00", "jam_selesai": "17:00", "dalam_jam": true },
  "baris": [
    {
      "id": "CALL-P-S1-2026-08",
      "pasien": "Andi Pratama",
      "umur": 54,
      "rs": "RS01",
      "nama_rs": "RS Melati Sehat",
      "ditagih": 11,
      "indikator": ["I1", "I2", "I4"],
      "penerima": { "nama": "Andi Pratama", "hubungan": "peserta" },
      "status": "antre",
      "label": null,
      "prioritas": false,
      "percobaan": 0
    }
  ]
}
```

- Hanya pasien dengan ≥2 indikator (R1.2). S7 tidak pernah muncul.
- `penerima` mengikuti R1.3: keluarga bila `hubungi_keluarga`, selain itu peserta.
- Urutan: sedang berjalan, lalu `prioritas`, lalu `antre`, lalu selesai/tidak terhubung.
- `angka` dihitung dari seluruh antrean bulan itu, tidak terpengaruh filter.

## `GET /api/v1/panggilan/{id}`

Dipakai layar Panggilan berlangsung (polling 1 detik) dan Kartu bukti. Contoh S1 setelah selesai:

```json
{
  "id": "CALL-P-S1-2026-08",
  "pasien": "Andi Pratama",
  "umur": 54,
  "rs": "RS01",
  "nama_rs": "RS Melati Sehat",
  "bulan": "2026-08",
  "ditagih": 11,
  "tanggal": ["2026-08-03", "2026-08-04", "2026-08-06", "2026-08-10", "2026-08-11", "2026-08-13", "2026-08-16", "2026-08-17", "2026-08-20", "2026-08-24", "2026-08-27"],
  "tanda_tanggal": { "2026-08-16": "Minggu", "2026-08-17": "Libur nasional" },
  "indikator": ["I1", "I2", "I4"],
  "tanggal_libur": ["2026-08-16", "2026-08-17"],
  "penerima": { "nama": "Andi Pratama", "hubungan": "peserta" },
  "status": "selesai",
  "percobaan": 1,
  "log": [
    { "status": "wa_terkirim", "waktu": "2026-10-06T10:11:00+07:00", "percobaan": 1, "catatan": null },
    { "status": "menelepon", "waktu": "2026-10-06T10:12:00+07:00", "percobaan": 1, "catatan": null },
    { "status": "tersambung", "waktu": "2026-10-06T10:12:08+07:00", "percobaan": 1, "catatan": null },
    { "status": "merekam", "waktu": "2026-10-06T10:12:08+07:00", "percobaan": 1, "catatan": null },
    { "status": "membaca_jawaban", "waktu": "2026-10-06T10:13:41+07:00", "percobaan": 1, "catatan": null },
    { "status": "selesai", "waktu": "2026-10-06T10:13:45+07:00", "percobaan": 1, "catatan": null }
  ],
  "durasi": 92,
  "transkrip": [
    { "detik": 45, "pembicara": "penerima", "teks": "Tiga kali. Awal bulan, pertengahan, terus sekali lagi tanggal dua puluhan." }
  ],
  "tangkapan_sementara": null,
  "jawaban": {
    "status_panggilan": "terjawab", "penerima": "peserta", "hubungan": null, "hadir": true,
    "jumlah_min": 3, "jumlah_maks": 3, "keyakinan": "tinggi", "tanda_bahaya": [],
    "membantah_tanggal_libur": true,
    "kutipan_kunci": "Tiga kali... Nggak pernah. Hari Minggu kan tutup.",
    "ringkasan": "Peserta menjalani 3 sesi di bulan Agustus dan tidak pernah terapi di hari Minggu atau 17 Agustus."
  },
  "label": "tidak_sesuai",
  "alasan": "Ditagih 11 sesi, versi penerima paling banyak 3 sesi (selisih 8).",
  "selisih": 8,
  "saran": "klarifikasi",
  "rekaman": "/api/v1/panggilan/CALL-P-S1-2026-08/rekaman",
  "hapus_pada": null,
  "konteks_rs": { "rs": "RS01", "tidak_sesuai": 3, "terjawab": 5, "status": "Perlu klarifikasi RS" },
  "keputusan": null,
  "galat_pembaca": null
}
```

- Selama panggilan berlangsung, `jawaban`, `label`, `alasan`, `selisih`, `saran`, `rekaman` bernilai `null`, sedangkan `transkrip` bertambah dan `tangkapan_sementara` boleh terisi (lihat B1).
- `transkrip` di contoh dipotong; respons berisi semua baris.
- `selisih` = `max(0, ditagih − jumlah_maks)`, `null` bila `jumlah_maks` kosong.
- `rekaman` `null` untuk label selain `sesuai` dan `tidak_sesuai`, atau bila sudah lewat `hapus_pada` (R5.5).
- `konteks_rs` = ringkasan RS terkini untuk RS panggilan ini (dipakai teks saran di kartu bukti).
- `keputusan` berisi objek seperti di `GET /keputusan` bila sudah diputuskan.
- Identitas penerima tidak ikut dalam data apa pun yang dibagikan ke RS (R5.6); endpoint ini hanya untuk verifikator.

Galat: `404 panggilan_tidak_ada`.

## `GET /api/v1/panggilan/{id}/rekaman`

Audio rekaman (`audio/webm`), mendukung `Range`. Galat: `404 rekaman_tidak_ada` (belum ada, label tanpa rekaman, atau sudah dihapus).

## `POST /api/v1/panggilan/{id}/mulai`

"Telepon sekarang" dari baris antrean. Body kosong. Menandai `prioritas = true`; agen mengambilnya di giliran berikutnya walau mode otomatis mati. Batas jam tetap berlaku.

Balasan `200`: baris antrean (bentuk sama dengan `baris[]`). Galat: `404 panggilan_tidak_ada`, `409 bukan_antre` (status bukan `antre`).

## `POST /api/v1/panggilan/{id}/keputusan`

```json
{ "ikut_saran": false, "tindakan": "teruskan", "alasan": "Pola serupa sudah ditemukan di dua pasien lain RS ini." }
```

- `ikut_saran: true` → `tindakan` boleh dikosongkan; API memakai saran. `alasan` opsional.
- `ikut_saran: false` → `tindakan` wajib salah satu `tutup`, `klarifikasi`, `teruskan`; `alasan` wajib, tidak boleh kosong (R5.3).
- Hanya untuk status `selesai` atau `tidak_terhubung`. Keputusan baru menggantikan yang lama (yang lama tetap di riwayat).

Balasan `201`:

```json
{
  "id": 12,
  "panggilan_id": "CALL-P-S1-2026-08",
  "verifikator": "R. Santoso",
  "tindakan": "klarifikasi",
  "ikut_saran": true,
  "alasan": null,
  "waktu": "2026-10-06T10:15:20+07:00"
}
```

Galat: `422 alasan_wajib`, `422 tindakan_tidak_dikenal`, `409 belum_selesai`, `404 panggilan_tidak_ada`.

## `GET /api/v1/keputusan`

Riwayat keputusan, terbaru dulu. Setiap butir = objek keputusan di atas ditambah `pasien`, `rs`, `nama_rs`, `label`.

## `GET /api/v1/ringkasan-rs`

Query opsional: `bulan` (bawaan `2026-08`).

```json
{
  "bulan": "2026-08",
  "aturan": "Perlu klarifikasi RS jika tidak sesuai >= 3 DAN rasio tidak sesuai/terjawab >= 10%",
  "rs": [
    {
      "id_rs": "RS01", "nama": "RS Melati Sehat",
      "aktif": 68, "terpicu": 27, "persen": 39.7,
      "sesuai": 2, "tidak_sesuai": 3, "tidak_yakin": 0, "tidak_terhubung": 0, "menolak": 0,
      "terjawab": 5, "rasio": 0.6, "status": "Perlu klarifikasi RS"
    }
  ]
}
```

`terjawab` = `sesuai + tidak_sesuai`. Contoh di atas adalah keadaan setelah S1; sebelum S1, RS01 `tidak_sesuai: 2, terjawab: 4, status: "Normal"` (`expected_ringkasan_rs.json`).

## `GET /api/v1/pengaturan` dan `PUT /api/v1/pengaturan`

```json
{ "mode_otomatis": true, "jam_mulai": "09:00", "jam_selesai": "17:00", "jeda_wa_menit": 1, "jeda_percobaan_menit": 2 }
```

`PUT` menerima sebagian field. Tombol AKTIF/Jeda di FE = `PUT {"mode_otomatis": true|false}`. Galat: `422 pengaturan_tidak_valid`.

## `POST /api/v1/demo/reset`

Mengembalikan panggilan, log, dan keputusan ke keadaan awal demo (4 riwayat selesai, 26 antre, mode otomatis mati). Data master (RS, peserta, klaim, indikator) tidak disentuh. Rekaman hasil panggilan baru ikut dihapus. Balasan `200 {"ok": true}`.

## `GET /api/v1/kesehatan`

```json
{ "api": "ok", "db": "ok", "pembaca": "ok", "versi_aturan": "2026.10" }
```

Bila `db` tidak ok, FE memakai `data-v3.js` (mode cadangan).

---

# Kontrak B1: agen suara ↔ API (`/api/v1`)

Semua endpoint di bagian ini wajib header `X-Kunci-Agen: <AGEN_KEY dari backend/.env>`. Tanpa atau salah → `401 kunci_salah`. Halaman agen berjalan di origin sendiri (mis. `http://localhost:5173`); origin itu ditambahkan ke `CORS_ORIGINS`. Prototipe: kunci terlihat di browser dan ini diterima (produksi: token per perangkat).

## `POST /api/v1/agen/ambil`

Body kosong. Agen memanggil tiap 3 detik saat menganggur.

- `204`: tidak ada tugas (mode mati dan tidak ada prioritas, di luar jam, ada panggilan lain berjalan, atau antrean kosong/menunggu `coba_lagi_setelah`).
- `200`: satu tugas. API langsung mengunci panggilan itu (status tetap `antre` sampai agen melapor `wa_terkirim`; kunci lepas otomatis setelah 5 menit tanpa laporan).

```json
{
  "id": "CALL-P-S1-2026-08",
  "percobaan": 1,
  "no_tujuan": "08xxxxxxxxxx",
  "skrip": {
    "nama_penerima": "Andi Pratama",
    "hubungan": "peserta",
    "nama_pasien": "Andi Pratama",
    "nama_rs": "RS Melati Sehat",
    "bulan": "Agustus",
    "tanggal_libur": ["16 Agustus", "17 Agustus"]
  },
  "wa": {
    "lewati": false,
    "teks": "Halo Andi Pratama. Ini BPJS Kesehatan. Dalam 1 menit kami akan menelepon dari nomor 0800-0000-0165 untuk konfirmasi singkat layanan fisioterapi Andi Pratama di RS Melati Sehat bulan Agustus. Ini bukan tagihan. Kami tidak akan meminta data pribadi, kode OTP, atau pembayaran. Untuk memastikan pesan ini, hubungi Care Center 165.",
    "tautan": "https://wa.me/628xxxxxxxxxx?text=Halo%20Andi%20Pratama..."
  },
  "jeda_wa_menit": 1,
  "batas_detik": 150
}
```

- `no_tujuan` prototipe = `NOMOR_PENGUJI` dari `.env` (R2.1), disimpan di `panggilan.no_tujuan`.
- `skrip` mengisi variabel Lampiran A (R3.1). `tanggal_libur` kosong bila I4 tidak aktif; agen tidak bertanya soal libur (S3).
- `wa.teks` = Lampiran B persis (R2.3), tanpa tautan di dalam teks. `wa.lewati = true` pada percobaan ke-2 (pemberitahuan cukup sekali).
- `batas_detik` = batas panggilan 2,5 menit (R3.3, Lampiran A).

## `POST /api/v1/panggilan/{id}/status`

```json
{ "laporan": "wa_terkirim", "waktu": "2026-10-06T10:11:00+07:00", "catatan": null }
```

| `laporan` | Akibat di API |
|---|---|
| `wa_terkirim` | status `wa_terkirim`, `waktu_wa` diisi, log |
| `menelepon` | status `menelepon`, log. Bila belum lewat `jeda_wa_menit` sejak `waktu_wa` → `409 jeda_belum_lewat` |
| `tersambung` | status `tersambung`, `waktu_mulai` diisi, log |
| `merekam` | status `merekam`, log |
| `tidak_diangkat` | log `menelepon` dengan `catatan = "tidak_diangkat"`. Percobaan ke-1: status kembali `antre`, `coba_lagi_setelah = sekarang + jeda_percobaan_menit`. Percobaan ke-2: status `tidak_terhubung`, label `Tidak terhubung` (R3.5) |
| `chat_cadangan_terkirim` | `chat_cadangan_terkirim = true`, log `tidak_terhubung` dengan catatan |

Balasan `200`:

```json
{ "status": "antre", "percobaan": 1, "coba_lagi_setelah": "2026-10-06T10:16:00+07:00", "chat_cadangan": null }
```

Pada percobaan ke-2 yang tidak diangkat, `chat_cadangan` terisi dan agen membuka tautannya, lalu melapor `chat_cadangan_terkirim`:

```json
{
  "status": "tidak_terhubung",
  "percobaan": 2,
  "coba_lagi_setelah": null,
  "chat_cadangan": {
    "teks": "Kami belum berhasil menelepon. Kira-kira berapa kali Joko Prasetyo menjalani fisioterapi di RS Cempaka Asri bulan Agustus? Balas dengan angka: 1) 1–2 kali  2) 3–4 kali  3) 5–8 kali  4) lebih dari 8 kali  5) tidak ingat  6) tidak pernah terapi di sana.",
    "tautan": "https://wa.me/628xxxxxxxxxx?text=Kami%20belum%20berhasil..."
  }
}
```

Galat: `404 panggilan_tidak_ada`, `409 urutan_salah` (mis. `tersambung` sebelum `menelepon`), `409 jeda_belum_lewat`, `422 laporan_tidak_dikenal`.

## `POST /api/v1/panggilan/{id}/transkrip`

Dikirim selama panggilan (mis. tiap giliran bicara selesai). Baris ditambahkan, bukan diganti.

```json
{
  "baris": [{ "detik": 45, "pembicara": "penerima", "teks": "Tiga kali. Awal bulan, pertengahan, terus sekali lagi tanggal dua puluhan." }],
  "tangkapan_sementara": { "penerima": "peserta", "hadir": true, "jumlah_maks": 3 }
}
```

`tangkapan_sementara` opsional, bentuk = sebagian field jawaban pembaca, hanya untuk tampilan "Yang ditangkap AI" selama panggilan (R5.1). Tidak pernah dipakai untuk label. Balasan `204`. Galat: `409 bukan_berlangsung` (status bukan `tersambung`/`merekam`).

## `POST /api/v1/panggilan/{id}/hasil`

`multipart/form-data`:

| Field | Isi |
|---|---|
| `rekaman` | File `.webm` dua arah (MediaRecorder, Lampiran C langkah 5). Opsional bila penerima menolak sebelum direkam |
| `transkrip` | JSON string, transkrip final lengkap (menggantikan baris sementara) |
| `durasi` | Detik, bilangan bulat |

Balasan `202 {"status": "membaca_jawaban"}`. Di latar belakang API:

1. Simpan rekaman di `backend/uploads/rekaman/<id>.webm` (`rekaman_path` relatif) dan transkrip di DB.
2. Panggil `POST /v1/baca` (Kontrak B2), ulang 1 kali bila gagal.
3. Hitung label dengan `aturan.py`, simpan `jawaban`, `label`, `alasan`, `hapus_pada` (R5.5: `sesuai` → selesai + 30 hari; `tidak_sesuai` → `null` sampai `klarifikasi_selesai_pada`; lainnya → rekaman dan transkrip tidak disimpan).
4. Status `selesai`, log `membaca_jawaban` dan `selesai`.

Galat: `404 panggilan_tidak_ada`, `409 bukan_berlangsung`, `413 terlalu_besar` (rekaman > 10 MB), `422 transkrip_tidak_valid`.

---

# Kontrak B2: API ↔ pembaca jawaban (`ai-service`, `/v1`)

Endpoint baru di `ai-service` milik Zahra, di samping `/v1/analisis` dan `/v1/bandingkan` (v2, dibiarkan). Header `X-Kunci-Layanan` (sama dengan v2; `KUNCI_MESIN` di backend, `AI_SERVICE_KEY` di `ai-service`).

## `POST /v1/baca`

```json
{
  "id": "CALL-P-S1-2026-08",
  "transkrip": [
    { "detik": 39, "pembicara": "ai", "teks": "Kira-kira berapa kali Bapak datang terapi di bulan Agustus?" },
    { "detik": 45, "pembicara": "penerima", "teks": "Tiga kali. Awal bulan, pertengahan, terus sekali lagi tanggal dua puluhan." }
  ],
  "konteks": {
    "sesi_ditagih": 11,
    "tanggal_libur": ["2026-08-16", "2026-08-17"],
    "nama_pasien": "Andi Pratama",
    "bulan": "2026-08"
  }
}
```

Balasan `200`: JSON jawaban sesuai skema README data uji, ditambah `versi_pembaca`:

```json
{
  "status_panggilan": "terjawab", "penerima": "peserta", "hubungan": null, "hadir": true,
  "jumlah_min": 3, "jumlah_maks": 3, "keyakinan": "tinggi", "tanda_bahaya": [],
  "membantah_tanggal_libur": true,
  "kutipan_kunci": "Tiga kali. Awal bulan, pertengahan, terus sekali lagi tanggal dua puluhan.",
  "ringkasan": "Peserta menjalani 3 sesi di bulan Agustus.",
  "versi_pembaca": "pembaca-0.1"
}
```

- `tanda_bahaya` hanya boleh berisi `tanda_tangan_tanpa_layanan`, `diminta_membayar`, `layanan_berbeda` (R4.2).
- Pembaca tidak mengirim label, saran, atau skor.
- Transkrip kosong → `status_panggilan` sesuai keadaan (`tidak_terhubung`/`menolak`) atau `422 transkrip_kosong`.

Galat pembaca: `422 transkrip_kosong`, `502 llm_gagal`, `504 batas_waktu`. Penanganan di API: batas waktu 30 detik; galat, timeout, atau JSON tidak lolos validasi skema → ulang 1 kali; tetap gagal → label `tidak_yakin`, pesan galat disimpan di `galat_pembaca` (R4.3).

Uji pembaca: `python3 data-uji-konfirmasi/tools/uji.py jawaban keluaran.json` lulus untuk transkrip S1–S6 dan S8 (R4.1).

---

# Alur ujung ke ujung

## S1 (Tidak sesuai)

1. Verifikator menekan AKTIF → FE `PUT /pengaturan {"mode_otomatis": true}`.
2. Agen `POST /agen/ambil` → tugas S1.
3. Agen membuka `wa.tautan` di WhatsApp Desktop, operator menekan kirim, agen `status wa_terkirim`.
4. Setelah `jeda_wa_menit`, agen menelepon: `status menelepon`, lalu `tersambung`, `merekam`.
5. Selama bicara, agen `POST …/transkrip` per giliran. FE (polling `GET /panggilan/{id}`) menampilkan transkrip mengalir.
6. Panggilan ditutup, agen `POST …/hasil` (rekaman + transkrip final) → `202`.
7. API memanggil `/v1/baca`, menghitung label `Tidak sesuai`, selisih 8, `hapus_pada = null`, status `selesai`.
8. FE melihat `selesai` dan pindah ke Kartu bukti: 11 vs 3, selisih 8, saran Minta klarifikasi RS.
9. Verifikator `POST …/keputusan {"ikut_saran": true}`.
10. `GET /ringkasan-rs`: RS Melati `Perlu klarifikasi RS` (3 dari 5).

## S5 (Tidak terhubung)

1. Ambil → WA → `menelepon` → `tidak_diangkat` → status `antre`, `coba_lagi_setelah` +2 menit.
2. Setelah lewat, ambil lagi (`percobaan: 2`, `wa.lewati: true`) → `menelepon` → `tidak_diangkat` → status `tidak_terhubung`, balasan berisi `chat_cadangan`.
3. Agen membuka tautan chat, operator kirim, agen `status chat_cadangan_terkirim`. Label `tidak_terhubung`, tidak dihitung di ringkasan RS.

## S8 (Menolak)

Panggilan tersambung, penerima curiga penipuan, AI menenangkan sekali lalu menutup. Agen mengirim `hasil` (rekaman boleh ada). Pembaca → `status_panggilan: "menolak"` → label `menolak`, saran Pantau, rekaman dan transkrip tidak disimpan, tidak dihitung.

---

# Pemetaan kontrak ↔ DB (`backend/db/schema_v3.sql`)

| Kontrak | DB |
|---|---|
| `id` | `panggilan.id` |
| `pasien`, `umur` | `peserta.nama`, `peserta.umur` lewat `panggilan.id_peserta` |
| `rs`, `nama_rs` | `panggilan.id_rs`, `rumah_sakit.nama_rs` |
| `bulan` | `panggilan.bulan_layanan` |
| `ditagih` | `panggilan.sesi_ditagih` |
| `tanggal`, `tanda_tanggal` | `klaim_sesi.tanggal` (pasien, RS, bulan) + hari Minggu + `libur_nasional` |
| `indikator`, `tanggal_libur` | `indikator_bulanan` (`i1_…`–`i4_…`, `tanggal_libur`) |
| `penerima.nama`, `penerima.hubungan` | `panggilan.nama_penerima`, `panggilan.hubungan` (`peserta` bila `panggilan.penerima = 'peserta'`) |
| `status`, `percobaan`, `prioritas` | `panggilan.status`, `.percobaan`, `.prioritas` |
| `coba_lagi_setelah` | `panggilan.coba_lagi_setelah` |
| `log[]` | `panggilan_log` |
| `transkrip` | `panggilan.transkrip` (objek `{detik, pembicara, teks}`) |
| `durasi` | `waktu_selesai − waktu_mulai` |
| `jawaban` | `panggilan.jawaban` |
| `label` | `panggilan.label` (`Tidak sesuai` ↔ `tidak_sesuai`, dst.) |
| `alasan` | `panggilan.alasan` |
| `rekaman` | `panggilan.rekaman_path` |
| `hapus_pada`, `galat_pembaca`, `no_tujuan` | kolom bernama sama |
| `chat_cadangan` terkirim | `panggilan.chat_cadangan_terkirim`, `.jawaban_chat` |
| `keputusan` | `keputusan_panggilan` (`tutup` ↔ `tutup_kasus`, `klarifikasi` ↔ `minta_klarifikasi_rs`, `teruskan` ↔ `teruskan_pk_jkn`, `pantau` ↔ `pantau`) |
| `pengaturan` | `pengaturan` (kunci-nilai) |

Perubahan skema yang dibutuhkan kontrak ini (dikerjakan di bagian D):

- `keputusan_panggilan.tindakan` mengizinkan `pantau`.
- Kunci ambil agen: kolom `diambil_pada timestamptz` di `panggilan` (lepas otomatis setelah 5 menit).

# Mode cadangan

- Pembaca mati → label `tidak_yakin` dengan `galat_pembaca`, demo tetap jalan.
- API atau DB mati → FE memakai `data-v3.js` (simulasi). Layar tidak pernah kosong.

# Jejak requirement (PIC I dan Z + I)

| Requirement | Dipenuhi oleh |
|---|---|
| R1.3 penerima | `penerima` di `GET /antrean`, `skrip` di `agen/ambil` |
| R1.4 layar Antrean | `GET /antrean` |
| R1.5 mode otomatis, jam, Jeda | `PUT /pengaturan`, aturan `agen/ambil`, `POST …/mulai` |
| R2.1 pesan WA | `wa.teks` + `wa.tautan` di `agen/ambil` |
| R2.2 jeda pesan ke panggilan | `jeda_wa_menit`, `409 jeda_belum_lewat`, `panggilan_log` |
| R2.3 isi pesan | `wa.teks` = Lampiran B tanpa tautan |
| R3.4 rekaman + transkrip | `POST …/hasil`, `GET …/rekaman` |
| R3.5 dua percobaan + chat cadangan | laporan `tidak_diangkat`, `chat_cadangan` |
| R3.7 status ke backend | `POST …/status`, `log[]` di `GET /panggilan/{id}` |
| R4.4 label dengan `aturan.py` | langkah 3 `POST …/hasil` |
| R5.1 layar Panggilan berlangsung | `GET /panggilan/{id}` (polling), `POST …/transkrip` |
| R5.2 kartu bukti | `GET /panggilan/{id}` setelah `selesai` |
| R5.3 keputusan | `POST …/keputusan`, `GET /keputusan` |
| R5.4 ringkasan RS | `GET /ringkasan-rs`, `konteks_rs` |
| R5.5 retensi | `hapus_pada`, `rekaman: null` setelah lewat |
| R5.6 identitas penerima, label Simulasi | catatan di `GET /panggilan/{id}`; label Simulasi di FE |

# Yang perlu disepakati dengan Zahra

Diisi saat push.
