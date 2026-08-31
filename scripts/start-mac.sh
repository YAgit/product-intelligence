#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
uv sync
uv run uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}" --reload
