#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/scout_common.sh
source "$SCRIPT_DIR/lib/scout_common.sh"

ROOT_DIR="$(scout_repo_root "${BASH_SOURCE[0]}")"
cd "$ROOT_DIR"

XLSX_PATH="${SCOUT_XLSX_PATH:-results/history.xlsx}"
REPORT_PATH="${SCOUT_REPORT_PATH:-results/availability-report.md}"
SUMMARY_PATH="${SCOUT_SUMMARY_PATH:-results/summary.md}"
LOOKBACK_RUNS="${SCOUT_LOOKBACK_RUNS:-24}"
SUMMARY_TITLE="${SCOUT_SUMMARY_TITLE:-Summary}"

scout_require_uv

uv run openrouter-free-model-report \
  --xlsx-path "$XLSX_PATH" \
  --output-path "$REPORT_PATH" \
  --lookback-runs "$LOOKBACK_RUNS"

mkdir -p "$(dirname "$SUMMARY_PATH")"

{
  echo "# ${SUMMARY_TITLE} ($(date '+%Y-%m-%d'))"
  scout_print_report_snapshot "$REPORT_PATH"
} >"$SUMMARY_PATH"

echo "[OK] Summary path: $SUMMARY_PATH"
cat "$SUMMARY_PATH"
