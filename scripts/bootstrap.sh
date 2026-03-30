#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

PY="$ROOT/.venv/bin/python"

"$PY" -m pip install --upgrade pip

if [[ "${1:-}" == "--dev" ]]; then
  "$PY" -m pip install -e ".[dev]"
else
  "$PY" -m pip install -e "."
fi

if [[ ! -f ".env" ]]; then
  cp .env.example .env
fi

echo "Ready."
echo "Activate with: source .venv/bin/activate"

