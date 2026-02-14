# Report Metrics

## Status Buckets

- `OK`: Cell starts with `OK` (for example: `OK (812ms)`)
- `429`: Cell value equals `429`
- `FAIL`: Non-empty value that is not `OK` or `429` (for example: `HTTP 500`, `network`)
- `MISSING`: Empty cell, interpreted as not sampled in that run

## Per-Run Metrics

- `checked_models`: Count of non-empty cells for that run
- `ok_rate`: `OK / checked_models`
- `rate_limited_rate`: `429 / checked_models`
- `fail_rate`: `FAIL / checked_models`

## Delta Metrics (Latest vs Previous)

- `recovered_models`: Previous run non-OK and latest run OK
- `regressed_models`: Previous run OK and latest run non-OK
- `ok_rate_delta_pp`: Latest `ok_rate` minus previous `ok_rate` in percentage points
- `429_rate_delta_pp`: Latest `rate_limited_rate` minus previous value in percentage points

## Model Stability Metrics

Computed on the configured lookback window.

- `samples`: Number of non-empty observations for the model
- `ok_rate`: `OK / samples`
- `429_rate`: `429 / samples`
- `flip_count`: Count of transitions where status category changed between adjacent sampled runs
- `latest_status`: Most recent non-empty category

## Ranking Rules

- Stable candidates: high `ok_rate` with enough `samples`
- Unstable candidates: high `flip_count`, high `429_rate`, or low `ok_rate`
- Recommendations prioritize reducing `429_rate` and selecting stable candidates
