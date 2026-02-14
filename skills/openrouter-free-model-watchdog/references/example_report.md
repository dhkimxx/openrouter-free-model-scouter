# OpenRouter Free Model Availability Report (Example)

Generated at: 2026-02-14 00:38:26 UTC
Source workbook: `results/history.xlsx`
Runs analyzed: 11 (from 2025-12-14 16:55:23 to 2026-02-13 14:09:54)

## Latest Run Snapshot

- Run: `2026-02-13 14:09:54`
- Checked models: 29
- OK: 13 (44.8%)
- 429: 13 (44.8%)
- FAIL: 3 (10.3%)

## Delta vs Previous Run

- OK rate delta: +0.0pp
- 429 rate delta: -3.4pp
- Recovered models: none
- Regressed models: none

## Multi-run Trend (excerpt)

| Run | Checked | OK | 429 | FAIL | OK % | 429 % | FAIL % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-02-13 13:53:54 | 29 | 13 | 12 | 4 | 44.8% | 41.4% | 13.8% |
| 2026-02-13 13:59:27 | 29 | 13 | 14 | 2 | 44.8% | 48.3% | 6.9% |
| 2026-02-13 14:09:54 | 29 | 13 | 13 | 3 | 44.8% | 44.8% | 10.3% |

## Stable Candidate Models (excerpt)

- `arcee-ai/trinity-mini:free`
- `alibaba/tongyi-deepresearch-30b-a3b:free`
- `amazon/nova-2-lite-v1:free`

## Unstable Models / 429 Risk (excerpt)

- `cognitivecomputations/dolphin-mistral-24b-venice-edition:free`
- `google/gemini-2.0-flash-exp:free`
- `mistralai/mistral-small-3.1-24b-instruct:free`

## Recommended Actions (example)

1. High 429 pressure: run with `--concurrency 1 --request-delay-seconds 1.0 --max-retries 3`.
2. Prefer stable free models as primary routing candidates.
3. Treat high-variance models as fallback-only until trend improves.
