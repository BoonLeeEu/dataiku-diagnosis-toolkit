#!/usr/bin/env bash
# Host preflight: prints which outputs this machine can produce. Pure bash, so it runs with no Python.
#   TIER=FULL         workbook + Summary + deck (Python >=3.10 with mcp, python-pptx, openpyxl, PyYAML, Pillow, lxml)
#   TIER=SPREADSHEET  workbook only (some Python has openpyxl; no deck)
#   TIER=FACTS_ONLY   orient/facts findings in chat only (no workbook, no deck)
# A trailing renderer=soffice+pdftoppm|none line says whether the deck can be rendered for a visual check.
# The interpreter candidates mirror start-review-generator.sh; keep the two lists in step.
set -uo pipefail

SRC="${BASH_SOURCE[0]}"; [[ "$SRC" == */* ]] || SRC="./$SRC"  # no dirname: it may not be on a stripped PATH
SCRIPT_DIR="$(cd "${SRC%/*}" && pwd)"
SERVER_DIR="$SCRIPT_DIR/../mcp-server-review-generator"
[[ -n "${PREFLIGHT_PATH_AS_IS:-}" ]] || export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"  # as-is is for tests

# Deck renderer for the visual check (informational only; it never changes the tier).
renderer_line() {
  if command -v soffice >/dev/null 2>&1 && command -v pdftoppm >/dev/null 2>&1; then echo "renderer=soffice+pdftoppm"
  else echo "renderer=none"; fi
}
trap renderer_line EXIT

ok310() { "$1" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; }
missing_in() {  # missing_in <python> <module>...  -> prints the modules it can't import
  local py="$1"; shift
  for m in "$@"; do "$py" -c "import $m" >/dev/null 2>&1 || printf '%s ' "$m"; done
}

ABS=(/opt/homebrew/bin/python3 /usr/local/bin/python3)
[[ -z "${PREFLIGHT_PATH_AS_IS:-}" ]] || ABS=()
PY=""
for cand in "${DATAIKU_PYTHON:-}" python3.13 python3.12 python3.11 python3.10 ${ABS[@]+"${ABS[@]}"} python3; do
  [[ -n "$cand" ]] || continue
  if command -v "$cand" >/dev/null 2>&1 && ok310 "$cand"; then PY="$cand"; break; fi
done

# Venvs the plugin may have built (Claude: beside the plugin; Codex: under PLUGIN_DATA).
VENVS=("$SERVER_DIR/.venv/bin/python3")
[[ -n "${PLUGIN_DATA:-}" ]] && VENVS+=("$PLUGIN_DATA/review-generator/mcp-server-review-generator/.venv/bin/python3")
for v in "$HOME"/.codex/plugins/data/*/*/review-generator/mcp-server-review-generator/.venv/bin/python3; do
  [[ -x "$v" ]] && VENVS+=("$v")
done

ALL="mcp pptx yaml openpyxl PIL lxml"
VENV_PY=""; VENV_MISSING=""
for v in "${VENVS[@]}"; do
  [[ -x "$v" ]] && ok310 "$v" || continue
  m="$(missing_in "$v" $ALL)"
  if [[ -z "$m" ]]; then VENV_PY="$v"; VENV_MISSING=""; break; fi
  VENV_MISSING="$m"
done

fix_python="install Python 3.10+ (or set DATAIKU_PYTHON to one) and restart the host so the review generator can build its venv"

if [[ -n "$VENV_PY" ]]; then
  echo "TIER=FULL"; echo "python=$VENV_PY"
  echo "detail=review generator venv is complete"
  exit 0
fi
if [[ -n "$PY" ]]; then
  echo "TIER=FULL"; echo "python=$PY"
  echo "detail=Python $("$PY" --version 2>&1 | cut -d' ' -f2) found; the review generator builds its venv on first launch (needs PyPI access)${VENV_MISSING:+; existing venv lacks: $VENV_MISSING}"
  exit 0
fi

# No Python >=3.10: the deck is impossible. Is there any interpreter with openpyxl for the workbook?
for cand in "${DATAIKU_PYTHON:-}" "${VENVS[@]}" python3.9 python3.8 python3; do
  [[ -n "$cand" ]] && command -v "$cand" >/dev/null 2>&1 || continue
  if [[ -z "$(missing_in "$cand" openpyxl)" ]]; then
    echo "TIER=SPREADSHEET"; echo "python=$cand"
    echo "detail=no Python 3.10+, so no deck and no review-generator tools; the workbook can be written with run_step.py and the manual Summary"
    echo "fix=$fix_python"
    exit 0
  fi
done

echo "TIER=FACTS_ONLY"
echo "detail=no Python 3.10+ and no Python with openpyxl: only orient/facts findings in chat, no workbook or deck"
echo "fix=$fix_python"
