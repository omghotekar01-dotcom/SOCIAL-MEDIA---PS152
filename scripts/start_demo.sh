#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r backend-ai/requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi

[ -f .env ] || cp .env.example .env

cleanup() {
  kill "${API_PID:-}" "${UI_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

.venv/bin/python -m uvicorn app.main:app --app-dir backend-ai --host 127.0.0.1 --port 8000 &
API_PID=$!
(cd frontend && npm run dev -- --host 127.0.0.1 --port 5173) &
UI_PID=$!

echo "NEXUS API: http://127.0.0.1:8000"
echo "NEXUS UI : http://127.0.0.1:5173"
echo "Replay data is clearly labelled; add credentials to .env to enable live connectors."
wait
