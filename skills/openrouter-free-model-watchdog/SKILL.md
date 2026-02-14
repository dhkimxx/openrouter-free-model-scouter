---
name: openrouter-free-model-watchdog
description: Monitor OpenRouter free-model availability and rate-limit behavior, then generate trend/change reports from the project timeline workbook. Use for recurring health checks, 429 spike analysis, free-model routing decisions, and summaries of model stability over time.
---

# OpenRouter Free Model Watchdog

## Overview

Run the project's scanner, update `results/history.xlsx`, and generate a Markdown report focused on availability trends and 429 fluctuations.
This skill is intentionally vendor-neutral: `SKILL.md` + `scripts/` + `references/` are the canonical source.

Documentation sync rule: treat `AGENTS.md` as the shared runbook source and keep this file aligned whenever commands or workflow steps change.

## Workflow

1. Validate runtime prerequisites.
2. Execute a health scan with parameters that match the current goal.
3. Generate a trend report from the Excel timeline.
4. Summarize key deltas, unstable models, and practical tuning actions.

## Step 1: Validate Prerequisites

- Work in the repository root (the directory that contains `pyproject.toml`)
- Ensure dependencies exist: `uv sync`
- `openpyxl` is already included in project dependencies and is installed by `uv sync`
- Ensure API key exists in environment or `.env`:
  - `OPENROUTER_API_KEY`
- If `.env` is missing, copy once: `cp .env.example .env`

Preflight rules for cloned environments:

- Verify `OPENROUTER_API_KEY` exists in process env or `.env` before executing scan/report commands.
- If the key is missing, stop and ask for key setup instead of continuing.
- Never include raw API key values in logs, reports, or committed files.

## Step 2: Run Scan

Use one of these command profiles.

### Cross-platform default (recommended)

```bash
uv run openrouter-free-model-scouter scan \
  --output-xlsx-path results/history.xlsx \
  --concurrency 1 \
  --max-retries 3 \
  --request-delay-seconds 1.0 \
  --timeout-seconds 25

uv run openrouter-free-model-report \
  --xlsx-path results/history.xlsx \
  --output-path results/availability-report.md \
  --lookback-runs 24
```

### Unix convenience runner (`bash`/`zsh`)

```bash
skills/openrouter-free-model-watchdog/scripts/run_scan_and_report.sh
```

Script-only overrides:

- `SCOUT_XLSX_PATH` (default: `results/history.xlsx`)
- `SCOUT_REPORT_PATH` (default: `results/availability-report.md`)
- `SCOUT_LOOKBACK_RUNS` (default: `24`)

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

### Conservative profile (recommended for frequent 429)

```bash
uv run openrouter-free-model-scouter scan \
  --output-xlsx-path results/history.xlsx \
  --concurrency 1 \
  --max-retries 3 \
  --request-delay-seconds 1.0 \
  --timeout-seconds 25
```

### Balanced profile

```bash
uv run openrouter-free-model-scouter scan \
  --output-xlsx-path results/history.xlsx \
  --concurrency 2 \
  --max-retries 2 \
  --request-delay-seconds 0.5 \
  --timeout-seconds 20
```

### Filtered profile (specific providers only)

```bash
uv run openrouter-free-model-scouter scan \
  --output-xlsx-path results/history.xlsx \
  --model-id-contains mistral google qwen \
  --concurrency 1 \
  --request-delay-seconds 0.8
```

For repeated in-process scans, use CLI repeat options only when explicitly requested:

```bash
uv run openrouter-free-model-scouter scan \
  --output-xlsx-path results/history.xlsx \
  --repeat-count 6 \
  --repeat-interval-minutes 10
```

## Step 3: Generate Trend Report

If you already used `run_scan_and_report.sh`, skip this step. Otherwise run:

```bash
uv run openrouter-free-model-report \
  --xlsx-path results/history.xlsx \
  --output-path results/availability-report.md \
  --lookback-runs 24
```

The script reads the timeline sheet and writes a concise report with:

- Latest run snapshot (`OK`, `429`, `FAIL` composition)
- Delta vs previous run (recovered/regressed models)
- Multi-run trend table
- Stable and unstable model candidates
- Tuning recommendations

Metric definitions: `references/report_metrics.md`
Report format example: `references/example_report.md`

## Step 4: Return Result to User

Always include:

- Report file path
- Latest run counts and rates
- Top regressions/recoveries
- 1-3 concrete tuning actions (for example: lower concurrency, increase delay, provider filter)

If timeline history has fewer than 2 runs, state that trend confidence is limited and suggest collecting more runs.

## Operational Rules

- Keep default output paths unless user asks otherwise.
- Do not delete historical columns from `results/history.xlsx`.
- Treat blank cells as "not sampled" rather than hard failure.
- If OpenRouter returns sustained 429 spikes, prioritize mitigation advice over expanding model coverage.
