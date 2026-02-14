# openrouter-free-model-scouter

OpenRouter에서 `:free` 모델을 자동으로 수집하고, 각 모델에 테스트 질문을 보내 정상 응답 여부를 체크한 뒤 결과를 Excel(xlsx) 타임라인으로 저장하는 CLI 도구입니다.

## 요구사항

- Python 3.10+
- OpenRouter API Key

## 환경변수

- `OPENROUTER_API_KEY` (필수)
- `OPENROUTER_BASE_URL` (선택, 기본: `https://openrouter.ai/api/v1`)
- `OPENROUTER_HTTP_REFERER` (선택)
- `OPENROUTER_X_TITLE` (선택)

스카우터 옵션(선택, 기본값 포함):

- `OPENROUTER_SCOUT_TIMEOUT_SECONDS` (기본: `20`)
- `OPENROUTER_SCOUT_MAX_RETRIES` (기본: `2`)
- `OPENROUTER_SCOUT_CONCURRENCY` (기본: `2`)
- `OPENROUTER_SCOUT_MAX_MODELS` (기본: 미설정)
- `OPENROUTER_SCOUT_MODEL_ID_CONTAINS` (기본: 미설정, 예: `mistral,google`)
- `OPENROUTER_SCOUT_REQUEST_DELAY_SECONDS` (기본: `0.3`)
- `OPENROUTER_SCOUT_REPEAT_COUNT` (기본: `1`)
- `OPENROUTER_SCOUT_REPEAT_INTERVAL_MINUTES` (기본: `0`)
- `OPENROUTER_SCOUT_PROMPT` (기본: `Respond with the exact text: OK`)
- `OPENROUTER_SCOUT_OUTPUT_XLSX_PATH` (기본: `results/history.xlsx`)
- `OPENROUTER_SCOUT_FAIL_IF_NONE_OK` (기본: `false`)

## 설치

```bash
uv sync
```

## 예시 파일

```bash
cp .env.example .env
```

모든 예시는 프로젝트 루트(`pyproject.toml`이 있는 디렉토리)에서 실행합니다.

## 실행

```bash
uv run openrouter-free-model-scouter scan
```

또는 모듈 실행:

```bash
uv run python -m openrouter_free_model_scouter scan
```

## 리포트 생성

스캔 결과(`results/history.xlsx`)로부터 가용성 트렌드 리포트를 생성합니다.

```bash
uv run openrouter-free-model-report \
  --xlsx-path results/history.xlsx \
  --output-path results/availability-report.md
```

## 스캔 + 리포트 한번에 실행

크로스플랫폼 기본 실행:

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

Unix 편의 스크립트(`bash`/`zsh`):

```bash
skills/openrouter-free-model-watchdog/scripts/run_scan_and_report.sh
```

## AI 에이전트 통합

여러 AI 코딩 도구에서 자동화 워크플로우로 사용할 수 있습니다.

| 도구 | 설정 파일 |
| --- | --- |
| OpenClaw / Claude Code / Cursor / Windsurf | `AGENTS.md` |
| SKILL.md compatible runners | `skills/openrouter-free-model-watchdog/SKILL.md` |

샘플 리포트 형식은 `skills/openrouter-free-model-watchdog/references/example_report.md`를 참고하세요.

## 주요 옵션

- `--env-file`: .env 파일 경로(기본: `./.env`)
- (참고) OpenRouter 인증/헤더(`OPENROUTER_API_KEY`, `OPENROUTER_HTTP_REFERER`, `OPENROUTER_X_TITLE`)는 CLI 옵션이 아니라 환경변수로만 설정합니다.
- `--timeout-seconds`: 요청 타임아웃(초)
- `--max-retries`: 재시도 횟수(429/5xx/네트워크 오류에 대해 적용)
- `--concurrency`: 동시 실행 수(레이트리밋이 심하면 낮추세요)
- `--max-models`: 상위 N개 모델만 체크
- `--model-id-contains`: 모델 ID에 특정 문자열이 포함된 모델만 체크(예: `--model-id-contains mistral google`)
- `--request-delay-seconds`: 요청 지연(초). index \* delay 만큼 각 모델 체크 시작을 지연
- `--repeat-count`: 반복 실행 횟수
- `--repeat-interval-minutes`: 반복 주기(분). 두 번째 실행부터 적용
- `--healthcheck-prompt`: 헬스체크용 테스트 프롬프트
- `--output-xlsx-path`: 결과 Excel(xlsx) 저장 경로(기본: `results/history.xlsx`)
- `--fail-if-none-ok`: 성공 모델이 0개면 exit code 3

## 테스트

```bash
uv run python -m unittest discover -s tests -q
```

## 결과 파일

- 기본 출력: `results/history.xlsx`
- 시트: `timeline`
  - 1행: 실행 시각(문자열)
  - 1열: `model_id`
- 리포트 출력(기본): `results/availability-report.md`
