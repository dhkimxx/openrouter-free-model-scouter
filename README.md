# openrouter-free-model-scouter

OpenRouter에서 `:free` 모델을 자동으로 수집하고, 각 모델에 테스트 질문을 보내 정상 응답 여부를 체크한 뒤 결과를 SQLite DB 타임라인으로 저장하고 웹 대시보드로 실시간 확인하는 CLI 도구입니다.

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
- `OPENROUTER_SCOUT_DB_PATH` (기본: `results/scouter.db`)
- `OPENROUTER_SCOUT_FAIL_IF_NONE_OK` (기본: `false`)
- `OPENROUTER_SCOUT_WEB_HOST` (기본: `0.0.0.0`)
- `OPENROUTER_SCOUT_WEB_PORT` (기본: `8000`)



## 설치

```bash
uv sync
```

## 예시 파일

```bash
cp .env.example .env
```

모든 예시는 프로젝트 루트(`pyproject.toml`이 있는 디렉토리)에서 실행합니다.

## 클론 환경 Preflight

다른 에이전트가 이 레포를 클론해서 실행하는 경우 아래를 먼저 확인하세요.

- `OPENROUTER_API_KEY`가 process env 또는 `.env`에 존재해야 합니다.
- 키가 없으면 스캔/리포트 실행을 중단하고 먼저 키 설정을 요청해야 합니다.
- API 키 원문은 로그, 리포트, 커밋에 절대 노출하지 마세요.

## 실행

```bash
uv run openrouter-free-model-scouter scan
```

또는 모듈 실행:

```bash
uv run python -m openrouter_free_model_scouter scan
```

## 웹 대시보드

스캔 결과(`results/scouter.db`)로부터 가용성 트렌드를 실시간으로 확인할 수 있는 대시보드 서버를 실행할 수 있습니다.

```bash
uv run openrouter-free-model-scouter serve --host 0.0.0.0 --port 8000
```
접속 주소: `http://localhost:8000/`

## 스캔 + 리포트 한번에 실행

크로스플랫폼 기본 실행:

```bash
uv run openrouter-free-model-scouter scan \
  --db-path results/scouter.db \
  --concurrency 1 \
  --max-retries 3 \
  --request-delay-seconds 1.0 \
  --timeout-seconds 25

uv run openrouter-free-model-scouter serve --port 8000
```

Unix 편의 스크립트(`bash`/`zsh`):

```bash
skills/openrouter-free-model-watchdog/scripts/run_scan_and_report.sh
```

스크립트 환경변수 오버라이드:

- `SCOUT_CSV_PATH` (기본: `results/history.csv`)
- `SCOUT_REPORT_PATH` (기본: `results/availability-report.md`)
- `SCOUT_LOOKBACK_RUNS` (기본: `24`)
- `SCOUT_PRINT_SUMMARY` (기본: `1`, `0`이면 요약 출력 비활성화)

## 에이전트 호출량 버스트 방지

- 기본 실행은 `run_scan_and_report.sh` 1회(포그라운드)로 처리하고, 백그라운드 실행 + 짧은 주기 폴링은 피하세요.
- 상태 확인이 꼭 필요하면 60초 미만 간격 폴링은 금지하고, 최대 5회 이내로 제한하세요.
- 에러 복구 시에는 설치/동기화/재실행을 가능한 한 한 번의 명령으로 묶어 turn 수를 줄이세요.
- 리포트 원문 전체 대신 스크립트 요약 출력부터 확인해 컨텍스트 토큰 사용량을 줄이세요.

## 크론 운영 (주기 결정은 크론에서)

작업 주기는 코드에 고정하지 말고, OS 크론에서 그때 결정하세요.
고빈도 작업은 AI 에이전트를 거치지 말고 스크립트를 직접 실행하도록 분리합니다.

```cron
# scan + report (무에이전트): <SCAN_SCHEDULE>를 원하는 주기로 설정
<SCAN_SCHEDULE> cd /ABS/PATH/openrouter-free-model-scouter && skills/openrouter-free-model-watchdog/scripts/run_scan_report_no_agent.sh

# summary 생성 (기본: 무AI): <SUMMARY_SCHEDULE>를 원하는 주기로 설정
<SUMMARY_SCHEDULE> cd /ABS/PATH/openrouter-free-model-scouter && skills/openrouter-free-model-watchdog/scripts/generate_summary_no_agent.sh
```

관련 스크립트:

- `skills/openrouter-free-model-watchdog/scripts/run_scan_report_no_agent.sh`
  - 중복 실행 방지 lock + 로그 파일(`results/logs/scan-report-no-agent.log`)
- `skills/openrouter-free-model-watchdog/scripts/generate_summary_no_agent.sh`
  - 최신 리포트 재생성 후 `results/summary.md` 출력

서술형 AI 요약이 필요하면, 위에서 생성한 `results/summary.md`를 입력으로 summary 주기당 1회만 에이전트를 호출하세요.

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
- `--db-path`: 결과 DB 저장 경로(기본: `results/scouter.db`)
- `--fail-if-none-ok`: 성공 모델이 0개면 exit code 3

`serve` 커맨드 옵션:
- `--host`: 바인딩 호스트(기본: `0.0.0.0`)
- `--port`: 포트 번호(기본: `8000`)

## 테스트

```bash
uv run python -m unittest discover -s tests -q
```

## 결과 파일

- 기본 출력: `results/scouter.db` (SQLite 파일)
  - `runs` 테이블: 실행 타임스탬프 기록
  - `healthchecks` 테이블: 모델별 결과 기록
