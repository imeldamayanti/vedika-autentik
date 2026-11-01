#!/usr/bin/env bash
# Start the local v3 demo: ai-service (8001), backend API (8000), and website (8899).
# Ctrl-C stops all three.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
API_PORT="${API_PORT:-8000}"
AI_PORT="${AI_PORT:-8001}"
WEB_PORT="${WEB_PORT:-8899}"

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

trap 'trap - EXIT; kill 0' INT TERM EXIT

(cd "$ROOT/ai-service" && uv run --env-file .env env LOG_FORMAT=text uvicorn vedika_ai.main:app --port "$AI_PORT" 2>&1 | sed -u 's/^/[ai-service] /') &
(cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --port "$API_PORT" 2>&1 | sed -u 's/^/[backend] /') &
(cd "$ROOT" && python3 -m http.server "$WEB_PORT" --bind 127.0.0.1 2>&1 | sed -u 's/^/[web] /') &

curl -s --retry 30 --retry-delay 1 --retry-connrefused -o /dev/null "http://localhost:$AI_PORT/v1/kesehatan"
curl -s --retry 30 --retry-delay 1 --retry-connrefused -o /dev/null "http://localhost:$API_PORT/api/v1/kesehatan"

cat <<EOF

Ready.
  Website:     http://localhost:$WEB_PORT
  Agent page:  http://localhost:$AI_PORT/voice/   (Chrome; Kunci agen = AGEN_KEY in backend/.env)
  Health:      $(curl -s "http://localhost:$API_PORT/api/v1/kesehatan")
Calls are handed out 09:00-17:00 WIB only. Press Ctrl-C to stop everything.

EOF
open -a "Google Chrome" "http://localhost:$AI_PORT/voice/" "http://localhost:$WEB_PORT" 2>/dev/null || true
wait
