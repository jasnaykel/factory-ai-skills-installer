#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "ERROR: Python 3 no está instalado o no está disponible en PATH." >&2
  exit 1
fi

exec "$PYTHON" "$ROOT/install_skills.py" "$@"
