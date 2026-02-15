#!/usr/bin/env bash

scout_repo_root() {
  local script_path="$1"
  (cd "$(dirname "$script_path")/../../.." && pwd)
}

scout_require_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "[ERROR] 'uv' not found. Install uv and run: uv sync" >&2
    return 1
  fi
}

scout_print_report_snapshot() {
  local report_path="$1"
  awk '
  /^## Latest Run Snapshot/ {section="latest"; print ""; print $0; next}
  /^## Delta vs Previous Run/ {section="delta"; print ""; print $0; next}
  /^## Recommended Actions/ {section="actions"; print ""; print $0; next}
  /^## / {section=""; next}
  section=="latest" && /^- / {print}
  section=="delta" && /^- / {print}
  section=="actions" && /^[0-9]+\./ {print}
  ' "$report_path"
}
