# OpenRouter Free Model Scouter

OpenRouter에서 무료(`:free`) 모델을 자동으로 수집해 헬스체크(정상 응답 및 Latency)를 수행하고, 그 결과를 SQLite DB에 저장하여 **FastAPI 및 ECharts 기반의 반응형 대시보드**로 실시간 모니터링할 수 있는 도구입니다.

## 주요 기능
- **백그라운드 스캐너 (Worker):** 설정된 주기로 전체 무료 모델에 대해 동시에 비동기 헬스체크 수행.
- **REST API (FastAPI):** 스캔 결과를 요약 통계 및 시계열 데이터 포맷으로 제공.
- **웹 대시보드 (Vanilla JS + ECharts):** 총 사용 가능한 모델 수, Uptime 추이, 최근 응답 지연 시간(Sparkline) 및 복합 차트 지원.

## 기술 스택
- **Backend:** Python 3.10+, FastAPI, SQLAlchemy (SQLite)
- **Frontend:** HTML5, TailwindCSS, Vanilla JS, ECharts
- **Package Manager:** `uv`

## 환경변수

- `OPENROUTER_API_KEY` (필수)
- `OPENROUTER_BASE_URL` (선택, 기본: `https://openrouter.ai/api/v1`)
- `OPENROUTER_HTTP_REFERER` (선택)
- `OPENROUTER_X_TITLE` (선택)

스카우터 옵션(선택, 기본값 포함):
- `OPENROUTER_SCOUT_TIMEOUT_SECONDS` (기본: `20`)
- `OPENROUTER_SCOUT_MAX_RETRIES` (기본: `2`)
- `OPENROUTER_SCOUT_CONCURRENCY` (기본: `2`)
- `OPENROUTER_SCOUT_REQUEST_DELAY_SECONDS` (기본: `0.3`)

## 설치

```bash
## 실행 (Docker Compose 권장)

## 실행 (Docker Compose 권장)

기본적으로 백그라운드 스캐너(자동 반복)와 대시보드 API가 통합된 컨테이너로 실행됩니다. `OPENROUTER_SCOUT_INTERVAL_HOURS` 속성으로 스캔 주기를 제어할 수 있습니다 (기본: `1`시간).

### 로컬 개발 환경용 (Dev)
포트 8000번이 바로 로컬머신으로 노출됩니다.
```bash
docker-compose -f docker-compose.dev.yml up -d --build
```
접속 주소: `http://localhost:8000/`

### 운영 배포용 (Prod with Traefik)
내부 포트가 노출되지 않고, Traefik 인그레스를 통해서 라우팅 및 TLS가 처리됩니다 (`openrouter-scouter.duckdns.org`). 서버 리소스 제한(limits/reservations)이 함께 적용됩니다.
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```
접속 주소: `https://openrouter-scouter.duckdns.org/`

> **공통 유의사항:**
> - 스캔 결과 DB는 호스트의 `./results` 디렉토리에 마운트되어 컨테이너 재시작 시에도 데이터가 유지됩니다.
> - 로그 확인: `docker logs -f openrouter-scouter-dev` (또는 `openrouter-scouter-prod`)

## 로컬 직접 실행 (개발용)

**백그라운드 스캐너 (1회 스캔) 직접 실행:**
```bash
uv run openrouter-free-model-scouter scan
```

**FastAPI 웹 대시보드 서버 (및 스케줄러) 실행:**
```bash
uv run openrouter-free-model-scouter serve --host 0.0.0.0 --port 8000
```
> **Note:** `serve`를 실행하면 곧바로 1회 스캔이 트리거되고, 그 이후부터 백그라운드 스케줄러(APScheduler)가 지정된 간격마다 주기적으로 스캔을 수행합니다.

## 테스트

```bash
uv run pytest -v
```

## 디렉토리 구조 및 레이어
- `src/openrouter_free_model_scouter/api`: FastAPI 라우터 및 읽기 전용 엔드포인트
- `src/openrouter_free_model_scouter/services`: 통계 계산 (Uptime, 분당 Latency 등) 비즈니스 로직
- `src/openrouter_free_model_scouter/models.py`: SQLAlchemy 기반 SQLite ORM 모델
- `src/openrouter_free_model_scouter/worker`: 기존 모델 체크 로직을 모듈화한 백그라운드 스캐너
- `src/openrouter_free_model_scouter/static`: Vanilla JS 프론트엔드 UI 대시보드
