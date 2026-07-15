#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="$ROOT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

# ── 0. Environment setup ──────────────────────────────────
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE="$ROOT_DIR/.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$ENV_EXAMPLE" ]]; then
        echo "Creating .env from .env.example..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo "⚠️  Please edit .env with your credentials (Supabase, JWT_SECRET, ADMIN_EMAIL/PASSWORD)"
    else
        echo "ERROR: No .env.example found. Cannot create .env"
        exit 1
    fi
fi

# Export env vars so subprocesses (uvicorn, vite) can see them
set -a
source "$ENV_FILE"
set +a

# ── 1. Python backend ─────────────────────────────────────
if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing Python dependencies..."
"$PIP_BIN" install -q --upgrade pip
"$PIP_BIN" install -q -r requirements.txt

# ── 2. Node frontend ──────────────────────────────────────
FRONTEND_DIR="$ROOT_DIR/frontend"

if [[ ! -d "$FRONTEND_DIR" ]]; then
    echo "ERROR: Frontend directory not found at $FRONTEND_DIR"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "ERROR: npm not found. Please install Node.js"
    exit 1
fi

echo "Installing frontend dependencies..."
cd "$FRONTEND_DIR"
npm install --silent 2>/dev/null || npm install
cd "$ROOT_DIR"

# ── 3. Start both services ────────────────────────────────
echo ""
echo "=============================================="
echo " Starting Surface Crack Detection App"
echo "=============================================="
echo ""

# Start API backend in background
echo "Starting FastAPI backend on http://localhost:8501 ..."
"$PYTHON_BIN" -m uvicorn backend.main:app --host 0.0.0.0 --port 8501 &
API_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend dev server (Vite + TanStack Start SSR)
echo "Starting frontend dev server on http://localhost:5173 ..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
cd "$ROOT_DIR"

echo ""
echo " * API:       http://localhost:8501"
echo " * Frontend:  http://localhost:5173"
echo " * API Docs:  http://localhost:8501/docs"
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
