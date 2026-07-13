#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
GRADIO_BIN="$VENV_DIR/bin/gradio"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Creating virtual environment in .venv..."
  python3 -m venv "$VENV_DIR"
fi

if [[ ! -x "$GRADIO_BIN" ]]; then
  echo "Installing Python dependencies..."
  "$PIP_BIN" install -r requirements.txt
fi

echo "Starting Gradio app on http://0.0.0.0:8501"
"$GRADIO_BIN" app.py --server.port 8501 --server.address 0.0.0.0