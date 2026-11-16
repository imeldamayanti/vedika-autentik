# Backend Vedika Autentik

Kontrak lengkap: [docs/api-contract.md](../docs/api-contract.md). Rencana: [docs/rencana-be.md](../docs/rencana-be.md).

```
FE  ──Kontrak A──▶  API (app/)  ──Kontrak B──▶  Mesin AI
                    + worker                    (`ai-service/`; `stub_mesin/` untuk fallback demo)
                    + Supabase
```

## Untuk AI engineering (Zahra)

Mesin nyata ada di `../ai-service/` dan memenuhi Kontrak B (`POST /v1/analisis`,
`POST /v1/bandingkan`, `GET /v1/kesehatan`). `stub_mesin/` tetap tersedia sebagai
fallback demo berbasis `dataset/manifest.json`.

Aturan yang paling sering terlewat (lengkapnya di kontrak, bagian "Aturan untuk mesin AI"):

- Mesin **tidak mengirim `label` atau `saran`**. Label dihitung API.
- Mesin **tidak mengirim temuan `berkas_kembar`**. Cukup `sidik_jari` yang deterministik (kolom identitas dan tanggal ditutup dulu). API yang mencari kembar dan memanggil `/v1/bandingkan`.
- Koordinat `region` = `[x, y, lebar, tinggi]` pada JPG A4 150 dpi, `ukuran = [1240, 1754]`.
- Scan jelek: `kualitas_scan.status = "scan_ulang"` dan tanpa temuan. Bukan tanda kecurangan.
- Berkas tidak terbaca: balas `422` `{"galat": {"kode": "tidak_terbaca", "pesan": "…"}}`.

Menjalankan stub:

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn stub_mesin.main:app --port 8001
```

Buka `http://localhost:8001/docs` untuk melihat bentuk request dan respons. Contoh:

```bash
curl -F "file=@../dataset/03-angka-disunting/VA-DST-01.pdf" -F 'klaim={}' localhost:8001/v1/analisis
```

Uji stub (tanpa database): `.venv/bin/pytest tests/test_stub_mesin.py tests/test_label.py`.

## Untuk BE

Butuh `backend/.env` (salin dari `.env.example`, jangan di-commit). Tanpa `DATABASE_URL`, uji yang memakai DB dilewati.

```bash
.venv/bin/uvicorn stub_mesin.main:app --port 8001        # mesin
.venv/bin/uvicorn app.main:app --port 8000               # API
.venv/bin/python -m app.worker                           # worker antrean
.venv/bin/python -m scripts.seed                         # isi antrean demo (12 berkas)
.venv/bin/pytest                                         # semua uji (±90 detik, memakai schema sementara)
```

Skema database: [db/schema.sql](db/schema.sql). Uji API berjalan di schema sementara `uji` yang di-rollback, jadi tabel produksi tidak tersentuh.

## v3: konfirmasi suara

Kontrak: [docs/api-contract-v3.md](../docs/api-contract-v3.md). Serah terima bagian Zahra: [docs/serah-terima-zahra.md](../docs/serah-terima-zahra.md).

```
FE (index.html) ──Kontrak A──▶ API ──Kontrak B2──▶ pembaca jawaban (stub_mesin: POST /v1/baca)
                                 ▲
agen suara (stasiun HP Android, atau scripts/stub_agen.py) ──Kontrak B1──┘   API ──▶ Meta WhatsApp Cloud API
```

Perlu di `backend/.env`: `AGEN_KEY` (kunci agen), `NOMOR_PENGUJI`, `NOMOR_PENELEPON`; lihat `.env.example`.

```bash
.venv/bin/python -m scripts.terapkan_v3 --reset            # skema v3 + seed keadaan awal (mengubah DB!)
.venv/bin/uvicorn stub_mesin.main:app --port 8001           # stub pembaca jawaban
.venv/bin/uvicorn app.main:app --port 8000                  # API
.venv/bin/python -m scripts.stub_agen                       # stub agen: menelepon antrean berurutan (mode otomatis bawaan aktif)
.venv/bin/python -m scripts.stub_agen --skenario S1         # atau: Dahulukan S1 lalu selesai
python3 -m http.server 8899                                 # website (dari akar repo)
```

Stasiun nyata (HP Android + halaman agen) dijalankan dengan `./stasiun.sh` dari akar repo; lihat
[docs/rencana-v3-otomatis/STASIUN.md](../docs/rencana-v3-otomatis/STASIUN.md).

Demo cepat: `PUT /api/v1/pengaturan {"jeda_wa_menit": 0, "jeda_percobaan_menit": 0}` dan, di luar jam 09.00–17.00,
`{"jam_mulai": "00:00", "jam_selesai": "23:59"}`. Tombol "Mulai ulang demo" (atau `POST /api/v1/demo/reset`) mengembalikan
panggilan, log, dan keputusan ke keadaan awal, dan menyalakan mode otomatis.

### Panggilan otomatis

- Mode otomatis **menyala sejak awal**. "Dahulukan" (`POST /panggilan/{id}/mulai`) memindahkan pasien ke urutan berikutnya.
- `POST /agen/detak` (kunci agen): detak stasiun, disimpan di `pengaturan["stasiun"]`. `GET /antrean` mengembalikannya
  sebagai `pengaturan.stasiun` dengan `aktif` = terlihat dalam 30 detik terakhir.
- `POST /panggilan/{id}/batal` (tanpa kunci): verifikator membatalkan panggilan yang tertahan; dihitung satu percobaan gagal.
- Panggilan berjalan yang 5 menit tanpa laporan dilepas otomatis (`KUNCI_MACET_MENIT`), di awal `agen/ambil` dan `GET /antrean`.
- Tidak diangkat, dibatalkan, dan macet memakai satu fungsi (`agen._gagal_satu_percobaan`): percobaan ke-1 kembali antre,
  percobaan ke-2 menjadi Tidak terhubung dan chat cadangan dikirim.

### WhatsApp (Meta Cloud API)

Pesan pemberitahuan (Lampiran B) dikirim server saat agen mengambil tugas; chat cadangan saat percobaan ke-2 gagal
(`app/wa.py`). Satu percobaan, batas 10 detik; gagal kirim tidak pernah menahan panggilan. Hasilnya tercatat di log
panggilan (`wa:terkirim|simulasi|gagal`, `chat:…`). Token, nomor, dan isi pesan tidak pernah dicatat.

| Variabel | Isi |
|---|---|
| `META_WA_MODE` | `log` (bawaan: tidak mengirim, tercatat `simulasi`), `teks`, atau `template` |
| `META_WA_TOKEN`, `META_WA_PHONE_ID` | Dari dasbor aplikasi Meta. Salah satunya kosong = mode selalu `log` |
| `META_WA_API_VERSION` | Versi Graph API yang tampil di dasbor aplikasi Meta. Wajib di mode `teks` dan `template`; tanpa nilai bawaan |
| `META_WA_TEMPLATE_PEMBERITAHUAN`, `META_WA_TEMPLATE_CADANGAN`, `META_WA_TEMPLATE_BAHASA` | Nama dan bahasa template (mode `template`; bahasa bawaan `id`) |

Mode `teks` hanya sampai dalam 24 jam setelah penerima terakhir mengirim pesan ke nomor bisnis. Urutan parameter template:

- pemberitahuan: `[nama_penerima, jeda_menit, nomor_penelepon, nama_pasien, nama_rs, bulan]`
- cadangan: `[nama_pasien, nama_rs, bulan]`

Isi badan template dan langkah di Meta: [STASIUN.md](../docs/rencana-v3-otomatis/STASIUN.md) bagian 5.

Uji: `.venv/bin/pytest` (±10 menit karena DB jauh). Uji v3 berjalan dalam satu transaksi di schema sementara `uji3`
yang di-rollback di akhir sesi; tabel produksi tidak tersentuh. Pembaca jawaban diganti objek palsu di uji, dan Meta
tidak pernah dihubungi (`tests/test_wa.py` memakai `httpx.MockTransport`).
