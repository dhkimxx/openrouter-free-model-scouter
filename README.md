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

스카우터 옵션(선택):

- `OPENROUTER_SCOUT_TIMEOUT_SECONDS`
- `OPENROUTER_SCOUT_MAX_RETRIES`
- `OPENROUTER_SCOUT_CONCURRENCY`
- `OPENROUTER_SCOUT_MAX_MODELS`
- `OPENROUTER_SCOUT_REQUEST_DELAY_SECONDS`
- `OPENROUTER_SCOUT_REPEAT_COUNT`
- `OPENROUTER_SCOUT_REPEAT_INTERVAL_MINUTES`
- `OPENROUTER_SCOUT_PROMPT`
- `OPENROUTER_SCOUT_OUTPUT_XLSX_PATH` (기본: `results/history.xlsx`)
- `OPENROUTER_SCOUT_FAIL_IF_NONE_OK`

## 설치

```bash
uv sync
```

## 예시 파일

```bash
cp .env.example .env
```

## 실행

```bash
uv run openrouter-free-model-scouter scan
```

또는 모듈 실행:

```bash
uv run python -m openrouter_free_model_scouter scan
```

## 주요 옵션

- `--concurrency`: 동시 실행 수(레이트리밋이 심하면 낮추세요)
- `--retries`: 429/5xx/네트워크 오류에 대한 재시도 횟수
- `--timeout`: 요청 타임아웃(초)
- `--request-delay`: 모델 index에 비례해서 요청 시작을 지연(429 완화 목적)
- `--repeat-count`: 반복 실행 횟수
- `--repeat-interval-minutes`: 반복 주기(분). 두 번째 실행부터 적용
- `--prompt`: 헬스체크용 테스트 프롬프트
- `--out`: 결과 Excel(xlsx) 저장 경로(기본: `results/history.xlsx`)

## 테스트

```bash
uv run python -m unittest discover -s tests -q
```

## 결과 파일

- 기본 출력: `results/history.xlsx`
- 시트: `timeline`
  - 1행: 실행 시각(datetime)
  - 1열: `model_id`
