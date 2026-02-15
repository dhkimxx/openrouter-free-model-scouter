---
name: openrouter-free-model-watchdog
description: Run OpenRouter free-model availability checks, detect 429/rate-limit trends, and produce markdown health reports for routing decisions. Use when an agent needs recurring free-model scans, latest-vs-previous deltas, stable/unstable model recommendations, or operational summaries.
---

# OpenRouter Free Model Watchdog

## Outcome

Produce two artifacts per run:

- `results/history.xlsx` (timeline matrix)
- `results/availability-report.md` (trend/change report)

## Required Inputs

- `OPENROUTER_API_KEY` in process environment or `.env`

Optional tuning inputs are supported through CLI flags and environment variables.

## Preflight (must pass before running)

1. Run commands from repository root (`pyproject.toml` directory).
2. Install dependencies (`uv sync` recommended).
3. Verify `OPENROUTER_API_KEY` exists in env or `.env`.
4. If the key is missing, stop and request setup (do not run partial workflow).
5. Never print, log, or commit raw API key values.

## Burst-Control Rules (required for agents)

1. Prefer one foreground shell execution per workflow stage; avoid background jobs.
2. For scan+report, prefer a single chained call in one turn:
   - `uv run openrouter-free-model-scouter scan ... && uv run openrouter-free-model-report ...`
3. Do not use tight polling loops. If status checks are unavoidable:
   - minimum interval: 60 seconds
   - maximum checks: 5
4. Avoid full-file reads for large outputs. Prefer concise summaries first.
5. Use `skills/openrouter-free-model-watchdog/scripts/run_scan_and_report.sh` with summary output enabled (default) to reduce follow-up read calls.
6. Use blocking execution with a generous timeout (recommend >= 20 minutes for large scans) instead of background monitor loops.
7. Before any retry cycle, run preflight checks first (`uv` present, API key set) to avoid repetitive failing turns.
8. Recurring schedules must be decided in scheduler config (cron/systemd), not hard-coded in script names or skill logic.
9. For high-frequency schedules, prefer OS scheduler + no-agent shell scripts to avoid LLM turn overhead.

## Default Workflow (cross-platform)

1) Scan free models:

```bash
uv run openrouter-free-model-scouter scan \
  --output-xlsx-path results/history.xlsx \
  --concurrency 1 \
  --max-retries 3 \
  --request-delay-seconds 1.0 \
  --timeout-seconds 25
```

2) Generate availability report:

```bash
uv run openrouter-free-model-report \
  --xlsx-path results/history.xlsx \
  --output-path results/availability-report.md \
  --lookback-runs 24
```

## Optional Execution Paths

### Unix convenience script (`bash`/`zsh`)

```bash
skills/openrouter-free-model-watchdog/scripts/run_scan_and_report.sh
```

Script-only overrides:

- `SCOUT_XLSX_PATH` (default: `results/history.xlsx`)
- `SCOUT_REPORT_PATH` (default: `results/availability-report.md`)
- `SCOUT_LOOKBACK_RUNS` (default: `24`)
- `SCOUT_PRINT_SUMMARY` (default: `1`, set `0` to disable)

### Recurring no-agent scripts (schedule-agnostic)

For frequent automation outside agent runtimes:

```bash
# Scan/report path (no-agent)
skills/openrouter-free-model-watchdog/scripts/run_scan_report_no_agent.sh

# Summary path (no-agent)
skills/openrouter-free-model-watchdog/scripts/generate_summary_no_agent.sh
```

### Fallback without `uv`

```bash
python -m pip install -e .

python -m openrouter_free_model_scouter scan \
  --output-xlsx-path results/history.xlsx \
  --concurrency 1 \
  --max-retries 3 \
  --request-delay-seconds 1.0 \
  --timeout-seconds 25

python -m openrouter_free_model_scouter.availability_report \
  --xlsx-path results/history.xlsx \
  --output-path results/availability-report.md \
  --lookback-runs 24
```

## Reporting Contract

When returning results to users/agents, always include:

1. Report path
2. Latest run counts and rates (`OK`, `429`, `FAIL`)
3. Delta vs previous run (recovered/regressed)
4. Stable and unstable model highlights
5. 1-3 concrete tuning actions

If history has fewer than 2 runs, explicitly state that trend confidence is limited.

## Operational Rules

- Treat blank timeline cells as "not sampled" (not immediate hard-failure).
- Do not delete historical columns from `results/history.xlsx`.
- If 429 pressure is high, prioritize mitigation (lower concurrency, higher delay, narrower model filter).

## References

- Metrics and definitions: `references/report_metrics.md`
- Expected report shape: `references/example_report.md`
- Cron and scheduler recipes: `references/cron_recipes.md`
