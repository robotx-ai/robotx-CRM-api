#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python}"
VENV_DIR="${VENV_DIR:-.venv312}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo "[1/5] Create/activate venv: $VENV_DIR"
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "[2/5] Install dependencies"
pip install -r requirements.txt >/dev/null

echo "[3/5] Static sanity check"
python -m compileall app >/dev/null

echo "[4/5] Quick health pre-check (may fail if server not running yet)"
set +e
curl -fsS "http://$HOST:$PORT/health" >/dev/null
if [ $? -eq 0 ]; then
  echo "Existing server is healthy at http://$HOST:$PORT/health"
else
  echo "No running server detected yet (expected if first run)."
fi
set -e

echo "[5/5] Start FastAPI locally"
echo "Open docs: http://$HOST:$PORT/docs"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
