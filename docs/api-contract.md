# Kontrak API Vedika Autentik

Dua kontrak, satu di tiap sambungan:

```
FE (Vercel, statis)
   │  Kontrak A: /api/v1   (hasil akhir siap tampil)
   ▼
API (FastAPI)  ◀── worker antrean ──▶ Supabase (Postgres + Storage + Auth)
   │  Kontrak B: /v1       (sinyal mentah)
   ▼
Mesin AI (PRAMANA, container terpisah, tanpa state)
```

| Pemilik | Kontrak | Pihak lain |
|---|---|---|
| BE (Imelda) | A | FE |
| AI engineering (Zahra) | B | BE |

## Prinsip

1. **FE tidak tahu mesin AI ada.** FE hanya bicara ke API.
2. **Label hanya dihitung di API**, memakai aturan PRD bagian 9 (`hitungLabel` di `data.js`). Mesin AI tidak pernah mengirim label atau saran tindakan.
3. **Mesin AI tanpa state.** Berkas masuk, temuan keluar. Penyimpanan, antrean, dan pencarian berkas kembar ada di API.
4. **Asinkron.** Upload langsung kembali dengan `status: "diproses"`. FE polling sampai `selesai` atau `gagal`.
5. **Gagal aman.** Berkas yang tidak bisa diproses menjadi `cek` (Perlu dicek), tidak pernah `lolos`. Scan jelek menjadi `ulang`, tidak pernah dihitung sebagai temuan.
6. **Bentuk objek hasil = JSON ground truth dataset** (`dataset/*/*.json`). FE sudah memakai bentuk ini, jadi sambungan ke API hampir tanpa ubahan.

## Konvensi

- Bahasa field mengikuti dataset (Indonesia, `snake_case`). Enum memakai nilai persis seperti di `data.js`.
- Koordinat `region` = `[x, y, lebar, tinggi]` dalam piksel pada **JPG ternormalisasi** berukuran `ukuran` (A4 150 dpi, `[1240, 1754]`). Mesin AI yang merender PDF ke JPG itu, API menyimpannya, FE menampilkannya.
- Waktu ISO 8601 dengan zona, mis. `2026-10-06T09:14:00+07:00`.
- Galat selalu berbentuk `{ "galat": { "kode": "berkas_terlalu_besar", "pesan": "…" } }` dengan status HTTP yang sesuai.
- Versi di path (`/v1`). Perubahan yang merusak = versi baru. Menambah field boleh tanpa naik versi, jadi penerima wajib mengabaikan field yang tidak dikenal.

### Enum

| Nama | Nilai |
|---|---|
| `status` | `diproses`, `selesai`, `gagal` |
| `label` | `prioritas`, `cek`, `ulang`, `lolos` |
| `kekuatan` | `kuat`, `sedang`, `lemah`, `info` |
| `cek` | `kualitas_scan`, `kecocokan_klaim`, `berkas_kembar`, `copy_paste`, `tempelan`, `suntingan`, `tanda_ai` |
| `tindakan` | `scanUlang`, `klarifikasi`, `telaah`, `wajar` |
| `kualitas_scan.status` | `baik`, `scan_ulang` |
| `jawaban` peserta | `1` Ya, `2` Tidak pernah, `3` Hanya sebagian |

Pemetaan label → saran: `lolos→wajar`, `ulang→scanUlang`, `cek→klarifikasi`, `prioritas→telaah`.

---

# Kontrak A: FE ↔ API (`/api/v1`)

Autentikasi: header `Authorization: Bearer <token Supabase>`. Peran: `verifikator`, `admin`. Demo memakai akun verifikator demo.

## `POST /api/v1/berkas`

Unggah satu berkas. `multipart/form-data`.

| Field | Tipe | Wajib | Catatan |
|---|---|---|---|
| `file` | file | ya | PDF, JPG, PNG. Maks 10 MB. |
| `kode_faskes` | string | ya | mis. `0901R014`. Konteks demo, bukan verifikasi asal dokumen. |
| `sep` | string | tidak | Bila kosong, API mencocokkan ke data klaim lewat `kode_faskes` + hasil OCR. |

Respons `202`:

```json
{ "id": "b_01HZX…", "status": "diproses", "diunggah": "2026-10-06T09:14:00+07:00" }
```

Galat: `400 format_tidak_didukung`, `413 berkas_terlalu_besar`, `422 faskes_tidak_dikenal`.

## `GET /api/v1/berkas/{id}`

Respons `200`. Selagi `status = "diproses"`, hanya `id`, `status`, `langkah` yang terisi.

```json
{
  "id": "b_01HZX…",
  "status": "selesai",
  "langkah": [
    { "nama": "Cek kualitas scan", "status": "ok", "hasil": "Terbaca, miring 0.4 derajat." },
    { "nama": "Baca isi berkas", "status": "ok", "hasil": "5 baris terisi, 4–18 Agustus 2026" },
    { "nama": "Cocokkan dengan klaim", "status": "temuan", "hasil": "Ditagih 8, berkas mendukung 5" }
  ],
  "label": "prioritas",
  "saran": "telaah",
  "alasan_saran": "Ada lebih dari satu sinyal kuat. Tim telaah perlu melihat kasus ini lebih dulu.",
  "ringkasan": "Hanya 5 baris terisi, angka jumlah kunjungan diubah dari 5 menjadi 8.",
  "klaim": {
    "sep": "0901R0140826V583301", "peserta": "Ratna Kusuma", "no_kartu": "0001611903327",
    "faskes": "RS Melati Sehat", "kode_faskes": "0901R014", "periode": "Agustus 2026",
    "layanan": "Fisioterapi rawat jalan", "sesi_ditagih": 8, "tarif_per_sesi": 207300,
    "nilai_klaim": 1658400, "nilai_klaim_teks": "Rp1.658.400"
  },
  "isi_lembar": {
    "nama": "Ratna Kusuma", "tanggal_lahir": "23-06-1966", "no_rm": "00-41-3380",
    "no_kartu": "0001611903327", "no_sep": "0901R0140826V583301",
    "diagnosis": "Gonartrosis bilateral", "icd10": "M17.0", "dpjp": "dr. Ayu Prameswari, Sp.KFR",
    "periode": "Agustus 2026", "baris_terisi": 5, "baris_asli": 5,
    "tanggal_sesi": ["04/08", "07/08", "11/08", "14/08", "18/08"],
    "jumlah_kunjungan_tertulis": 8, "kemiripan_ttd_rerata": 0.815
  },
  "kualitas_scan": { "status": "baik", "catatan": "Terbaca, miring 0.4 derajat." },
  "temuan": [
    { "cek": "kecocokan_klaim", "kekuatan": "kuat", "kalimat": "Ditagih 8 sesi, berkas hanya mendukung 5.", "region": [90, 1036, 1065, 283] },
    { "cek": "suntingan", "kekuatan": "sedang", "kalimat": "Angka 8 di kolom jumlah kunjungan terdeteksi ditempel di atas angka 5.", "region": [347, 1360, 29, 44] }
  ],
  "metadata_file": { "Producer": "Microsoft: Print To PDF", "Creator": "Adobe Photoshop 25.0", "ModDate": "2026-09-01T22:05:00" },
  "ukuran": [1240, 1754],
  "berkas": { "jpg": "https://…/b_01HZX/halaman-1.jpg", "pdf": "https://…/b_01HZX/asli.pdf", "sha256": "9f2c…" },
  "keluarga": null,
  "keputusan": null,
  "konfirmasi": null,
  "versi_aturan": "2026.09",
  "versi_mesin": "pramana-0.3.1",
  "diunggah": "2026-10-06T09:14:00+07:00"
}
```

Catatan field:

- `temuan[].pasangan` (id berkas) ada hanya untuk `berkas_kembar` dan `tempelan`. Dari situ `keluarga` dibangun: `{ "akar": "b_…", "anggota": ["b_…", "b_…"] }`, atau `null`.
- `temuan[].area` (opsional): daftar `region` bila satu temuan punya banyak kotak (mis. delapan tanda tangan).
- `temuan[].skor` (opsional, 0–1): keyakinan mesin, ditampilkan untuk sinyal lemah seperti `tanda_ai`.
- Bila `status = "gagal"`: `label = "cek"`, `temuan` memuat satu entri `kekuatan: "info"` berisi penyebab. Tidak pernah `lolos`.
- `berkas.jpg` dan `berkas.pdf` berupa URL bertanda tangan berumur pendek.
- `sha256` dihitung API dari berkas asli, bukan oleh mesin AI.

## `GET /api/v1/berkas`

Antrean. Parameter: `label` (`prioritas|cek|ulang|lolos`), `kode_faskes`, `q` (nama/SEP/id), `status`, `halaman` (default 1), `per_halaman` (default 25, maks 100). Urutan default: label (prioritas dulu), lalu waktu unggah terbaru.

```json
{
  "total": 17, "halaman": 1, "per_halaman": 25,
  "item": [
    { "id": "b_01HZX…", "status": "selesai", "label": "prioritas", "ringkasan": "…",
      "klaim": { "sep": "…", "peserta": "…", "faskes": "…", "sesi_ditagih": 8, "nilai_klaim": 1658400 },
      "baris_terisi": 5, "diunggah": "…", "keputusan": null }
  ]
}
```

## `POST /api/v1/berkas/{id}/keputusan`

```json
{ "tindakan": "telaah", "catatan": "Konfirmasi peserta: hanya sebagian." }
```

Aturan: `catatan` wajib bila `tindakan` berbeda dari `saran`. Respons `201` berisi objek `keputusan`:

```json
{ "tindakan": "telaah", "catatan": "…", "verifikator": "R. Santoso", "waktu": "2026-10-06T09:20:00+07:00",
  "laporan": { "nomor": "LT-VA/DST01/X/2026", "url": "/api/v1/berkas/b_01HZX…/laporan" } }
```

`laporan` hanya ada bila tindakan = `telaah`. `DELETE /api/v1/berkas/{id}/keputusan` membatalkan (tercatat di jejak, tidak menghapus).

## `GET /api/v1/berkas/{id}/laporan`

`application/pdf`. Berisi identitas klaim, temuan, potongan bukti, `sha256`, `versi_aturan`, dan keputusan. Dibuat di server, bukan cetak browser.

## `POST /api/v1/berkas/{id}/konfirmasi`

Hanya untuk label `prioritas`. Tanpa body. Demo: mengirim pesan PANDAWA tiruan. Produksi: WhatsApp Business API resmi BPJS. Respons `201`:

```json
{ "pertanyaan": "…teks pesan netral tanpa tautan…", "dikirim": "2026-10-06T09:14:00+07:00", "jawaban": null, "dijawab": null }
```

`POST /api/v1/berkas/{id}/konfirmasi/jawaban` dengan `{ "jawaban": 3 }` hanya aktif di mode demo.

## `GET /api/v1/berkas/{id}/jejak`

Kronologi: diunggah, diperiksa, label terbit, konfirmasi dikirim/dijawab, keputusan, laporan.

```json
[ { "waktu": "…", "judul": "Diunggah rumah sakit ke JKN Drive", "teks": "RS Melati Sehat · VA-DST-01.pdf" } ]
```

## `GET /api/v1/ringkasan`

Angka untuk beranda: per faskes `masuk`, `selesai`, `prioritas`, `cek`, `ulang`.

## `GET /api/v1/kesehatan`

`{ "api": "ok", "db": "ok", "mesin": "ok|lambat|mati" }`. FE memakai ini untuk memilih jalur cadangan (data manifest) saat mesin mati.

---

# Kontrak B: API ↔ Mesin AI (`/v1`)

Tanpa state, tanpa autentikasi pengguna. Dilindungi kunci layanan `X-Kunci-Layanan` yang hanya dipegang API. Target: di bawah 10 detik per berkas 1–2 halaman di CPU biasa.

## `POST /v1/analisis`

`multipart/form-data`:

| Field | Tipe | Catatan |
|---|---|---|
| `file` | file | PDF/JPG/PNG asli |
| `klaim` | JSON string | `{ "sep", "sesi_ditagih", "periode", "kode_faskes" }` untuk pemeriksaan kecocokan |
| `template` | string | id template letak kolom per rumah sakit, mis. `melati-v1`. Kosong = deteksi tabel otomatis. |

Respons `200`:

```json
{
  "versi_mesin": "pramana-0.3.1",
  "ukuran": [1240, 1754],
  "halaman_jpg": "<base64 atau URL sementara>",
  "kualitas_scan": { "status": "baik", "catatan": "Terbaca, miring 0.4 derajat.", "ketajaman": 0.91, "miring_derajat": 0.4 },
  "isi_lembar": { "nama": "Ratna Kusuma", "no_sep": "…", "baris_terisi": 5, "tanggal_sesi": ["04/08"], "jumlah_kunjungan_tertulis": 8, "kemiripan_ttd_rerata": 0.815 },
  "temuan": [
    { "cek": "kecocokan_klaim", "kekuatan": "kuat", "kalimat": "Ditagih 8 sesi, berkas hanya mendukung 5.", "region": [90, 1036, 1065, 283], "skor": 0.98 },
    { "cek": "suntingan", "kekuatan": "sedang", "kalimat": "Angka 8 … ditempel di atas angka 5.", "region": [347, 1360, 29, 44], "skor": 0.74 }
  ],
  "metadata_file": { "Producer": "…", "Creator": "…", "CreationDate": "…", "ModDate": "…" },
  "sidik_jari": {
    "algoritma": "phash64+simhash",
    "halaman": "a3f09c…",
    "baris": ["…", "…"],
    "teks": "7d21…"
  },
  "waktu_proses_ms": 4210
}
```

Aturan untuk mesin AI:

1. **Jangan mengirim `label` atau `saran`.** Hanya sinyal.
2. `kekuatan` ditentukan oleh mesin sesuai PRD bagian 8: `kecocokan_klaim`, `berkas_kembar`, `copy_paste`, `tempelan` = `kuat` bila bukti jelas; `suntingan` = `sedang`; `tanda_ai` = `lemah` sampai `sedang`, tidak pernah `kuat`.
3. Bila scan terlalu jelek untuk dinilai: `kualitas_scan.status = "scan_ulang"` dan **`temuan` kosong** (selain `kualitas_scan`). Scan jelek bukan temuan kecurangan.
4. Kolom identitas dan tanggal **ditutup sebelum** `sidik_jari` dihitung (PRD bagian 14).
5. `sidik_jari` harus deterministik: berkas yang sama menghasilkan nilai yang sama.
6. Setiap temuan wajib punya `kalimat` satu kalimat dalam bahasa verifikator, tanpa istilah teknis (mis. tulis "ditempel", bukan "ELA anomali").
7. Mesin AI boleh memakai LLM hanya untuk merangkai `kalimat`, tidak untuk memutuskan `kekuatan`.
8. **Jangan mengirim temuan `berkas_kembar`.** Kembar hanya bisa dibuktikan dengan arsip, jadi dibuat API: sidik jari dicari di DB, kandidat dikonfirmasi lewat `/v1/bandingkan`. Mesin cukup memberi `sidik_jari`. Temuan `tempelan` boleh dikirim tanpa `pasangan`, API yang mengisinya.
9. Berkas yang tidak bisa dibaca dibalas galat `422 tidak_terbaca`. API lalu menandainya Perlu dicek, tidak pernah Lolos.

> **`klaim` ke mesin:** API mengirim `klaim` bila `sep` diisi saat unggah dan SEP itu ada di data klaim pembanding (stand-in E-Klaim). Bila `sep` kosong atau tidak dikenal, `klaim` dikirim `{}`. Mesin menghitung `kecocokan_klaim` hanya bila `klaim.sesi_ditagih` ada; bila kosong, lewati pemeriksaan itu dan tetap kembalikan `isi_lembar` (jumlah baris dan tanggal sesi). API juga mencocokkan klaim dari `isi_lembar.no_sep` hasil baca mesin untuk ditampilkan.

## `POST /v1/bandingkan`

Dipanggil API setelah pencarian sidik jari di DB menemukan kandidat berkas kembar. Memastikan dan menghasilkan area yang sama.

Request `multipart/form-data`: `file_a`, `file_b`.

Respons `200`:

```json
{
  "kemiripan": 0.97,
  "sama": true,
  "kalimat": "Isi berkas 97% sama dengan berkas pembanding, setelah kolom identitas ditutup.",
  "region_a": [[86, 541, 1069, 779]],
  "region_b": [[86, 541, 1069, 779]],
  "tempelan": [
    { "bagian": "ttd-3", "region_a": [901, 760, 251, 94], "region_b": [901, 760, 251, 94], "kemiripan": 0.99 }
  ]
}
```

API lalu membuat dua temuan di hasil akhir: `berkas_kembar` (dengan `pasangan`) dan, bila `tempelan` tidak kosong, `tempelan`.

## `GET /v1/kesehatan`

`{ "status": "ok", "versi_mesin": "pramana-0.3.1", "model": ["ocr", "ela"] }`

## Galat mesin

`422 tidak_terbaca` (file rusak), `413 terlalu_besar`, `504 batas_waktu`. API membalas ke FE dengan `status: "gagal"` dan `label: "cek"`.

---

# Alur ujung ke ujung

1. FE `POST /api/v1/berkas`. API simpan file ke Storage, buat baris `berkas` (`diproses`), balas `202`.
2. Worker mengambil job, memanggil `POST /v1/analisis`.
3. API menyimpan `hasil_cek`, mencari kandidat kembar lewat `sidik_jari`, bila ada memanggil `POST /v1/bandingkan` dan menambah temuan.
4. API menghitung `label` (aturan PRD 9), menyimpan, mengubah `status` jadi `selesai`.
5. FE yang polling `GET /api/v1/berkas/{id}` menerima hasil.
6. Verifikator memutuskan lewat `POST …/keputusan`. Tercatat di `keputusan` dan `jejak`.

# Skema database (Supabase / PostgreSQL)

| Tabel | Kolom utama |
|---|---|
| `berkas` | `id`, `sep`, `kode_faskes`, `nama_file`, `path_storage`, `sha256`, `jumlah_halaman`, `status`, `sidik_jari_halaman`, `sidik_jari_teks`, `diunggah_oleh`, `waktu_unggah` |
| `hasil_cek` | `id`, `berkas_id`, `cek`, `kekuatan`, `skor`, `region` (jsonb), `pasangan_id`, `kalimat`, `versi_mesin`, `versi_aturan` |
| `label` | `berkas_id`, `label`, `alasan`, `waktu` |
| `konfirmasi` | `berkas_id`, `pertanyaan`, `jawaban`, `waktu_kirim`, `waktu_jawab` |
| `keputusan` | `id`, `berkas_id`, `verifikator`, `tindakan`, `catatan`, `waktu`, `dibatalkan` |
| `akses_log` | `waktu`, `pengguna`, `aksi`, `berkas_id` (PRD bagian 14) |

Row Level Security: verifikator hanya membaca berkas faskes di kantor cabangnya. Kolom identitas tidak pernah masuk `sidik_jari`.

# Mode cadangan

Bila `GET /api/v1/kesehatan` melaporkan `mesin != ok`, FE dan API memakai **stub**: hasil dibaca dari `dataset/manifest.json` untuk berkas dataset, sedangkan berkas luar dataset menjadi `cek` dengan `status: "gagal"`. Demo tidak boleh pernah menampilkan layar kosong.

# Yang perlu disepakati dengan Zahra

1. Ukuran dan DPI `halaman_jpg` (usul: A4 150 dpi, `[1240, 1754]`).
2. Format template per rumah sakit (usul: JSON `region_lembar`, seperti di dataset).
3. Algoritma `sidik_jari` dan ambang kemiripan kembar (usul awal: ≥ 0.90).
4. Urutan prioritas fitur: OCR jumlah sesi, `copy_paste` (SSIM), `berkas_kembar` dulu; `suntingan` dan `tanda_ai` menyusul.
5. Cara hosting (usul: Docker, endpoint di atas).
