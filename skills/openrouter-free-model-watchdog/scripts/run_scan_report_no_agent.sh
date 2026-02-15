#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/scout_common.sh
source "$SCRIPT_DIR/lib/scout_common.sh"

ROOT_DIR="$(scout_repo_root "${BASH_SOURCE[0]}")"
cd "$ROOT_DIR"

LOCK_DIR="${SCOUT_NO_AGENT_LOCK_DIR:-results/.scan-report-no-agent.lock}"
LOG_PATH="${SCOUT_NO_AGENT_LOG_PATH:-results/logs/scan-report-no-agent.log}"

mkdir -p "$(dirname "$LOCK_DIR")"
mkdir -p "$(dirname "$LOG_PATH")"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[SKIP] Another scan/report run is still running: $LOCK_DIR" >&2
  exit 0
fi

cleanup() {
  rmdir "$LOCK_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] no-agent scan/report run start"
  SCOUT_PRINT_SUMMARY="${SCOUT_PRINT_SUMMARY:-0}" \
    "$SCRIPT_DIR/run_scan_and_report.sh" "$@"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] no-agent scan/report run end"
} >>"$LOG_PATH" 2>&1
