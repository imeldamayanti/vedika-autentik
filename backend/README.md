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
agen suara (scripts/stub_agen.py) ──Kontrak B1──┘
```

Perlu di `backend/.env`: `AGEN_KEY` (kunci agen), `NOMOR_PENGUJI`; lihat `.env.example`.

```bash
.venv/bin/python -m scripts.terapkan_v3 --reset            # skema v3 + seed keadaan awal (mengubah DB!)
.venv/bin/uvicorn stub_mesin.main:app --port 8001           # stub pembaca jawaban
.venv/bin/uvicorn app.main:app --port 8000                  # API
.venv/bin/python -m scripts.stub_agen --skenario S1         # stub agen: Telepon sekarang S1 sampai selesai
python3 -m http.server 8899                                 # website (dari akar repo)
```

Demo cepat: `PUT /api/v1/pengaturan {"jeda_wa_menit": 0, "jeda_percobaan_menit": 0}` dan, di luar jam 09.00–17.00,
`{"jam_mulai": "00:00", "jam_selesai": "23:59"}`. Tombol "Mulai ulang demo" (atau `POST /api/v1/demo/reset`) mengembalikan
panggilan, log, dan keputusan ke keadaan awal.

Uji: `.venv/bin/pytest` (±10 menit karena DB jauh). Uji v3 berjalan dalam satu transaksi di schema sementara `uji3`
yang di-rollback di akhir sesi; tabel produksi tidak tersentuh. Pembaca jawaban diganti objek palsu di uji.
