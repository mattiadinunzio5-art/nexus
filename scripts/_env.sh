#!/usr/bin/env bash
# Funzioni comuni agli script: trovano Python e l'ambiente virtuale su Linux, macOS e Windows
# (Git Bash, MSYS2/UCRT64, Cygwin). Da includere con: source "$(dirname "$0")/_env.sh"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/backend/.venv"

is_windows() {
  case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) return 0 ;; *) return 1 ;; esac
}

# Interprete Python di sistema adatto (3.11–3.13: alcune librerie, es. onnxruntime per PyMuPDF,
# non sono ancora disponibili per versioni più recenti). Su Windows serve il Python ufficiale
# (python.org): quello di MSYS2 non ha i pacchetti precompilati per numpy/pandas.
find_python() {
  local cand out
  for cand in "py -3.13" "py -3.12" "py -3.11" "py -3" python3 python; do
    out="$($cand -c 'import sys; print(sys.platform, sys.version_info[0], sys.version_info[1])' 2>/dev/null)" || continue
    read -r plat major minor <<<"$out"
    [[ "$major" == 3 && "$minor" -ge 11 && "$minor" -le 13 ]] || continue
    if is_windows && [[ "$plat" != "win32" ]]; then continue; fi
    echo "$cand"
    return 0
  done
  return 1
}

# Python dell'ambiente virtuale (Windows: .venv/Scripts, altrove: .venv/bin).
venv_python() {
  if [[ -x "$VENV/Scripts/python.exe" ]]; then echo "$VENV/Scripts/python.exe"
  elif [[ -x "$VENV/bin/python" ]]; then echo "$VENV/bin/python"
  else return 1
  fi
}

require_venv() {
  VPY="$(venv_python)" || { echo "Ambiente Python non trovato: esegui prima scripts/setup.sh" >&2; exit 1; }
}
