#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python
fi

if [ ! -d .venv ]; then
  echo "• Creating virtual environment…"
  "$PYTHON" -m venv .venv
fi

if [ -x .venv/bin/python ]; then
  VENV_PY=.venv/bin/python
else
  VENV_PY=.venv/Scripts/python.exe
fi

echo "• Installing dependencies…"
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "• Created .env from .env.example"
fi

echo "• Preparing demo database…"
"$VENV_PY" -m app.seed

echo "• Starting portal at http://127.0.0.1:${PORT:-5000}"
exec "$VENV_PY" run.py
