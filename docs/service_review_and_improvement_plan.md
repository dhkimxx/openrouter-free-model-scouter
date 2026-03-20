# OpenRouter Free Model Scouter - 서비스 검토 및 개선안

## 1. 현재 서비스 아키텍처 및 현황 검토

현재 프로젝트는 OpenRouter의 무료(`:free`) 모델들을 대상으로 상태(연결 가능 여부) 및 지연 시간(Latency)을 주기적으로 확인하고, 그 결과를 웹 대시보드로 시각화하는 시스템입니다.

### 주요 구성 요소
* **Backend**: FastAPI를 사용한 API 서버 제공 및 APScheduler를 통한 백그라운드 스케줄링.
* **Worker**: `ThreadPoolExecutor`를 사용하여 동기식(requests 추정) HTTP 요청으로 모델 Health Check 수행.
* **Database**: SQLite (SQLAlchemy ORM)를 사용하여 매 실행(Run)마다 각 모델의 체크 결과(HealthCheck) 저장.
* **Frontend**: Vanilla JS와 TailwindCSS, ECharts를 사용한 반응형 SPA.

### 현재 구조의 장점
* 구성이 단순하여 배포(Docker Compose) 및 로컬 실행이 매우 쉽습니다.
* 외부 의존성(Redis, PostgreSQL 등)을 최소화하여 단일 SQLite 파일만으로 데이터 영속성을 보장합니다.
* 직관적인 Vanilla JS 프론트엔드로 빌드 과정 없이 정적 파일 제공만으로 동작합니다.

---

## 2. 식별된 문제점 및 한계 (Pain Points)

### 2.1. 동시성 및 네트워크 I/O 병목
* **문제**: `healthcheck_service.py`에서 `ThreadPoolExecutor`를 사용하여 스레드 풀 기반으로 검사를 진행하고 있습니다. 수백 개의 모델을 동시에 스캔할 때 스레드 생성 오버헤드와 블로킹 I/O로 인해 자원 효율성이 떨어집니다.
* **영향**: 스캔 주기가 짧아지거나 모델 수가 급증할 경우 호스트 리소스를 불필요하게 많이 점유하며, 네트워크 지연에 취약해집니다.

### 2.2. 데이터베이스 조회 성능 (N+1 및 대량 데이터 로드)
* **문제**: `stats_service.py`의 `get_models_stats()`를 보면 최근 100개의 스캔 결과 목록(`Run`)을 가져온 뒤, 관련된 `HealthCheck` 데이터를 모두 메모리로 가져와서 그룹핑 및 통계를 계산합니다. ($100 \times 200 = 20,000$ row 이상 메모리 적재)
* **영향**: 대시보드 API(`/api/models`) 호출 시마다 무거운 조작이 일어나 CPU와 DB 오버헤드가 발생하며 응답 속도가 느려질 수 있습니다. 방문자가 많아지면 치명적인 병목이 됩니다.

### 2.3. SQLite 동시성 문제 (Database is Locked)
* **문제**: 주기적으로 워커가 다량의 쓰기 작업을 수행하면서, 동시에 FastAPI가 무거운 읽기 트랜잭션을 실행합니다.
* **영향**: SQLite는 파일 기반 잠금(File-level locking, 특히 WAL 모드가 아닐 경우)을 사용하므로 잦은 "database is locked" 에러가 발생할 가능성이 높습니다.

### 2.4. 프론트엔드 확장성 제한
* **문제**: 모든 데이터를 `/api/models`에서 한 번에 가져와 브라우저 메모리에 담고(`allModels`) 클라이언트 사이드에서 정렬과 검색을 처리합니다.
* **영향**: 데이터 건수가 수천 건이 될 경우 브라우저 렌더링 지연이 발생하며, 로직 확장이(예: 페이지네이션, 복합 필터 등) 어려워집니다.

---

## 3. 서비스 개선안 (Improvement Plan)

### 3.1. 백엔드 동시성 모델 전환 (Async/Await)
* **개선**: 기존 동기 방식(`requests` + `ThreadPoolExecutor`)을 비동기 방식(`httpx` + `asyncio`)으로 완전히 전환합니다.
* **효과**: 적은 메모리와 CPU 스레드로도 수천 개의 HTTP 요청을 동시에 관리할 수 있어 스캐닝 속도와 리소스 효율이 비약적으로 상승합니다.

### 3.2. 실시간 통계 캐싱 및 집계 테이블(Summary Table) 도입
* **개선**: 
  1. API 호출 시마다 Raw Data 20,000건을 읽어 통계를 내는 대신, Worker가 스캔을 완료하는 즉시 `최신 통계 뷰` 혹은 `Cache(In-memory or Redis)`를 업데이트하도록 구조를 변경합니다.
  2. অথবা SQLite의 기능을 활용하기 위해 View나 Materialized 형태로 요약 테이블을 유지합니다.
* **효과**: 대시보드 API 응답 시간이 $O(N)$에서 $O(1)$에 가깝게 대폭 감소합니다.

### 3.3. 데이터베이스 고도화 및 최적화
* **개선**: 
  1. SQLite 연결 설정에 `PRAGMA journal_mode=WAL;` 설정을 추가하여 읽기와 쓰기가 서로 차단되지 않도록 하여 DB 잠금 이슈를 방지합니다.
  2. 장기적으로 프로덕션(Docker) 환경에서는 PostgreSQL로의 전환을 지원할 수 있도록 설정 유연석(Database URL)을 확보합니다.
* **효과**: 데이터 무결성 훼손 없이 동시 접속 및 백그라운드 워커의 안정성이 확보됩니다.

### 3.4. API 및 프론트엔드 최적화
* **개선**: 
  1. 데이터가 많아질 것에 대비하여 API에 서버 사이드 페이지네이션(Pagination) 및 정렬 기능을 추가합니다.
  2. 프론트엔드 코드가 비대해지는 것을 방지하기 위해 파일 혹은 모듈 단위로 분리하고, 장기적으로는 가벼운 프레임워크(Vue.js, Svelte, 등) 도입을 고려합니다.
* **효과**: 네트워크 대역폭 절약과 클라이언트 측 렌더링 성능 향상.

---

## 4. 요약 및 우선순위 (Action Items)

| 우선순위 | 작업 내용 | 난이도 | 기대 효과 |
|---|---|---|---|
| **High** | SQLite WAL 모드 적용 (`database.py` 수정) | 낮음 | DB Lock 방지 |
| **High** | `httpx` 및 `asyncio`를 활용한 Async Worker 로 재작성 | 중간 | 스캐너 리소스 점유 축소 및 속도 비약적 향상 |
| **Medium**| `stats_service.py` 쿼리 튜닝 (Summary Cache 테이블 사용 또는 캐시 계층 추가) | 중간 | 대시보드 로딩 응답 개선 (극적인 속도 향상) |
| **Low**  | 프론트엔드 클라이언트 사이드 페이지네이션 또는 Vue.js/React 마이그레이션 | 높음 | UI/UX 개선 및 코드 유지보수성 향상 |
