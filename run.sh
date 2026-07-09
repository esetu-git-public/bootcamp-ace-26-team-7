#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
STREAMLIT_BIN="$VENV_DIR/bin/streamlit"
UVICORN_BIN="$VENV_DIR/bin/uvicorn"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Creating virtual environment in .venv..."
  python3 -m venv "$VENV_DIR"
fi

if [[ ! -x "$STREAMLIT_BIN" ]] || [[ ! -x "$UVICORN_BIN" ]]; then
  echo "Installing Python dependencies..."
  "$PIP_BIN" install -r requirements.txt streamlit
fi

echo "Starting Streamlit UI on http://0.0.0.0:8501"
"$STREAMLIT_BIN" run app.py --server.address 0.0.0.0 --server.port 8501 &
STREAMLIT_PID=$!

echo "Starting FastAPI backend on http://0.0.0.0:8000"
"$UVICORN_BIN" backend.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

cleanup() {
  echo "Stopping services..."
  kill "$STREAMLIT_PID" "$API_PID" 2>/dev/null || true
  wait "$STREAMLIT_PID" "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait -n "$STREAMLIT_PID" "$API_PID"
