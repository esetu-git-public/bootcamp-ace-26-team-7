#!/bin/bash
set -e

BACKEND_PORT=5000
FRONTEND_PORT="${PORT:-7860}"

# Start FastAPI backend on internal port
echo "Starting FastAPI backend on port $BACKEND_PORT..."
uvicorn backend.main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
BACKEND_PID=$!

# Start frontend SSR server (proxies /api/* to FastAPI)
echo "Starting frontend SSR server on port $FRONTEND_PORT..."
cd /app/frontend && node server.mjs &
FRONTEND_PID=$!

cleanup() {
  echo "Shutting down..."
  kill "$FRONTEND_PID" 2>/dev/null
  kill "$BACKEND_PID" 2>/dev/null
  exit
}
trap cleanup SIGINT SIGTERM

echo "Both servers running. Frontend at http://0.0.0.0:$FRONTEND_PORT"
wait
