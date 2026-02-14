#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

XLSX_PATH="${SCOUT_XLSX_PATH:-results/history.xlsx}"
REPORT_PATH="${SCOUT_REPORT_PATH:-results/availability-report.md}"
LOOKBACK_RUNS="${SCOUT_LOOKBACK_RUNS:-24}"

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
