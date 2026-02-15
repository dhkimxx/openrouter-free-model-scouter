#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

XLSX_PATH="${SCOUT_XLSX_PATH:-results/history.xlsx}"
REPORT_PATH="${SCOUT_REPORT_PATH:-results/availability-report.md}"
LOOKBACK_RUNS="${SCOUT_LOOKBACK_RUNS:-24}"
PRINT_SUMMARY="${SCOUT_PRINT_SUMMARY:-1}"

DEFAULT_SCAN_ARGS=(
  --concurrency 1
  --max-retries 3
  --request-delay-seconds 1.0
  --timeout-seconds 25
)

if [[ $# -gt 0 ]]; then
  SCAN_ARGS=("$@")
else
  SCAN_ARGS=("${DEFAULT_SCAN_ARGS[@]}")
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "[ERROR] 'uv' not found. Install uv and run: uv sync" >&2
  exit 1
fi

has_api_key_in_dotenv() {
  if [[ ! -f ".env" ]]; then
    return 1
  fi

  local line raw_value value

  line="$(grep -E '^[[:space:]]*OPENROUTER_API_KEY[[:space:]]*=' .env | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi

  raw_value="${line#*=}"
  raw_value="${raw_value%%#*}"

  value="$(printf '%s' "$raw_value" | sed -E "s/^[[:space:]]+//; s/[[:space:]]+$//; s/^\"(.*)\"$/\\1/; s/^'(.*)'$/\\1/")"
  [[ -n "$value" ]]
}

if [[ -z "${OPENROUTER_API_KEY:-}" ]] && ! has_api_key_in_dotenv; then
  echo "[ERROR] OPENROUTER_API_KEY is missing (env or .env)." >&2
  echo "[HINT] Set OPENROUTER_API_KEY in environment or create .env from .env.example." >&2
  exit 1
fi

run_scan() {
  uv run openrouter-free-model-scouter scan "$@"
}

run_report() {
  uv run openrouter-free-model-report "$@"
}

echo "[1/2] Running OpenRouter free-model scan..."
run_scan --output-xlsx-path "$XLSX_PATH" "${SCAN_ARGS[@]}"

echo "[2/2] Generating availability report..."
run_report \
  --xlsx-path "$XLSX_PATH" \
  --output-path "$REPORT_PATH" \
  --lookback-runs "$LOOKBACK_RUNS"

echo "[OK] Report path: $REPORT_PATH"

print_summary() {
  awk '
  /^## Latest Run Snapshot/ {section="latest"; print ""; print $0; next}
  /^## Delta vs Previous Run/ {section="delta"; print ""; print $0; next}
  /^## Recommended Actions/ {section="actions"; print ""; print $0; next}
  /^## / {section=""; next}
  section=="latest" && /^- / {print}
  section=="delta" && /^- / {print}
  section=="actions" && /^[0-9]+\./ {print}
  ' "$REPORT_PATH"
}

if [[ "$PRINT_SUMMARY" != "0" ]]; then
  echo "[3/3] Summary (set SCOUT_PRINT_SUMMARY=0 to disable):"
  print_summary
fi
