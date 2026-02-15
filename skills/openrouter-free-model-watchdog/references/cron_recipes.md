# Cron Recipes (Schedule-Decided-at-Runtime)

## Goal

- Scan/report jobs run without invoking an AI agent runtime.
- Summary jobs remain deterministic (no AI) by default, with optional once-per-run AI narrative.

## Template crontab (choose schedules later)

```cron
# 1) Scan/report job: put your schedule in <SCAN_SCHEDULE>
<SCAN_SCHEDULE> cd /ABS/PATH/openrouter-free-model-scouter && skills/openrouter-free-model-watchdog/scripts/run_scan_report_no_agent.sh

# 2) Summary job: put your schedule in <SUMMARY_SCHEDULE>
<SUMMARY_SCHEDULE> cd /ABS/PATH/openrouter-free-model-scouter && skills/openrouter-free-model-watchdog/scripts/generate_summary_no_agent.sh
```

## Concrete example (optional)

```cron
# Example only: scan/report every hour
0 * * * * cd /ABS/PATH/openrouter-free-model-scouter && skills/openrouter-free-model-watchdog/scripts/run_scan_report_no_agent.sh

# Example only: summary in the morning
0 7 * * * cd /ABS/PATH/openrouter-free-model-scouter && skills/openrouter-free-model-watchdog/scripts/generate_summary_no_agent.sh
```

## Optional AI step after summary generation

If you still want an LLM-written narrative, call the agent once per summary run and feed it:

- `results/summary.md` (preferred compact input)
- or `results/availability-report.md` (full detail)

Keep frequent ingestion on the no-agent script path.
