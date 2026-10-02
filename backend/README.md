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
