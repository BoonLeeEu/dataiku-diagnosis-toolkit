#!/usr/bin/env bash
# Read-only triage for an extracted Dataiku DSS diagnosis.zip bundle.
# Usage: orient.sh <bundle_root>
#
# Prints: node type/version, the data-dir mirror path, the largest files in the
# bundle (so you don't try to `cat` a multi-hundred-MB manifest), and the
# presence/size of key troubleshooting files. Makes no changes and no network
# calls. Portable to macOS (BSD tools) and Linux (GNU tools).

set -u

root="${1:-}"
if [ -z "$root" ]; then
  echo "Usage: $0 <bundle_root>" >&2
  exit 1
fi
if [ ! -d "$root" ]; then
  echo "Error: not a directory: $root" >&2
  exit 1
fi

if [ ! -f "$root/diag.txt" ] || [ ! -f "$root/timings.txt" ]; then
  echo "Error: '$root' does not look like a diagnosis bundle root (missing diag.txt/timings.txt)." >&2
  exit 1
fi

human_size() {
  # $1 = size in KB (integer). Prints e.g. "512K", "3.4M", "2.1G".
  awk -v kb="$1" 'BEGIN {
    if (kb >= 1048576) printf "%.1fG", kb/1048576;
    else if (kb >= 1024) printf "%.1fM", kb/1024;
    else printf "%dK", kb;
  }'
}

echo "== Dataiku diagnosis bundle orientation: $root =="
echo

# --- Locate install.ini / the data-dir mirror ---
install_ini=$(find "$root" -maxdepth 6 -name install.ini 2>/dev/null | head -1)
if [ -z "$install_ini" ]; then
  echo "! Could not find install.ini under this bundle (searched 6 levels deep)."
  mirror=""
else
  mirror=$(dirname "$install_ini")
  echo "Data-dir mirror: $mirror"
  nodetype=$(grep -m1 -E '^[[:space:]]*nodetype[[:space:]]*=' "$install_ini" | sed -E 's/^[^=]*=[[:space:]]*//')
  nodeid=$(grep -m1 -E '^[[:space:]]*nodeid[[:space:]]*=' "$install_ini" | sed -E 's/^[^=]*=[[:space:]]*//')
  echo "  nodetype: ${nodetype:-<not found>}"
  echo "  nodeid:   ${nodeid:-<not found>}"

  dssver="$mirror/dss-version.json"
  if [ -f "$dssver" ]; then
    product_version=$(grep -o '"product_version"[[:space:]]*:[[:space:]]*"[^"]*"' "$dssver" | sed -E 's/.*"([^"]*)"$/\1/')
    conf_version=$(grep -o '"conf_version"[[:space:]]*:[[:space:]]*"[^"]*"' "$dssver" | sed -E 's/.*"([^"]*)"$/\1/')
    echo "  product_version: ${product_version:-<not found>}"
    echo "  conf_version:    ${conf_version:-<not found>}"
  else
    echo "  ! dss-version.json not found next to install.ini"
  fi

  case "$nodetype" in
    design|automation) : ;;
    "") echo "  ! nodetype not parsed — check $install_ini manually" ;;
    *) echo "  Note: nodetype '$nodetype' is not design/automation — this skill's config/run docs are unverified for it (see references/limitations.md)." ;;
  esac
fi
echo

# --- Largest files (flag before anything tries to read them whole) ---
echo "-- Largest files in bundle (top 10) --"
find "$root" -type f -exec du -k {} + 2>/dev/null | sort -rn | head -10 | while IFS=$'\t' read -r kb path; do
  printf "  %6s  %s\n" "$(human_size "$kb")" "$path"
done
echo

# --- Key troubleshooting files ---
echo "-- Key troubleshooting files --"
check_file() {
  # $1 = label, $2 = path
  if [ -f "$2" ]; then
    kb=$(du -k "$2" 2>/dev/null | cut -f1)
    printf "  [present] %-45s %s\n" "$1" "$(human_size "${kb:-0}")"
  else
    printf "  [absent]  %s\n" "$1"
  fi
}

check_file "dmesg.txt" "$root/dmesg.txt"
check_file "stacks.txt" "$root/stacks.txt"
check_file "cgroups_usage.txt" "$root/cgroups_usage.txt"

if [ -n "${mirror:-}" ]; then
  check_file "run/sanity-check.json" "$mirror/run/sanity-check.json"

  hs_err_count=$(find "$mirror/run" -maxdepth 1 -name 'hs_err_pid*.log' 2>/dev/null | wc -l | tr -d ' ')
  if [ "${hs_err_count:-0}" -gt 0 ]; then
    echo "  [present] run/hs_err_pid*.log ($hs_err_count file(s)) -- JVM crash dumps, check these first for OOM/crash root cause"
  else
    echo "  [absent]  run/hs_err_pid*.log"
  fi

  if [ -d "$mirror/run/audit" ]; then
    audit_count=$(find "$mirror/run/audit" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "  [present] run/audit/ ($audit_count file(s))"
  else
    echo "  [absent]  run/audit/"
  fi

  echo
  echo "-- Logs in run/ (scan them with scripts/logscan.py) --"
  if [ -d "$mirror/run" ]; then
    find "$mirror/run" -maxdepth 1 -type f \( -name '*.log' -o -name '*.log.[0-9]*' \) ! -name 'hs_err_pid*' 2>/dev/null | sort | while read -r f; do
      kb=$(du -k "$f" 2>/dev/null | cut -f1)
      printf "  %6s  %s\n" "$(human_size "${kb:-0}")" "${f#$mirror/}"
    done
  else
    echo "  [absent]  run/"
  fi

  echo
  echo "-- Bundle-activation signals (common on automation, rare on design) --"
  bundle_count=$(find "$mirror/config/projects" -maxdepth 2 -name active-bundle.json 2>/dev/null | wc -l | tr -d ' ')
  echo "  active-bundle.json found under config/projects/: $bundle_count"
  if [ -d "$mirror/acode-envs" ] && [ -n "$(find "$mirror/acode-envs" -type f -print -quit 2>/dev/null)" ]; then
    echo "  acode-envs/ has content (activated-code-env envs present)"
  else
    echo "  acode-envs/ absent or empty"
  fi
fi

echo
echo "== Done. See SKILL.md's investigation workflow for next steps. =="
