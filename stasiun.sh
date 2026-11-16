#!/usr/bin/env bash
# Start the line station: Android phone over adb, ai-service with the Phone helper (8001), backend API (8000),
# website (8899), and the agent page in its own Chrome app window. Ctrl-C stops everything.
# Setup and troubleshooting: docs/rencana-v3-otomatis/STASIUN.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
API_PORT="${API_PORT:-8000}"
AI_PORT="${AI_PORT:-8001}"
WEB_PORT="${WEB_PORT:-8899}"
env_value() { grep -E "^$2=" "$1" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d "\"'" || true; }
ADB="${SALURAN_ADB_BIN:-$(env_value "$ROOT/ai-service/.env" SALURAN_ADB_BIN)}"
ADB="${ADB:-adb}"
SERIAL="${SALURAN_ADB_SERIAL:-$(env_value "$ROOT/ai-service/.env" SALURAN_ADB_SERIAL)}"
adb_phone() { if [ -n "$SERIAL" ]; then "$ADB" -s "$SERIAL" "$@"; else "$ADB" "$@"; fi; }

if ! command -v "$ADB" >/dev/null; then
  echo "adb tidak ditemukan. Pasang dulu: brew install android-platform-tools"
  exit 1
fi
devices=$("$ADB" devices | tail -n +2 | awk 'NF >= 2')
[ -n "$SERIAL" ] && devices=$(echo "$devices" | awk -v s="$SERIAL" '$1 == s')
ready=$(echo "$devices" | awk '$2 == "device"' | grep -c . || true)
if [ "$ready" -ne 1 ] || [ "$(echo "$devices" | grep -c . || true)" -ne 1 ]; then
  if echo "$devices" | grep -q unauthorized; then echo "HP belum mengizinkan laptop ini: buka kunci HP lalu setujui \"Izinkan debugging USB\"."
  elif [ "$ready" -gt 1 ] || [ "$(echo "$devices" | grep -c . || true)" -gt 1 ]; then echo "Lebih dari satu HP terhubung. Isi SALURAN_ADB_SERIAL (lihat: adb devices)."
  else echo "HP tidak terhubung ke laptop. Cek kabel USB dan nyalakan USB debugging."; fi
  exit 1
fi

for port in "$API_PORT" "$AI_PORT" "$WEB_PORT"; do
  if pid=$(lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -1) && [ -n "$pid" ]; then
    echo "Port $port is in use by: $(ps -o command= -p "$pid" | cut -c1-100)"
    echo "Stop it first (kill $pid), then rerun."
    exit 1
  fi
done

db_host=$(grep -E '^DATABASE_URL=' "$ROOT/backend/.env" | sed -E 's#.*@([^:/]+):([0-9]+).*#\1 \2#')
if ! nc -z -G 5 $db_host 2>/dev/null; then
  echo "Supabase is unreachable from this network (ports 5432/6543 blocked). Switch to the hotspot."
  exit 1
fi

if [ ! -x "$ROOT/backend/.venv/bin/uvicorn" ]; then
  uv venv -q --python 3.12 "$ROOT/backend/.venv"
  uv pip install -q --python "$ROOT/backend/.venv/bin/python" -r "$ROOT/backend/requirements.txt"
fi

adb_phone shell svc power stayon usb
model=$(adb_phone shell getprop ro.product.model | tr -d '\r')
sim=$(adb_phone shell getprop gsm.sim.state | tr -d '\r')
audio="${SALURAN_AUDIO:-$(env_value "$ROOT/ai-service/.env" SALURAN_AUDIO)}"
meta=$(env_value "$ROOT/backend/.env" META_WA_MODE)
if [ -z "$(env_value "$ROOT/backend/.env" META_WA_TOKEN)" ] || [ -z "$(env_value "$ROOT/backend/.env" META_WA_PHONE_ID)" ]; then meta=log; fi
echo "HP saluran : $model"
echo "SIM        : $sim$(echo "$sim" | grep -qE 'READY|LOADED' || echo '  <- belum siap, panggilan tidak akan dimulai')"
echo "Audio      : ${audio:-speaker}"
echo "Meta WA    : ${meta:-log}$([ "${meta:-log}" = log ] && echo ' (pesan tidak benar-benar dikirim)')"

trap 'trap - EXIT; kill 0' INT TERM EXIT

caffeinate -dims -w $$ &
# The agent page gets the agent key only through the localhost-only /v1/saluran/konfigurasi route.
(cd "$ROOT/ai-service" && SALURAN_ADB=1 SALURAN_AGEN_KEY="${SALURAN_AGEN_KEY:-$(env_value "$ROOT/backend/.env" AGEN_KEY)}" \
  SALURAN_API_URL="${SALURAN_API_URL:-http://localhost:$API_PORT}" \
  uv run --env-file .env env LOG_FORMAT=text uvicorn vedika_ai.main:app --port "$AI_PORT" 2>&1 | sed -u 's/^/[ai-service] /') &
(cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --port "$API_PORT" 2>&1 | sed -u 's/^/[backend] /') &
(cd "$ROOT" && python3 -m http.server "$WEB_PORT" --bind 127.0.0.1 2>&1 | sed -u 's/^/[web] /') &

curl -s --retry 30 --retry-delay 1 --retry-connrefused -o /dev/null "http://localhost:$AI_PORT/v1/kesehatan"
curl -s --retry 30 --retry-delay 1 --retry-connrefused -o /dev/null "http://localhost:$API_PORT/api/v1/kesehatan"

cat <<EOF

Stasiun siap.
  Website petugas : http://localhost:$WEB_PORT
  Halaman agen    : http://localhost:$AI_PORT/voice/?mulai=1 (jendela Chrome tersendiri, jangan ditutup)
  Kesehatan       : $(curl -s "http://localhost:$API_PORT/api/v1/kesehatan")
Panggilan hanya berjalan 09.00-17.00 WIB. Ctrl-C menghentikan semuanya.

EOF
open -na "Google Chrome" --args --user-data-dir="$HOME/.vedika-stasiun-chrome" --use-fake-ui-for-media-stream \
  --autoplay-policy=no-user-gesture-required --app="http://localhost:$AI_PORT/voice/?mulai=1"
open "http://localhost:$WEB_PORT"
wait
