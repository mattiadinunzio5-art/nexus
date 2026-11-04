#!/usr/bin/env bash
# Esegue tutti i test automatici (backend + frontend + typecheck).
set -euo pipefail
source "$(dirname "$0")/_env.sh"
require_venv
echo "==> pytest";      (cd "$ROOT/backend" && "$VPY" -m pytest)
echo "==> typecheck";   (cd "$ROOT/frontend" && npx tsc -b)
echo "==> vitest";      (cd "$ROOT/frontend" && npx vitest run)
