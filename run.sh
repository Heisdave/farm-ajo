#!/usr/bin/env bash
# Farm Ajo demo — one command.
# Creates the Python environment itself, installs dependencies,
# and starts the demo server on port 8792. No manual venv steps.
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/uvicorn ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
exec .venv/bin/uvicorn app.main:app --port 8792
