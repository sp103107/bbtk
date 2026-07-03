#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"
echo "Best Buds Time Clock - local dev start-all"
echo "Starting backend on http://127.0.0.1:${PORT} ..."
python scripts/start_kiosk_server.py --host "$HOST" --port "$PORT" &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true" EXIT
TRIES=0
while [ "$TRIES" -lt 30 ]; do
  if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${PORT}/api/health', timeout=2)"; then
    break
  fi
  TRIES=$((TRIES + 1))
  sleep 1
done
echo "Backend healthy."
echo "Owner console: http://127.0.0.1:${PORT}/"
echo "Employee portal: http://127.0.0.1:${PORT}/employee"
echo "Local dev convenience only. Not a production deployment claim."
wait "$SERVER_PID"
