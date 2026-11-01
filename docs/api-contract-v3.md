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
3. **Verifikator yang menyalakan.** Mode otomatis dinyalakan, dijeda, dan dimatikan dari FE. Agen hanya menarik tugas; API memberi tugas bila (mode AKTIF dan tidak dijeda) atau ada permintaan "Telepon sekarang", di jam 09.00–17.00, dan tidak ada panggilan lain yang sedang berjalan (prototipe: satu panggilan aktif).
4. **Aturan waktu dan percobaan di API.** Jeda WA ke telepon (R2.2) dan dua percobaan (R3.5) diputuskan API, agen hanya melapor.
5. **Pembaca tanpa state.** Transkrip masuk, JSON keluar. API yang menyimpan, mengulang, dan memberi label.
6. **Gagal aman.** Pembaca gagal dua kali → label `tidak_yakin`, tidak pernah `tidak_sesuai` atau `sesuai`. Tidak menjawab, menolak, atau tidak ingat tidak pernah dihitung (PRD bagian 10).
7. **Bentuk Kontrak A = bentuk `data-v3.js`**, supaya FE cukup mengganti sumber data. Perbedaan bentuk (transkrip berupa objek, tanggal ISO, nama status) ditangani adaptor FE; daftarnya di bagian "Sumber data FE". **Pembagian tugas**: apa yang dikirim ke penerima dan apa yang dihitung aturan datang dari API; nama tampilan dan teks penjelasan tetap konstanta FE.

## Konvensi

- Field `snake_case` bahasa Indonesia. Penerima wajib mengabaikan field yang tidak dikenal; menambah field tidak menaikkan versi.
- Waktu ISO 8601 dengan zona, mis. `2026-10-06T09:14:00+07:00`. Tanggal layanan ISO tanpa jam, mis. `2026-08-16`. Bulan layanan `YYYY-MM`.
- Galat selalu `{ "galat": { "kode": "…", "pesan": "…" } }` dengan status HTTP yang sesuai (sama dengan v2 dan `ai-service`). Daftar kode ada di tabel "Kode galat" di bawah.
- `204` berarti tidak ada isi (mis. tidak ada tugas untuk agen).
- ID panggilan: `CALL-<id_peserta>-<bulan>`, mis. `CALL-P-S1-2026-08`. Pengecualian: empat riwayat latar demo memakai `CALL-LATAR-001` … `CALL-LATAR-004` (isi berkas `riwayat_panggilan_2026-08.json`).

### Enum

| Nama | Nilai | Catatan |
|---|---|---|
| `status` panggilan | `antre`, `wa_terkirim`, `menelepon`, `tersambung`, `merekam`, `membaca_jawaban`, `selesai`, `tidak_terhubung` | Sama dengan DB |
| `label` | `sesuai`, `tidak_sesuai`, `tidak_yakin`, `tidak_terhubung`, `menolak` | DB menyimpan teks `aturan.py` (`Tidak sesuai`, …); API memetakan |
| `tindakan` | `pantau`, `tutup`, `klarifikasi`, `teruskan` | DB: `pantau`, `tutup_kasus`, `minta_klarifikasi_rs`, `teruskan_pk_jkn`; API memetakan. `pantau` hanya bisa menjadi saran; ia tersimpan sebagai `tindakan` hanya lewat `ikut_saran: true` (label `tidak_yakin`, `tidak_terhubung`, `menolak`) |
| `indikator` | `I1`, `I2`, `I3`, `I4` | PRD F1 |
| `penerima.hubungan` | `peserta`, `anak`, `orang tua`, `pasangan` | `peserta` = pasien sendiri. Nilai lain = `peserta.hubungan_keluarga` |
| `jawaban.penerima` | `peserta`, `keluarga`, `null` | Skema pembaca |
| `pembicara` | `ai`, `penerima` | Transkrip |
| `status_rs` | `Normal`, `Perlu klarifikasi RS` | R5.4 |
| `laporan` agen | `wa_terkirim`, `menelepon`, `tersambung`, `merekam`, `tidak_diangkat`, `chat_cadangan_terkirim` | Kontrak B1 |
| `tanda_tanggal` | `Minggu`, `Libur nasional` | Satu tanda per tanggal; bila tanggal jatuh di keduanya, `Minggu` |

Saran per label (PRD tabel F4): `sesuai → tutup`, `tidak_sesuai → klarifikasi`, `tidak_yakin → pantau`, `tidak_terhubung → pantau`, `menolak → pantau`.

### Kode galat

| Kode | HTTP | Dipakai di |
|---|---|---|
| `panggilan_tidak_ada` | 404 | semua endpoint `…/panggilan/{id}…` |
| `rekaman_tidak_ada` | 404 | `GET …/rekaman` |
| `bukan_antre` | 409 | `POST …/mulai` |
| `belum_selesai` | 409 | `POST …/keputusan` |
| `alasan_wajib` | 422 | `POST …/keputusan` |
| `tindakan_tidak_dikenal` | 422 | `POST …/keputusan` |
| `tindakan_sama_saran` | 422 | `POST …/keputusan` |
| `pengaturan_tidak_valid` | 422 | `PUT /pengaturan` |
| `kunci_salah` | 401 | semua endpoint B1 (`X-Kunci-Agen`) dan B2 (`X-Kunci-Layanan`) |
| `urutan_salah` | 409 | `POST …/status` |
| `jeda_belum_lewat` | 409 | `POST …/status` |
| `laporan_tidak_dikenal` | 422 | `POST …/status` |
| `bukan_berlangsung` | 409 | `POST …/transkrip`, `POST …/hasil` |
| `terlalu_besar` | 413 | `POST …/hasil` |
| `transkrip_tidak_valid` | 422 | `POST …/hasil` (JSON rusak atau bentuk salah) |
| `transkrip_kosong` | 422 | `POST /v1/baca` |
| `llm_gagal` | 502 | `POST /v1/baca` |
| `batas_waktu` | 504 | `POST /v1/baca` |

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

Autentikasi prototipe: tanpa login (produksi: login Supabase, peran `verifikator`). Verifikator diambil dari konfigurasi API (`R. Santoso`); nama itu muncul sebagai `verifikator` di keputusan dan harus sama dengan nama di header FE.

## `GET /api/v1/antrean`

Query opsional: `bulan` (bawaan `2026-08`), `id_rs` (mis. `RS01`), `status` (nilai enum persis). FE tidak memakai `id_rs` dan `status`: ia menyaring sendiri dari respons penuh (±30 baris), karena chip "Menelepon" di FE mewakili empat status (tabel di bagian "Sumber data FE").

```json
{
  "bulan": "2026-08",
  "angka": {
    "pasien_aktif": 300, "terpicu": 30, "sudah_ditelepon": 4, "tidak_sesuai": 2, "rs_perlu_klarifikasi": 0,
    "antre": 26, "menunggu_keputusan": 2
  },
  "pengaturan": {
    "mode_otomatis": false, "jeda": false, "jam_mulai": "09:00", "jam_selesai": "17:00",
    "jeda_wa_menit": 1, "jeda_percobaan_menit": 2,
    "dalam_jam": true, "waktu_server": "2026-10-06T09:20:00+07:00"
  },
  "daftar_rs": [
    { "id_rs": "RS01", "nama": "RS Melati Sehat" },
    { "id_rs": "RS02", "nama": "RSU Bakti Mulia" }
  ],
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
      "keputusan_tindakan": null,
      "prioritas": false,
      "percobaan": 0
    }
  ]
}
```

- Hanya pasien dengan ≥2 indikator (R1.2). S7 tidak pernah muncul.
- `penerima` mengikuti R1.3: keluarga bila `hubungi_keluarga`, selain itu peserta.
- `angka` dihitung dari seluruh antrean bulan itu, tidak terpengaruh query. `sudah_ditelepon` = jumlah panggilan berstatus `selesai` atau `tidak_terhubung`. `tidak_sesuai` = jumlah berlabel `tidak_sesuai`. `antre` = jumlah berstatus `antre`. `menunggu_keputusan` = berlabel `tidak_sesuai` dan belum punya keputusan (lencana di menu).
- `pengaturan` = isi `GET /pengaturan` ditambah `dalam_jam` dan `waktu_server` (jam server; FE memakainya untuk tanggal di Beranda).
- `daftar_rs` = semua RS (termasuk yang tidak punya pasien terpicu), untuk pilihan filter.
- `label` terisi bila status `selesai` atau `tidak_terhubung`. `keputusan_tindakan` = `tindakan` keputusan terkini (enum `tindakan`) atau `null` bila belum diputuskan.
- Urutan: sedang berjalan (`wa_terkirim` … `membaca_jawaban`), lalu `prioritas`, lalu `antre` (urut `id` dengan collation biner, sehingga `P-S1`…`P-S8` mendahului `P0002`…), lalu `selesai`/`tidak_terhubung` (terbaru dulu). Agen mengambil tugas dengan urutan yang sama.

## `GET /api/v1/panggilan/{id}`

Dipakai layar Panggilan berlangsung (polling 1 detik) dan Kartu bukti. Contoh S1 setelah selesai:

```json
{
  "id": "CALL-P-S1-2026-08",
  "sumber": "panggilan",
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
  "waktu": "2026-10-06T10:12:08+07:00",
  "log": [
    { "status": "wa_terkirim", "waktu": "2026-10-06T10:11:00+07:00", "percobaan": 1, "catatan": null },
    { "status": "menelepon", "waktu": "2026-10-06T10:12:00+07:00", "percobaan": 1, "catatan": null },
    { "status": "tersambung", "waktu": "2026-10-06T10:12:08+07:00", "percobaan": 1, "catatan": null },
    { "status": "merekam", "waktu": "2026-10-06T10:12:08+07:00", "percobaan": 1, "catatan": null },
    { "status": "membaca_jawaban", "waktu": "2026-10-06T10:13:40+07:00", "percobaan": 1, "catatan": null },
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
  "toleransi": 2,
  "saran": "klarifikasi",
  "rekaman": "/api/v1/panggilan/CALL-P-S1-2026-08/rekaman",
  "hapus_pada": null,
  "konteks_rs": { "rs": "RS01", "tidak_sesuai": 3, "terjawab": 5, "status": "Perlu klarifikasi RS" },
  "pesan_wa": {
    "dari": "0800-0000-0165",
    "pemberitahuan": "Halo Andi Pratama. Ini BPJS Kesehatan. Dalam 1 menit kami akan menelepon dari nomor 0800-0000-0165 untuk konfirmasi singkat layanan fisioterapi Andi Pratama di RS Melati Sehat bulan Agustus. Ini bukan tagihan. Kami tidak akan meminta data pribadi, kode OTP, atau pembayaran. Untuk memastikan pesan ini, hubungi Care Center 165.",
    "cadangan": null
  },
  "keputusan": null,
  "galat_pembaca": null
}
```

- Selama panggilan berlangsung, `jawaban`, `label`, `alasan`, `selisih`, `saran`, `rekaman` bernilai `null`, sedangkan `transkrip` bertambah dan `tangkapan_sementara` boleh terisi (lihat B1). Setelah status `selesai`, `tangkapan_sementara` kembali `null`.
- `transkrip` di contoh dipotong; respons berisi semua baris. `transkrip` kosong bila tidak disimpan: label selain `sesuai`/`tidak_sesuai`, sudah lewat `hapus_pada`, atau `sumber` = `sintetis-riwayat`.
- `sumber`: `panggilan` atau `sintetis-riwayat` (riwayat latar demo, tanpa rekaman, transkrip, dan log). FE memakainya untuk teks "riwayat latar sebelum demo".
- `waktu` = waktu panggilan dimulai: `waktu_mulai` (saat `tersambung`); bila tidak pernah tersambung (S5), waktu log `menelepon` pertama; `null` bila belum ada percobaan.
- `durasi` = detik, nilai kiriman agen (`durasi` di `POST …/hasil`); `null` bila tidak pernah tersambung.
- `selisih` = `max(0, ditagih − jumlah_maks)`, `null` bila `jumlah_maks` kosong. `toleransi` = `TOLERANSI_SESI` di `aturan.py` (2), dikirim supaya FE tidak punya salinan aturan.
- `rekaman` `null` untuk label selain `sesuai` dan `tidak_sesuai`, atau bila sudah lewat `hapus_pada` (R5.5). Nilainya path relatif; FE menambahkan alamat dasar API.
- `jawaban` selalu terisi saat status `selesai` atau `tidak_terhubung`. Untuk `tidak_terhubung` pembaca tidak dipanggil: API menyusun `{"status_panggilan": "tidak_terhubung", "penerima": null, "hubungan": null, "hadir": null, "jumlah_min": null, "jumlah_maks": null, "keyakinan": null, "tanda_bahaya": [], "membantah_tanggal_libur": null, "kutipan_kunci": "", "ringkasan": "Panggilan tidak diangkat 2 kali."}`. Key yang tidak ada pada baris lama (riwayat tanpa `membantah_tanggal_libur`) dilengkapi `null`. `versi_pembaca` ikut tersimpan di dalam `jawaban`; FE mengabaikannya.
- `alasan` dari `aturan.py` apa adanya, untuk S2: `Ada pernyataan berisiko: tanda_tangan_tanpa_layanan.` FE menampilkan nama tanda bahaya dengan mengganti kode di teks itu; isi di API tidak diubah (uji E membandingkan dengan `expected_alasan`).
- `konteks_rs` = ringkasan RS terkini untuk RS panggilan ini (dipakai teks saran di kartu bukti).
- `pesan_wa.pemberitahuan` = Lampiran B persis (sumber yang sama dengan `wa.teks` di `agen/ambil`), `pesan_wa.cadangan` = teks chat cadangan, hanya terisi untuk label `tidak_terhubung`; `dari` = nomor penelepon di konfigurasi API (`NOMOR_PENELEPON`). FE memakainya untuk mockup WA.
- `keputusan` berisi objek seperti di `GET /keputusan` (tanpa field gabungan) bila sudah diputuskan.
- Identitas penerima tidak ikut dalam data apa pun yang dibagikan ke RS (R5.6); endpoint ini hanya untuk verifikator.

Galat: `404 panggilan_tidak_ada`.

## `GET /api/v1/panggilan/{id}/rekaman`

Audio rekaman (`audio/webm`), mendukung `Range`. Galat: `404 rekaman_tidak_ada` (belum ada, label tanpa rekaman, atau sudah dihapus).

## `POST /api/v1/panggilan/{id}/mulai`

"Telepon sekarang" dari baris antrean. Body kosong. Menandai `prioritas = true`; agen mengambilnya di giliran berikutnya walau mode otomatis mati atau dijeda. Batas jam tetap berlaku.

Balasan `200`: baris antrean (bentuk sama dengan `baris[]`). Galat: `404 panggilan_tidak_ada`, `409 bukan_antre` (status bukan `antre`).

## `POST /api/v1/panggilan/{id}/keputusan`

```json
{ "ikut_saran": false, "tindakan": "teruskan", "alasan": "Pola serupa sudah ditemukan di dua pasien lain RS ini." }
```

- `ikut_saran: true` → `tindakan` boleh dikosongkan; API memakai saran (bisa `pantau`). `alasan` opsional.
- `ikut_saran: false` → `tindakan` wajib salah satu `tutup`, `klarifikasi`, `teruskan` dan tidak boleh sama dengan saran (`422 tindakan_sama_saran`); `alasan` wajib, tidak boleh kosong (R5.3).
- Hanya untuk status `selesai` atau `tidak_terhubung`. Keputusan baru menggantikan yang lama (yang lama tetap di riwayat). Tombol "Ubah keputusan" di FE hanya membuka pilihan; keputusan lama baru tergantikan saat yang baru disimpan.

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

Galat: `422 alasan_wajib`, `422 tindakan_tidak_dikenal`, `422 tindakan_sama_saran`, `409 belum_selesai`, `404 panggilan_tidak_ada`.

## `GET /api/v1/keputusan`

Riwayat keputusan, terbaru dulu, termasuk yang sudah tergantikan. Setiap butir = objek keputusan di atas ditambah `terkini`, `pasien`, `umur`, `rs`, `nama_rs`, `label`. `terkini: true` untuk keputusan terbaru tiap panggilan; layar Riwayat di FE hanya menampilkan butir `terkini`.

```json
[
  {
    "id": 12, "panggilan_id": "CALL-P-S1-2026-08", "verifikator": "R. Santoso",
    "tindakan": "klarifikasi", "ikut_saran": true, "alasan": null, "waktu": "2026-10-06T10:15:20+07:00",
    "terkini": true, "pasien": "Andi Pratama", "umur": 54, "rs": "RS01", "nama_rs": "RS Melati Sehat", "label": "tidak_sesuai"
  }
]
```

## `GET /api/v1/ringkasan-rs`

Query opsional: `bulan` (bawaan `2026-08`).

```json
{
  "bulan": "2026-08",
  "aturan": "Perlu klarifikasi RS jika tidak sesuai >= 3 DAN rasio tidak sesuai/terjawab >= 10%",
  "panggilan_selesai": 5,
  "rs": [
    {
      "id_rs": "RS01", "nama": "RS Melati Sehat",
      "aktif": 68, "terpicu": 27, "persen": 39.7,
      "sesuai": 2, "tidak_sesuai": 3, "tidak_yakin": 0, "tidak_terhubung": 0, "menolak": 0,
      "terjawab": 5, "rasio": 0.6, "status": "Perlu klarifikasi RS",
      "panggilan": [
        { "id": "CALL-P-S1-2026-08", "pasien": "Andi Pratama", "label": "tidak_sesuai", "ditagih": 11, "jumlah_min": 3, "jumlah_maks": 3, "selisih": 8 },
        { "id": "CALL-LATAR-003", "pasien": "Ani Siregar", "label": "sesuai", "ditagih": 9, "jumlah_min": 8, "jumlah_maks": 10, "selisih": 0 }
      ]
    }
  ]
}
```

- `terjawab` = `sesuai + tidak_sesuai`. `panggilan_selesai` = jumlah panggilan `selesai` atau `tidak_terhubung` bulan itu. Contoh di atas adalah keadaan setelah S1; sebelum S1, RS01 `tidak_sesuai: 2, terjawab: 4, status: "Normal"` (`expected_ringkasan_rs.json`). `rs` memuat kelima RS, yang belum punya panggilan bernilai nol.
- `panggilan` = daftar panggilan selesai RS itu (terbaru dulu, dipotong di contoh), untuk rincian "Lihat kartu". `jumlah_min`, `jumlah_maks`, `selisih` bernilai `null` untuk label `menolak` dan `tidak_terhubung`. Nama pasien hanya untuk verifikator (R5.6).

## `GET /api/v1/pengaturan` dan `PUT /api/v1/pengaturan`

```json
{ "mode_otomatis": true, "jeda": false, "jam_mulai": "09:00", "jam_selesai": "17:00", "jeda_wa_menit": 1, "jeda_percobaan_menit": 2 }
```

`PUT` menerima sebagian field. Tombol "Panggilan otomatis: AKTIF/NONAKTIF" di FE = `PUT {"mode_otomatis": true|false}`; tombol Jeda/Lanjutkan = `PUT {"jeda": true|false}`.

- `mode_otomatis` diubah ke nilai apa pun → `jeda` otomatis `false`.
- `jeda: true` hanya sah bila `mode_otomatis` true; selain itu `422 pengaturan_tidak_valid`.
- `jeda` menahan pengambilan tugas otomatis. Panggilan yang sedang berjalan diselesaikan dulu; "Telepon sekarang" tetap diambil.

Galat: `422 pengaturan_tidak_valid`.

## `POST /api/v1/demo/reset`

Mengembalikan panggilan, log, dan keputusan ke keadaan awal demo (4 riwayat selesai, 26 antre, mode otomatis mati, `jeda` mati). Data master (RS, peserta, klaim, indikator) tidak disentuh. Rekaman hasil panggilan baru ikut dihapus. Balasan `200 {"ok": true}`.

## `GET /api/v1/kesehatan`

```json
{ "api": "ok", "db": "ok", "pembaca": "ok", "versi_aturan": "2026.10" }
```

Bila `db` tidak ok, FE memakai `data-v3.js` (mode cadangan).

---

# Sumber data FE (keputusan konstanta FE vs API)

Hasil review KT-06 terhadap `app-v3.js` dan isi `DATA3` di `data-v3.js`. Aturan: yang dikirim ke penerima atau dihitung aturan datang dari API; nama tampilan dan teks penjelasan tetap konstanta FE.

**Dari API** (adaptor FE menyesuaikan bentuk):

| `DATA3` / isian FE | Sumber di Kontrak A |
|---|---|
| `HARI_INI` | `antrean.pengaturan.waktu_server`, diformat FE |
| `BULAN`, `BULAN_PENDEK` | `bulan` (`2026-08`); nama bulan Indonesia = konstanta FE |
| `JEDA_PESAN_MENIT` | `pengaturan.jeda_wa_menit` |
| `NOMOR_PENELEPON` | `panggilan.pesan_wa.dari` |
| `RS` (`id`, `nama`) | `antrean.daftar_rs` |
| `RS` (`aktif`, `terpicu`, `persen`) | `ringkasan-rs.rs[]` |
| `PASIEN_AKTIF`, `PASIEN_TERPICU` | `antrean.angka.pasien_aktif`, `antrean.angka.terpicu` |
| kartu angka, lencana menu, jumlah menunggu di Beranda | `antrean.angka` (`sudah_ditelepon`, `tidak_sesuai`, `rs_perlu_klarifikasi`, `menunggu_keputusan`, `antre`) |
| `SKENARIO`/`LATAR`/`MENGANTRE`/`SEMUA` (per pasien) | `antrean.baris[]` dan `panggilan/{id}`: `tanggal` ISO (FE mengambil tanggalnya), `tanda_tanggal` berkunci ISO, `penerima`, `durasi`, `rekaman`, `jawaban`, `label`, `alasan` |
| `URUTAN_ANTREAN` | urutan `baris[]` |
| `waktu` (`LATAR`), waktu kartu dan cap waktu progres | `panggilan.waktu` dan `log[].waktu` |
| jam di kolom Progres | `log[].waktu` per `status`; S5: baris `menelepon` ber-`catatan` `tidak_diangkat` = gagal, baris `tidak_terhubung` = chat cadangan terkirim |
| `transkrip` `[A/P, detik, teks]` | objek `{detik, pembicara, teks}` (`A` = `ai`, `P` = `penerima`) |
| `tangkap` (indeks baris) | tidak ada di API; panel "Yang ditangkap AI" memakai `tangkapan_sementara` |
| `SARAN` | `panggilan.saran` |
| `TOLERANSI` | `panggilan.toleransi` |
| `selisih()`, `hitungLabel()`, `ringkasanRs()` | `selisih`, `label`, `ringkasan-rs` (dihitung API) |
| `pesanPemberitahuan()`, `pesanCadangan()` | `panggilan.pesan_wa.pemberitahuan`, `.cadangan` |
| `VERIFIKATOR.nama` | `keputusan.verifikator` (nama sama dengan konstanta FE) |

**Tetap konstanta FE** (tidak dikirim API):

| Konstanta | Alasan |
|---|---|
| `LABEL[*].nama`, `TINDAKAN[*].nama`/`akibat`/`status`, `PILIHAN_TINDAKAN` | Nama dan teks tampilan; API hanya mengirim kode enum |
| `INDIKATOR[*].nama`/`arti` | Nama tampilan chip; API mengirim `I1`–`I4` |
| `STATUS` (peta chip status) | Lihat tabel kelompok status di bawah |
| `TANDA_BAHAYA` (nama tampil tiga kode) | Teks tampilan |
| `RETENSI[label]` | Teks penjelasan R5.5 per label; tanggal pasti ada di `hapus_pada` |
| Teks penjelasan di mockup WA ("10 menit di produksi", "2 jam di produksi"), aturan RS di Ringkasan RS, catatan kaki, "Layanan: Fisioterapi" | Teks penjelasan, bukan data |
| `VERIFIKATOR.peran`, `.kantor` | Prototipe tanpa login; produksi dari profil login |
| Banner "Setelah panggilan Andi Pratama (S1) …" di Ringkasan RS | Narasi demo; tampil bila `CALL-P-S1-2026-08` selesai |
| `TIDAK_DIPICU` (S7) | Hanya uji mandiri FE. API menjamin S7 tidak ada di `baris` (R1.2); diuji di bagian E |

**Hanya simulasi** (hilang saat FE disambung ke API): `SIM`, `titik()`, `statusSim()`, `tangkap`, `UJI`, pintasan Alt+L, jeda 12 detik antar panggilan otomatis, `rekaman` placeholder `assets/rekaman/*.wav`. Perilaku nyata di API: baris `antre` mana pun bisa ditelepon lewat `POST …/mulai`, dan API tidak mematikan mode otomatis sendiri bila antrean habis.

**Kelompok status tampilan** (chip di tabel antrean):

| `status` API | Chip FE | Kunci `STATUS` FE |
|---|---|---|
| `antre` | Antre | `antre` |
| `wa_terkirim` | WA terkirim | `wa` |
| `menelepon`, `tersambung`, `merekam`, `membaca_jawaban` | Menelepon | `menelepon` |
| `selesai` | Selesai | `selesai` |
| `tidak_terhubung` | Tidak terhubung | `tidak_terhubung` |

**Panel "Yang ditangkap AI"** (enam isian) mengambil dari `tangkapan_sementara` selama panggilan dan dari `jawaban` setelah selesai. Key yang belum ada tampil "–".

| Isian | Field |
|---|---|
| Penerima | `penerima` (+ `hubungan`) |
| Hadir | `hadir` |
| Jumlah sesi | `jumlah_min`, `jumlah_maks` |
| Keyakinan | `keyakinan` |
| Tanggal libur | `membantah_tanggal_libur` |
| Tanda bahaya | `tanda_bahaya` |

---

# Kontrak B1: agen suara ↔ API (`/api/v1`)

Semua endpoint di bagian ini wajib header `X-Kunci-Agen: <AGEN_KEY dari backend/.env>`. Tanpa atau salah → `401 kunci_salah`. Halaman agen berjalan di origin sendiri (mis. `http://localhost:5173`); origin itu ditambahkan ke `CORS_ORIGINS`. Prototipe: kunci terlihat di browser dan ini diterima (produksi: token per perangkat).

## `POST /api/v1/agen/ambil`

Body kosong. Agen memanggil tiap 3 detik saat menganggur.

- `204`: tidak ada tugas (mode mati atau dijeda dan tidak ada prioritas, di luar jam, ada panggilan lain berjalan, atau antrean kosong/menunggu `coba_lagi_setelah`).
- `200`: satu tugas. Prioritas dulu, lalu `antre` dengan urutan `id` (sama dengan `GET /antrean`). API langsung mengunci panggilan itu (`diambil_pada`; status tetap `antre` sampai agen melapor; kunci lepas otomatis setelah 5 menit tanpa laporan).

```json
{
  "id": "CALL-P-S1-2026-08",
  "percobaan": 1,
  "no_tujuan": "08xxxxxxxxxx",
  "skrip": {
    "nama_penerima": "Andi Pratama",
    "sapaan_penerima": "Bapak",
    "hubungan": "peserta",
    "nama_pasien": "Andi Pratama",
    "sapaan_pasien": "Bapak",
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

- `percobaan` = percobaan ke-n yang akan dijalankan (`panggilan.percobaan + 1`). Nilai di DB naik saat agen melapor `menelepon`, bukan saat tugas diambil, supaya kunci yang kedaluwarsa tidak menghabiskan percobaan.
- `no_tujuan` prototipe = `NOMOR_PENGUJI` dari `.env` (R2.1), disimpan di `panggilan.no_tujuan`. `wa.tautan` memakai nomor itu dalam format `62…`.
- `skrip` mengisi variabel Lampiran A (R3.1). `hubungan` salah satu `peserta`, `anak`, `orang tua`, `pasangan`. `tanggal_libur` kosong bila I4 tidak aktif; agen tidak bertanya soal libur (S3).
- `sapaan_pasien` (`Bapak`/`Ibu`) dari `peserta.jenis_kelamin` pasien (`L` → Bapak, `P` → Ibu). `sapaan_penerima` sama dengan `sapaan_pasien` bila penerima peserta; bila keluarga, `Bapak/Ibu` karena jenis kelamin keluarga tidak tercatat, dan agen boleh menyesuaikan dari `nama_penerima`. Contoh S2: `sapaan_pasien: "Ibu"`, `sapaan_penerima: "Bapak/Ibu"`, `hubungan: "anak"`.
- `wa.teks` = Lampiran B persis (R2.3), tanpa tautan di dalam teks. `wa.lewati = true` pada percobaan ke-2 (pemberitahuan cukup sekali); `wa.teks` dan `wa.tautan` tetap terisi.
- `batas_detik` = batas panggilan 2,5 menit (R3.3, Lampiran A).

## `POST /api/v1/panggilan/{id}/status`

```json
{ "laporan": "wa_terkirim", "waktu": "2026-10-06T10:11:00+07:00", "catatan": null }
```

| `laporan` | Akibat di API |
|---|---|
| `wa_terkirim` | status `wa_terkirim`, `waktu_wa` diisi, log |
| `menelepon` | status `menelepon`, `percobaan` naik 1, log. Percobaan ke-1: bila belum lewat `jeda_wa_menit` sejak `waktu_wa` → `409 jeda_belum_lewat`. Percobaan ke-2: tanpa pemeriksaan jeda WA |
| `tersambung` | status `tersambung`, `waktu_mulai` diisi, log |
| `merekam` | status `merekam`, log |
| `tidak_diangkat` | log `menelepon` dengan `catatan = "tidak_diangkat"`. Percobaan ke-1: status kembali `antre`, `coba_lagi_setelah = sekarang + jeda_percobaan_menit`. Percobaan ke-2: status `tidak_terhubung`, label `Tidak terhubung` (R3.5), `jawaban` disusun API (lihat `GET /panggilan/{id}`), `waktu_selesai` diisi |
| `chat_cadangan_terkirim` | `chat_cadangan_terkirim = true`, log `tidak_terhubung` dengan catatan |

Urutan laporan yang sah (selain itu `409 urutan_salah`):

| Dari status | Laporan yang boleh |
|---|---|
| `antre`, percobaan ke-1 | `wa_terkirim` |
| `wa_terkirim` | `menelepon` |
| `antre`, percobaan ke-2 (WA dilewati) | `menelepon` |
| `menelepon` | `tersambung`, `tidak_diangkat` |
| `tersambung` | `merekam` |
| `tidak_terhubung` | `chat_cadangan_terkirim` |

`log[].percobaan` = nomor percobaan yang sedang dijalankan.

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

Galat: `404 panggilan_tidak_ada`, `409 urutan_salah`, `409 jeda_belum_lewat`, `422 laporan_tidak_dikenal`.

## `POST /api/v1/panggilan/{id}/transkrip`

Dikirim selama panggilan (mis. tiap giliran bicara selesai). Baris ditambahkan, bukan diganti.

```json
{
  "baris": [{ "detik": 45, "pembicara": "penerima", "teks": "Tiga kali. Awal bulan, pertengahan, terus sekali lagi tanggal dua puluhan." }],
  "tangkapan_sementara": { "penerima": "peserta", "hadir": true, "jumlah_min": 3, "jumlah_maks": 3 }
}
```

`tangkapan_sementara` opsional, bentuk = sebagian field jawaban pembaca (`penerima`, `hubungan`, `hadir`, `jumlah_min`, `jumlah_maks`, `keyakinan`, `membantah_tanggal_libur`, `tanda_bahaya`), hanya untuk panel "Yang ditangkap AI" selama panggilan (R5.1). Tiap kiriman menggantikan yang sebelumnya. Tidak pernah dipakai untuk label. Balasan `204`. Galat: `409 bukan_berlangsung` (status bukan `tersambung`/`merekam`).

## `POST /api/v1/panggilan/{id}/hasil`

`multipart/form-data`:

| Field | Isi |
|---|---|
| `rekaman` | File `.webm` dua arah (MediaRecorder, Lampiran C langkah 5). Opsional bila penerima menolak sebelum direkam |
| `transkrip` | JSON string, transkrip final lengkap (menggantikan baris sementara). `[]` sah |
| `durasi` | Detik, bilangan bulat |

Balasan `202 {"status": "membaca_jawaban"}`. Di latar belakang API:

1. Simpan rekaman di `backend/uploads/rekaman/<id>.webm` (`rekaman_path` relatif), transkrip di DB, `durasi` ke `durasi_detik`, `waktu_selesai` = waktu hasil diterima. Log `membaca_jawaban`.
2. Panggil `POST /v1/baca` (Kontrak B2). Galat `502`, `504`, timeout, atau JSON tidak lolos skema → ulang 1 kali. `422 transkrip_kosong` tidak diulang.
3. Hitung label dengan `aturan.py`, simpan `jawaban`, `label`, `alasan`, `hapus_pada` (R5.5: `sesuai` → `waktu_selesai` + 30 hari; `tidak_sesuai` → `null` sampai `klarifikasi_selesai_pada`; lainnya → rekaman (file dihapus) dan transkrip tidak disimpan). `tangkapan_sementara` dikosongkan.
4. Status `selesai`, log `selesai`.

Galat: `404 panggilan_tidak_ada`, `409 bukan_berlangsung`, `413 terlalu_besar` (rekaman > 10 MB), `422 transkrip_tidak_valid`.

## Cakupan `perilaku_ai_wajib` (R3.2)

Perilaku yang butuh data dari API harus ada di `skrip`; sisanya ada di instruksi sistem agen (Lampiran A), bukan di kontrak.

| Skenario | Perilaku | Sumber |
|---|---|---|
| S1 | Menyebut nama penerima untuk memastikan identitas | `skrip.nama_penerima`, `sapaan_penerima` |
| S1 | Menyebut nama RS dan bulan layanan | `skrip.nama_rs`, `skrip.bulan` |
| S1 | Menanyakan tanggal libur (16 dan 17 Agustus) | `skrip.tanggal_libur` |
| S3 | Tidak menanyakan libur bila I4 tidak aktif | `skrip.tanggal_libur` kosong |
| S2, S4 | Menelepon keluarga dan menyapa "keluarga Ibu Siti" | `skrip.hubungan`, `nama_pasien`, `sapaan_pasien` |
| S5 | Dua percobaan lalu chat WA berisi pilihan jawaban | aturan `tidak_diangkat`, `chat_cadangan` di balasan `status` |
| S1–S8 | Pembuka rekaman dan bukan tagihan, satu pertanyaan per giliran, mengulang jawaban, penutup tidak memengaruhi layanan atau iuran, tidak meminta NIK/OTP/uang | Lampiran A (statis) |
| S2, S4, S6, S8 | Tidak menuduh RS, tidak mendesak, bahasa santai, menyebut Care Center 165 atau Mobile JKN, menawarkan sekali | Lampiran A (statis) |
| S7 | Tidak dipicu | R1.2, tidak ada di antrean |

---

# Kontrak B2: API ↔ pembaca jawaban (`ai-service`, `/v1`)

Endpoint baru di `ai-service` milik Zahra, di samping `/v1/analisis` dan `/v1/bandingkan` (v2, dibiarkan). Header `X-Kunci-Layanan` (sama dengan v2; `KUNCI_MESIN` di backend, `AI_SERVICE_KEY` di `ai-service`). Kunci salah → `401 kunci_salah`.

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
- `membantah_tanggal_libur` bernilai `null` bila `tanggal_libur` kosong.
- Transkrip kosong → selalu `422 transkrip_kosong` (bukan `status_panggilan` tebakan). Panggilan `tidak_terhubung` tidak sampai ke pembaca.

Galat pembaca: `422 transkrip_kosong`, `502 llm_gagal`, `504 batas_waktu`. Penanganan di API: batas waktu 30 detik; `502`, `504`, timeout, atau JSON tidak lolos validasi skema → ulang 1 kali; tetap gagal atau `422` → label `tidak_yakin`, pesan galat disimpan di `galat_pembaca` (R4.3).

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
2. Setelah lewat, ambil lagi (`percobaan: 2`, `wa.lewati: true`) → `menelepon` → `tidak_diangkat` → status `tidak_terhubung`, label `tidak_terhubung`, `jawaban` disusun API, balasan berisi `chat_cadangan`.
3. Agen membuka tautan chat, operator kirim, agen `status chat_cadangan_terkirim`. Tidak dihitung di ringkasan RS.

## S8 (Menolak)

Panggilan tersambung, penerima curiga penipuan, AI menenangkan sekali lalu menutup. Agen mengirim `hasil` (rekaman boleh ada). Pembaca → `status_panggilan: "menolak"` → label `menolak`, saran Pantau, rekaman dan transkrip tidak disimpan, tidak dihitung.

---

# Pemetaan kontrak ↔ DB (`backend/db/schema_v3.sql`)

Kolom langsung:

| Kontrak | DB |
|---|---|
| `id` | `panggilan.id` |
| `sumber` | `panggilan.sumber` |
| `pasien`, `umur` | `peserta.nama`, `peserta.umur` lewat `panggilan.id_peserta` |
| `rs`, `nama_rs` | `panggilan.id_rs`, `rumah_sakit.nama_rs` |
| `bulan` | `panggilan.bulan_layanan` |
| `ditagih` | `panggilan.sesi_ditagih` |
| `indikator`, `tanggal_libur` | `indikator_bulanan` (`i1_…`–`i4_…`, `tanggal_libur`) |
| `penerima.nama`, `penerima.hubungan` | `panggilan.nama_penerima`, `panggilan.hubungan` (`peserta` bila `panggilan.penerima = 'peserta'`) |
| `status`, `percobaan`, `prioritas` | `panggilan.status`, `.percobaan`, `.prioritas` |
| `coba_lagi_setelah` | `panggilan.coba_lagi_setelah` |
| `log[]` | `panggilan_log` (`status`, `waktu`, `percobaan`, `catatan`) |
| `transkrip` | `panggilan.transkrip` (objek `{detik, pembicara, teks}`) |
| `tangkapan_sementara` | `panggilan.tangkapan_sementara` (kolom baru) |
| `waktu` | `panggilan.waktu_mulai`; bila `null`, waktu log `menelepon` pertama |
| `durasi` | `panggilan.durasi_detik` (kolom baru) |
| `jawaban` | `panggilan.jawaban` |
| `label` | `panggilan.label` (`Tidak sesuai` ↔ `tidak_sesuai`, dst.) |
| `alasan` | `panggilan.alasan` |
| `hapus_pada`, `galat_pembaca`, `no_tujuan` | kolom bernama sama |
| `chat_cadangan` terkirim | `panggilan.chat_cadangan_terkirim` |
| `keputusan` | `keputusan_panggilan` (`tutup` ↔ `tutup_kasus`, `klarifikasi` ↔ `minta_klarifikasi_rs`, `teruskan` ↔ `teruskan_pk_jkn`, `pantau` ↔ `pantau`) |
| `pengaturan` (`mode_otomatis`, `jeda`, `jam_mulai`, `jam_selesai`, `jeda_wa_menit`, `jeda_percobaan_menit`) | `pengaturan` (kunci-nilai) |
| kunci ambil agen | `panggilan.diambil_pada` (kolom baru) |
| `skrip.sapaan_*` | `peserta.jenis_kelamin` |

Turunan (tanpa kolom sendiri):

| Kontrak | Dihitung dari |
|---|---|
| `tanggal`, `tanda_tanggal` | `klaim_sesi.tanggal` (pasien, RS, bulan) + hari Minggu + `libur_nasional` |
| `selisih`, `saran` | `jawaban.jumlah_maks` dan `sesi_ditagih`; peta label → tindakan |
| `toleransi` | `aturan.TOLERANSI_SESI` |
| `rekaman` | `rekaman_path` bila label `sesuai`/`tidak_sesuai` dan `hapus_pada` kosong atau belum lewat |
| `konteks_rs`, `ringkasan-rs` (hitungan, `rasio`, `status`, `panggilan[]`) | `aturan.ringkasan_rs` atas panggilan `selesai`/`tidak_terhubung` per RS |
| `aktif`, `terpicu`, `persen`, `angka.pasien_aktif`, `angka.terpicu` | hitungan `indikator_bulanan` per bulan (`dipicu`) |
| `angka.*`, `keputusan_tindakan`, `daftar_rs`, `terkini` | hitungan `panggilan`, `keputusan_panggilan`, `rumah_sakit` |
| `skrip.*`, `wa.*`, `pesan_wa.*` | `peserta`, `rumah_sakit`, `indikator_bulanan` + template Lampiran B + `NOMOR_PENGUJI`, `NOMOR_PENELEPON` (`.env`) |
| `batas_detik`, `versi_aturan`, `dalam_jam`, `waktu_server` | konfigurasi dan jam API |

Kolom DB yang tidak dipakai kontrak ini: `jawaban_chat` (balasan chat cadangan belum dibaca di prototipe), `klarifikasi_selesai_pada` (endpoint "klarifikasi selesai" dan penghapusan terjadwal dikerjakan di bagian F), `waktu_wa` (hanya aturan jeda), `jeda_wa_menit` per panggilan (salinan `pengaturan.jeda_wa_menit` saat tugas diambil).

Perubahan skema yang dibutuhkan kontrak ini (dikerjakan di bagian D):

- `keputusan_panggilan.tindakan` mengizinkan `pantau`.
- Kunci ambil agen: kolom `diambil_pada timestamptz` di `panggilan` (lepas otomatis setelah 5 menit).
- Kolom `tangkapan_sementara jsonb` di `panggilan` (panel "Yang ditangkap AI" selama panggilan; dikosongkan saat `selesai`).
- Kolom `durasi_detik int` di `panggilan` (kiriman `durasi` dari agen; `waktu_selesai − waktu_mulai` tidak cukup tepat).
- Baris `pengaturan`: `jeda` = `false` (tombol Jeda terpisah dari mode otomatis).
- Komentar kolom `panggilan.transkrip` di `schema_v3.sql` diperbaiki dari `[{waktu, pembicara, teks}]` menjadi `[{detik, pembicara, teks}]`.

Perubahan seed riwayat (`seed_v3.py`, empat baris `CALL-LATAR-001`…`004`), supaya sama dengan data demo FE:

- Penerima mengikuti R1.3 (pakai `tentukan_penerima`), bukan kolom `penerima` di berkas riwayat: `CALL-LATAR-001` (Bayu Utami, 5 tahun) dan `CALL-LATAR-004` (Ratna Handayani, 8 tahun) → keluarga, `orang tua`; `jawaban.penerima` dan `jawaban.hubungan` disesuaikan.
- `waktu_mulai` per baris, bukan satu `WAKTU_RIWAYAT` untuk semuanya: 2026-10-05 09:42, 10:05, 10:31, 11:18 (+07:00). `durasi_detik` 84, 71, 66, 74; `waktu_selesai = waktu_mulai + durasi_detik`; `hapus_pada` baris `sesuai` = `waktu_selesai` + 30 hari.

# Mode cadangan

- Pembaca mati → label `tidak_yakin` dengan `galat_pembaca`, demo tetap jalan.
- API atau DB mati → FE memakai `data-v3.js` (simulasi). Layar tidak pernah kosong.

# Jejak requirement (PIC I dan Z + I)

| Requirement | Dipenuhi oleh |
|---|---|
| R1.3 penerima | `penerima` di `GET /antrean`, `skrip` di `agen/ambil` |
| R1.4 layar Antrean | `GET /antrean` |
| R1.5 mode otomatis, jam, Jeda | `PUT /pengaturan` (`mode_otomatis`, `jeda`), aturan `agen/ambil`, `POST …/mulai` |
| R2.1 pesan WA | `wa.teks` + `wa.tautan` di `agen/ambil` |
| R2.2 jeda pesan ke panggilan | `jeda_wa_menit`, `409 jeda_belum_lewat`, `panggilan_log` |
| R2.3 isi pesan | `wa.teks` = Lampiran B tanpa tautan; `pesan_wa` di `GET /panggilan/{id}` |
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
