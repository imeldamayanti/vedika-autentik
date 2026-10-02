#!/bin/sh
# Menjalankan semua proses backend dalam satu container (demo).
#
# - Stub mesin hanya dijalankan bila MESIN_URL kosong atau menunjuk ke localhost:8001.
#   Untuk memakai mesin AI asli, isi MESIN_URL dengan alamat mesin Zahra.
# - Worker dijalankan dalam loop supaya hidup lagi bila prosesnya mati.
# - API berjalan di port $PORT (diisi Railway).
set -e

if [ -z "$MESIN_URL" ] || [ "$MESIN_URL" = "http://localhost:8001" ]; then
  uvicorn stub_mesin.main:app --host 127.0.0.1 --port 8001 &
fi

(while true; do python -m app.worker || true; sleep 2; done) &

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
