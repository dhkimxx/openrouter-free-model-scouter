# OpenRouter Free Model Scouter Agent Guide

> **TL;DR**: `uv sync && cp .env.example .env` 후 API 키를 설정하고, `uv run openrouter-free-model-scouter scan ...` 다음 `uv run openrouter-free-model-report ...`를 실행하면 됩니다.

This repository supports a recurring workflow:

1. Scan OpenRouter `:free` models.
2. Record availability results to `results/history.xlsx`.
3. Generate a trend/change report at `results/availability-report.md`.

Documentation sync rule: this file is the shared runbook source for cross-tool agents. When commands or workflow steps change, update `skills/openrouter-free-model-watchdog/SKILL.md` in the same change.
Execution scope: run all commands from the repository root (the directory containing `pyproject.toml`).

## Runbook

### 1) Prepare environment

- Run `uv sync` (installs all dependencies including `openpyxl`)
- Ensure `.env` exists (`cp .env.example .env` if needed)
- Set `OPENROUTER_API_KEY`

Preflight rules for cloned environments:

- Before any scan/report command, verify `OPENROUTER_API_KEY` exists in either process env or `.env`.
- If the key is missing, stop immediately and request user input instead of running partial commands.
- Never print, log, or commit the raw API key value.

### 2) Run scan + report

Cross-platform default (recommended):

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

Unix convenience script (`bash`/`zsh`):

```bash
skills/openrouter-free-model-watchdog/scripts/run_scan_and_report.sh
```

Script-only environment overrides:

- `SCOUT_XLSX_PATH` (default: `results/history.xlsx`)
- `SCOUT_REPORT_PATH` (default: `results/availability-report.md`)
- `SCOUT_LOOKBACK_RUNS` (default: `24`)

### 3) Run scan only

```bash
uv run openrouter-free-model-scouter scan \
  --output-xlsx-path results/history.xlsx \
  --concurrency 1 \
  --max-retries 3 \
  --request-delay-seconds 1.0 \
  --timeout-seconds 25
```

### 4) Generate report only

```bash
uv run openrouter-free-model-report \
  --xlsx-path results/history.xlsx \
  --output-path results/availability-report.md \
  --lookback-runs 24
```

### 5) Fallback without `uv`

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

## Example prompts

- "OpenRouter free model 스캔 돌려줘"
- "최근 429 스파이크 분석해줘"
- "안정적인 free model 추천해줘"

## Reporting expectations

- Include latest run counts/rates (`OK`, `429`, `FAIL`)
- Include delta vs previous run (recovered/regressed)
- Include top stable and unstable model candidates
- Include 1-3 concrete tuning actions
- Use metric definitions from `skills/openrouter-free-model-watchdog/references/report_metrics.md`
- Report output format example: `skills/openrouter-free-model-watchdog/references/example_report.md`

## Notes

- Keep historical columns in `results/history.xlsx` (no destructive cleanup)
- Treat blank timeline cells as "not sampled"
- If 429 rate spikes, prefer mitigation advice over expanding model coverage
- Portable skill source lives in `skills/openrouter-free-model-watchdog/` (`SKILL.md`, `scripts/`, `references/`)
- Vendor-specific adapter metadata files are intentionally omitted by default
