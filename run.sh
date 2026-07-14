#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="$ROOT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

# ── 1. Python backend ──────────────────────────────────
if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing Python dependencies..."
"$PIP_BIN" install -r requirements.txt

# ── 2. Node frontend ───────────────────────────────────
FRONTEND_DIR="$ROOT_DIR/frontend"

if [[ -d "$FRONTEND_DIR" ]]; then
    echo "Installing frontend dependencies..."
    cd "$FRONTEND_DIR"
    npm install
    cd "$ROOT_DIR"
else
    echo "WARNING: Frontend directory not found at $FRONTEND_DIR"
fi

# ── 3. Start both services ────────────────────────────
echo ""
echo "=============================================="
echo " Starting Surface Crack Detection App"
echo "=============================================="
echo ""

# Start API backend in background
"$PYTHON_BIN" -m uvicorn backend.main:app --host 0.0.0.0 --port 8501 &
API_PID=$!
echo " * API running at http://localhost:8501 (PID $API_PID)"

# Start frontend dev server
if [[ -d "$FRONTEND_DIR" ]]; then
    cd "$FRONTEND_DIR"
    npm run dev &
    FRONTEND_PID=$!
    cd "$ROOT_DIR"
    echo " * Frontend starting at http://localhost:5173 (PID $FRONTEND_PID)"
fi

echo ""
echo " Press Ctrl+C to stop both services"
echo ""

# Trap Ctrl+C to clean up both processes
cleanup() {
    echo ""
    echo "Shutting down..."
    if [[ -n "${API_PID:-}" ]]; then kill "$API_PID" 2>/dev/null || true; fi
    if [[ -n "${FRONTEND_PID:-}" ]]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
    exit 0
}
trap cleanup SIGINT SIGTERM

# Wait for both
wait
