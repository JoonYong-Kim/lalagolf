# GolfRaiders v2 Architecture Proposal

## 1. Architecture Goals

- v1의 검증된 파서/분석 로직을 재사용하면서 UI, API, 데이터 저장소를 분리한다.
- 멀티 유저 환경에서 사용자별 데이터 격리와 공유 권한을 명확히 보장한다.
- Ask 질의를 정형 데이터 조회 중심으로 안전하게 제공하고, RAG 검색은 post-MVP로 확장한다.
- 인사이트를 연습 계획, 연습 다이어리, 다음 라운드 목표, 목표 평가로 연결하는 개선 루프를 제공한다.
- 모바일/데스크톱 모두에서 빠르게 동작하는 웹 앱을 만든다.
- 초기에는 단일 서버 또는 Docker Compose로 운영 가능하게 하고, 이후 서비스별 분리를 쉽게 한다.

## 2. Recommended Stack

- Frontend: Next.js App Router, React 19, TypeScript.
- UI: Tailwind CSS + shadcn/ui style component system.
- Charts: Recharts, Tremor-style components, or equivalent React chart library.
- Backend API: FastAPI.
- Analytics Core: Python package. v1의 `data_parser`, `metrics`, `shot_model`, `expected_value`, `strokes_gained`, `recommendations`를 이관한다.
- Database: PostgreSQL.
- Vector Search: pgvector post-MVP.
- ORM/Migration: SQLAlchemy 2.x + Alembic.
- Auth: API-managed session or JWT with refresh token. Production에서는 secure httpOnly cookie 기반을 우선한다.
- Worker: Celery/RQ/Arq 중 하나. 초기 구현은 RQ 또는 Arq처럼 단순한 queue를 권장한다.
- Cache/Queue Backend: Redis.
- LLM Runtime: Ollama.
- Deployment: Docker Compose first. 이후 web/api/worker/db/ollama 분리 배포 가능하게 설계한다.

## 3. High-Level Components

```text
Browser
  |
  | HTTPS
  v
Next.js Web App
  |
  | REST/JSON or typed client
  v
FastAPI Backend
  |                 |
  | SQL             | Queue jobs
  v                 v
PostgreSQL       Worker
  |                 |
  |                 | parse/analyze
  v                 v
Ask context      Optional Ollama
```

## 4. Service Responsibilities

### 4.1 Web App

- MVP: 로그인 전 최소 진입 화면.
- Post-MVP: 공개 홈, 샘플 분석, 공개 라운드 화면.
- 로그인 후 Dashboard, Rounds, Round Detail, Analysis, Practice, Goals, Upload Review, Ask.
  Profile/Feed/Settings는 post-MVP 또는 별도 계정 설정 범위로 둔다.
- 서버 컴포넌트는 초기 데이터 로딩과 SEO가 필요한 공개 화면에 사용한다.
- 클라이언트 컴포넌트는 필터, 차트 상호작용, 업로드 리뷰, 채팅에 사용한다.
- 인증 토큰 또는 세션 쿠키는 브라우저에서 직접 조작하지 않는다.

### 4.2 API Server

- 인증, 권한, 사용자 데이터 격리.
- 라운드/홀/샷 CRUD.
- 업로드 파일 등록 및 파싱 작업 요청.
- 분석 결과 조회.
- 연습 계획, 연습 다이어리, 다음 라운드 목표, 목표 평가 관리.
- 공유 링크 및 공개 데이터 필터링.
- Ask 요청 orchestration.
- Worker 작업 상태 조회.

### 4.3 Analytics Core

- v1 Python 분석 로직을 framework-independent package로 분리한다.
- 입력은 DB row가 아니라 명시적인 dict/dataclass/list 형태로 받는다.
- 출력은 API 저장/응답에 적합한 구조화된 dict로 반환한다.
- 주요 모듈:
  - parser: v1 텍스트 라운드 파일 파싱.
  - metrics: 라운드/홀/샷 지표 계산.
  - shot_model: 샷 카테고리와 상태 정규화.
  - expected_value: expected score table.
  - strokes_gained: shot_value 계산.
  - recommendations: insight candidate 생성.
  - insight_dedupe: 중복 insight 병합 및 우선순위 정리.

### 4.4 Worker

- 업로드 파일 파싱.
- 파싱 리뷰 데이터 생성.
- 라운드 저장 후 분석 재계산.
- expected table/shot values 갱신.
- insight 생성 및 중복 제거.
- 목표 자동 평가.
- 라운드 요약 텍스트 생성.
- embedding 생성은 post-MVP RAG에서 추가한다.
- 장기적으로 public feed materialization, notification도 담당 가능.

### 4.5 PostgreSQL

- 모든 정형 데이터의 source of truth.
- 사용자, 라운드, 홀, 샷, 지표, 추천, 공유, LLM 메시지를 저장한다.
- post-MVP에서 pgvector extension으로 embedding을 저장하고 권한 필터와 함께 검색한다.
- JSONB는 LLM 근거, 분석 evidence, 파싱 경고처럼 스키마가 느슨한 보조 정보에 사용한다.

### 4.6 Ollama Service

- `/api/chat`으로 답변 생성.
- `/api/embed`으로 embedding 생성은 post-MVP.
- API server/worker에서 직접 호출한다.
- 모델명, timeout, keep_alive, stream 여부는 환경변수로 관리한다.
- Ollama 장애 시 일반 분석 기능과 MVP Ask 템플릿 답변은 계속 동작해야 한다.

## 5. Request Flows

### 5.1 Login

1. 사용자가 이메일/비밀번호로 로그인한다.
2. API가 credentials를 검증한다.
3. API가 secure httpOnly session cookie 또는 access/refresh token을 발급한다.
4. Web app은 `/me` 또는 session endpoint로 현재 사용자 정보를 가져온다.
5. 모든 private API는 user_id scope를 강제한다.

### 5.2 Round Upload

1. 사용자가 라운드 텍스트 파일을 업로드한다.
2. API가 `source_files` row를 만들고 파일을 저장한다.
3. API가 parse job을 queue에 넣는다.
4. Worker가 파일을 파싱하고 `upload_reviews`에 normalized preview와 warnings를 저장한다.
5. Web app은 review 화면에서 오류/경고를 보여준다.
6. 사용자가 수정 후 commit한다.
7. API가 `rounds`, `holes`, `shots`를 트랜잭션으로 저장한다.
8. API 또는 Worker가 analysis job을 queue에 넣는다.

### 5.3 Analysis Recalculation

1. Worker가 사용자 또는 라운드 scope로 관련 데이터를 조회한다.
2. Analytics core가 metrics, expected table, shot values, recommendations를 계산한다.
3. 결과를 `round_metrics`, `shot_values`, `insights`, `analysis_snapshots`에 저장한다.
4. 기존 insight와 새 insight를 비교해 중복 또는 stale 데이터를 정리한다.

### 5.4 Practice and Goal Loop

1. 사용자가 Dashboard, Analysis, Round Detail의 insight에서 연습 계획을 만든다.
2. API가 `practice_plans` row를 만들고 insight의 category/root_cause/next_action을 초기값으로 사용한다.
3. 사용자는 연습 후 `/practice`에서 다이어리 entry를 남긴다.
4. 사용자는 연습 계획 또는 인사이트에서 다음 라운드 목표를 만든다.
5. 목표는 가능한 한 `metric_key`, `target_operator`, `target_value`로 구조화한다.
6. 새 라운드가 commit/recalculate되면 API 또는 Worker가 활성 목표를 owner scope로 조회한다.
7. 지원되는 metric은 라운드/홀/샷/metric 데이터에서 actual value를 계산해 `goal_evaluations`에 저장한다.
8. 자동 계산이 불가능하면 `not_evaluable`로 남기고 수동 평가 UI를 제공한다.
9. 평가 결과는 Dashboard, Goals, Ask context에서 “연습 -> 다음 라운드 결과” 근거로 사용한다.

### 5.5 Sharing

1. 사용자가 라운드 또는 분석 스냅샷의 visibility를 변경한다.
2. private이면 owner만 조회 가능하다.
3. link-only이면 `shares.token` 기반 URL로 조회 가능하다.
4. public profile/feed 노출은 post-MVP에서 추가한다.
5. 공개 응답 serializer는 동반자명, 비공개 메모, 원본 파일, 정확한 티타임을 제거한다.

### 5.6 Ask Question

1. 사용자가 Ask 화면에서 질문한다.
2. API가 질문을 저장하고 user_id를 확인한다.
3. Query planner가 질문에서 기간, 라운드, 골프장, 클럽, 샷 유형 필터를 추출한다.
4. API가 정형 SQL 조회로 핵심 수치와 후보 라운드/샷을 가져온다.
5. API가 수치, 근거, 권한 필터 정보를 answer context로 구성한다.
6. MVP는 deterministic template으로 답변한다.
7. Ollama가 설정된 경우 wording 보조로 `/api/chat`을 호출할 수 있다.
8. Post-MVP에서는 pgvector owner_id scope 검색과 citation framework를 추가한다.
9. 응답과 evidence를 저장하고 Web app에 반환한다.

## 6. Data Ownership & Authorization

- 모든 private resource는 `owner_id` 또는 `user_id`를 가진다.
- API endpoint는 현재 사용자와 resource owner를 비교한다.
- 공유 조회는 visibility와 token을 통해 별도 serializer를 사용한다.
- admin은 운영 목적 조회만 가능하며, 감사 로그를 남긴다.
- Ask/RAG 검색은 반드시 user_id 또는 share scope를 먼저 적용한 뒤 수행한다.
- public feed에 노출되는 데이터는 public serializer를 통과해야 한다.

## 7. API Design Principles

- `/api/v1` prefix를 둔다.
- JSON response는 일관된 envelope를 사용한다.
- 리스트 endpoint는 cursor pagination을 기본으로 한다.
- 필터는 명시적 query parameter로 제공한다.
- 에러 포맷:

```json
{
  "error": {
    "code": "round_not_found",
    "message": "Round not found",
    "details": {}
  }
}
```

- 분석 결과는 가능하면 precomputed table에서 읽는다.
- 비용이 큰 재계산은 동기 요청에서 수행하지 않는다.

## 8. Background Jobs

- `parse_upload_file`
- `commit_upload_review`
- `recalculate_round_metrics`
- `recalculate_user_expected_table`
- `recalculate_shot_values`
- `generate_insights`
- `dedupe_insights`
- `evaluate_round_goals`
- `generate_round_summary`
- `embed_document`
- `refresh_public_feed_item`

Job requirements:

- job id와 상태를 저장한다.
- 동일 라운드에 대한 중복 job은 coalesce한다.
- 실패 시 retry count와 error message를 저장한다.
- 분석 job은 idempotent하게 작성한다.

## 9. LLM Architecture

### 9.1 Context Sources

- Structured:
  - rounds
  - holes
  - shots
  - round_metrics
  - shot_values
- insights
- practice_plans
- practice_diary_entries
- round_goals
- goal_evaluations
- Unstructured:
  - uploaded original text
  - round notes
  - generated round summaries
  - insight explanations
  - user-visible recommendation text

### 9.2 Prompt Contract

- 시스템 프롬프트는 GolfRaiders 분석 도우미 역할을 명시한다.
- 답변은 사용자의 실제 데이터와 제공된 context에만 근거한다.
- 샘플 수가 작으면 불확실성을 표시한다.
- 사용자의 권한 밖 데이터는 존재 여부도 언급하지 않는다.
- 가능한 경우 라운드 수, 샷 수, 기간, 핵심 지표를 포함한다.
- 스윙 교정, 부상, 의료 조언은 일반적 안내 수준으로 제한한다.

### 9.3 Citation Format

LLM 응답은 내부적으로 다음 citation 구조를 가진다.

```json
{
  "citations": [
    {
      "type": "round",
      "id": "round_uuid",
      "label": "2026-04-10 Sky72",
      "metric": "driver_penalty_rate"
    }
  ]
}
```

## 10. Frontend Routing Proposal

- `/`: logged-out entry or logged-in dashboard redirect.
- `/dashboard`: personal dashboard.
- `/rounds`: round list.
- `/rounds/[id]`: round detail.
- `/upload`: upload entry.
- `/upload/[id]/review`: upload review.
- `/analysis`: analysis workspace.
- `/practice`: practice plans and diary.
- `/goals`: next-round goals and evaluations.
- `/ask`: Ask GolfRaiders.
- `/profile/[handle]`: post-MVP public profile.
- `/feed`: post-MVP public/following feed.
- `/s/[token]`: shared resource.
- `/settings`: post-MVP account and privacy settings.
- `/admin/uploads/errors`: MVP admin upload error console.

## 11. Deployment Topology

### 11.1 Local Development

```text
docker compose:
  web
  api
  worker
  postgres
  redis
  ollama
```

### 11.2 Production Minimum

- Reverse proxy terminates TLS.
- Web and API run as separate processes.
- Worker runs separately from API.
- PostgreSQL has automated backup.
- Redis is used for queue/cache only, not source of truth.
- Ollama can run on the same host initially but should be independently restartable.

## 12. Observability

- API request logs with request_id.
- Worker job logs with job_id and resource_id.
- LLM call logs with model, latency, token counts if available, timeout/error status.
- Upload parse warnings and failure reasons.
- Analysis recalculation duration.
- Public share access counts.

## 13. Security

- Passwords are hashed with a modern password hashing algorithm.
- Auth cookies are secure, httpOnly, SameSite=Lax or Strict.
- File uploads are size-limited and stored outside public static directories.
- Original upload files are private by default.
- Public serializers remove sensitive fields.
- Admin routes require explicit admin role.
- Secrets are provided through environment variables.
- Production `SECRET_KEY`, DB password, Ollama host, and OAuth secrets are never committed.

## 14. Migration Strategy

- Keep v1 repository stable while v2 is built separately.
- Extract analytics core from v1 into a reusable package.
- Write MySQL-to-PostgreSQL migration scripts.
- Import raw repo-root `data/<year>` files as an independent validation path.
- Compare v1 and v2 outputs for representative rounds:
  - score
  - GIR
  - putts
  - penalty strokes
  - shot category
  - expected_before/after
  - shot_value
  - recommendation priority
- Differences must be explained or fixed before production cutover.

## 15. Open Decisions

- FastAPI session cookie vs JWT access/refresh token.
- RQ vs Celery vs Arq for background jobs.
- Whether to store original upload files in local filesystem, S3-compatible object storage, or PostgreSQL large object.
- Supported MVP Ask question set.
- Initial optional Ollama chat model.
- Initial post-MVP embedding model and pgvector dimension.
