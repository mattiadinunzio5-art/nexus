#!/usr/bin/env bash
# Installa le dipendenze di backend e frontend (una tantum). Funziona su Linux, macOS e Windows.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

echo "==> Python"
if ! PY="$(find_python)"; then
  echo "ERRORE: serve Python 3.11 o successivo." >&2
  if is_windows; then
    echo "Installalo da https://www.python.org/downloads spuntando «Add python.exe to PATH»," >&2
    echo "poi chiudi e riapri il terminale e rilancia scripts/setup.sh" >&2
  fi
  exit 1
fi
echo "    uso: $PY ($($PY --version 2>&1))"

echo "==> Backend (ambiente virtuale)"
# Un ambiente rimasto a metà da un tentativo precedente viene ricreato.
if [[ -d "$VENV" ]] && ! { VPY="$(venv_python)" && "$VPY" -c 'import sys' 2>/dev/null; }; then
  echo "    ambiente incompleto: lo ricreo"
  rm -rf "$VENV"
fi
[[ -d "$VENV" ]] || $PY -m venv "$VENV"
VPY="$(venv_python)"
"$VPY" -m pip --version >/dev/null 2>&1 || "$VPY" -m ensurepip --upgrade >/dev/null
"$VPY" -m pip install -q --upgrade pip
echo "    installazione dei pacchetti (qualche minuto)…"
"$VPY" -m pip install -q -r "$ROOT/backend/requirements-dev.txt"

echo "==> Database (migrazioni)"
(cd "$ROOT/backend" && "$VPY" -m alembic upgrade head)

echo "==> Frontend (npm)"
if ! command -v npm >/dev/null 2>&1; then
  echo "ERRORE: serve Node.js (versione LTS) da https://nodejs.org — poi riapri il terminale." >&2
  exit 1
fi
cd "$ROOT/frontend"
npm install --no-fund --no-audit

echo "Pronto. Avvia con: scripts/dev.sh   (oppure scripts/dev.sh --lan per il telefono)"
