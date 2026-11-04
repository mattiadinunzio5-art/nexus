#!/usr/bin/env bash
# Esegue uno script Python con l'ambiente di NEXUS, su qualsiasi sistema.
#   scripts/py.sh scripts/seed_demo.py
#   scripts/py.sh scripts/generate_briefing.py --refresh
set -euo pipefail
source "$(dirname "$0")/_env.sh"
require_venv
exec "$VPY" "$@"
