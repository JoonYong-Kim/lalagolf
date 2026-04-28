# LalaGolf v2 MVP Plan

## 1. MVP Objective

LalaGolf v2 MVP는 단일 사용자 중심 v1을 멀티 유저 분석 서비스로 재구성하는 첫 번째 릴리스다. MVP의 목표는 사용자가 계정을 만들고, 라운드 파일을 업로드하고, 파싱 결과를 검토한 뒤, 개인 대시보드/라운드 상세/분석 화면에서 신뢰 가능한 인사이트를 확인하고, 선택적으로 링크 공유와 Ollama 기반 질의를 사용할 수 있게 하는 것이다.

## 2. MVP Scope

### Must Have

- Next.js + FastAPI + PostgreSQL 기반 새 프로젝트 스캐폴딩.
- 계정 생성, 로그인, 로그아웃, 현재 사용자 조회.
- PostgreSQL schema와 Alembic migration.
- v1 파서/분석 로직의 analytics core 이관.
- 라운드 텍스트 파일 업로드.
- 파싱 리뷰 화면.
- 라운드 저장 및 사용자별 데이터 격리.
- Dashboard, Rounds, Round Detail, Analysis 기본 화면.
- 모바일 반응형 Dashboard, Round Detail, Upload Review, Ask 화면.
- 중복 정리된 insight unit.
- link-only 공유.
- 로그인 전 Public Home과 샘플 분석 프리뷰.
- Ollama 기반 Ask LalaGolf 1차 버전.
- v1 데이터 migration dry-run 및 diff report.

### Should Have

- public profile의 기본 구조.
- public round 목록.
- embedding 기반 RAG 검색.
- 관리자용 업로드 오류 확인 화면.
- Lighthouse 접근성/성능 점수 90 이상을 목표로 한 모바일 검증.

### Not in MVP

- 댓글, 좋아요, 팔로우.
- followers visibility.
- 코치/그룹 기능.
- 네이티브 모바일 앱.
- 복잡한 public feed ranking.
- 실시간 알림.
- 외부 상용 LLM 연동.

## 3. Milestones

## M0. Project Bootstrap

Goal: v2 프로젝트를 개발 가능한 상태로 만든다.

Deliverables:

- 새 repository 또는 새 project root.
- `web` Next.js app.
- `api` FastAPI app.
- `worker` process skeleton.
- Docker Compose: web, api, worker, postgres, redis, ollama.
- `.env.example`.
- v2 전용 `README.md`.
- v2 전용 `AGENTS.md`는 새 repository 생성 시 작성한다.

Acceptance Criteria:

- `docker compose up`으로 기본 서비스가 뜬다.
- Web app이 health page 또는 public home placeholder를 표시한다.
- API가 `/health`를 반환한다.
- PostgreSQL과 Redis 연결 확인이 가능하다.
- 개발자가 README만 보고 로컬 실행할 수 있다.

## M1. Database & Auth Foundation

Goal: 멀티 유저 데이터 격리 기반을 만든다.

Deliverables:

- Alembic setup.
- users, user_profiles, sessions 또는 refresh token 관련 테이블.
- source_files, upload_reviews 기본 테이블.
- rounds, holes, shots 기본 테이블.
- auth endpoints:
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/me`
- frontend login/register screens.

Acceptance Criteria:

- 사용자가 가입/로그인/로그아웃할 수 있다.
- 인증되지 않은 사용자는 private API에 접근할 수 없다.
- 사용자 A는 사용자 B의 round를 조회할 수 없다.
- auth cookie 또는 token이 안전한 방식으로 저장된다.
- 기본 테스트가 user ownership을 검증한다.

## M2. Analytics Core Extraction

Goal: v1 분석 로직을 v2 backend에서 독립적으로 호출 가능하게 만든다.

Deliverables:

- analytics core package.
- parser module.
- metrics module.
- shot model module.
- expected value module.
- strokes gained module.
- recommendations/insights module.
- v1 fixture 기반 regression tests.

Acceptance Criteria:

- v1 sample files를 v2 parser가 파싱한다.
- score, GIR, putts, penalty strokes가 v1 테스트 기대값과 일치한다.
- shot category와 shot_value 계산이 기존 테스트 기준을 통과한다.
- analytics core는 FastAPI나 DB에 의존하지 않는다.
- low sample confidence 처리가 가능하다.

## M3. Upload Review Flow

Goal: 사용자가 라운드 파일을 올리고 저장 전 검토할 수 있다.

Deliverables:

- `POST /api/v1/uploads/round-file`.
- parse upload background job.
- `GET /api/v1/uploads/{id}/review`.
- `PATCH /api/v1/uploads/{id}/review`.
- `POST /api/v1/uploads/{id}/commit`.
- Upload Review UI.
- 모바일 Upload Review UI.

Acceptance Criteria:

- 텍스트 라운드 파일 업로드 후 review 화면이 표시된다.
- 파싱 경고가 path와 함께 표시된다.
- 사용자가 클럽, 날짜, 골프장, 홀/샷 오류를 수정할 수 있다.
- commit 시 rounds, holes, shots가 트랜잭션으로 저장된다.
- 저장된 데이터는 현재 사용자에게만 귀속된다.
- commit 후 analytics job이 queue에 등록된다.

## M4. Round & Dashboard MVP

Goal: 저장된 라운드를 조회하고 핵심 요약을 볼 수 있다.

Deliverables:

- `GET /api/v1/rounds`.
- `GET /api/v1/rounds/{id}`.
- `PATCH /api/v1/rounds/{id}`.
- `DELETE /api/v1/rounds/{id}` soft delete.
- `GET /api/v1/analytics/summary`.
- Dashboard UI.
- Rounds list UI.
- Round Detail UI.
- 모바일 Dashboard/Round Detail.

Acceptance Criteria:

- 로그인 후 `/dashboard`에서 최근 라운드와 KPI를 볼 수 있다.
- `/rounds`에서 필터 가능한 라운드 목록을 볼 수 있다.
- `/rounds/{id}`에서 스코어카드와 샷 타임라인을 볼 수 있다.
- 모바일에서 Dashboard와 Round Detail이 overflow 없이 사용 가능하다.
- 라운드 수정 시 analytics status가 stale 또는 recalculation 대상이 된다.

## M5. Analysis & Insight Deduplication

Goal: 중복된 추천과 코멘트를 정리한 분석 화면을 제공한다.

Deliverables:

- `GET /api/v1/analytics/trends`.
- `GET /api/v1/analytics/rounds/{id}`.
- `GET /api/v1/insights`.
- `PATCH /api/v1/insights/{id}`.
- insight dedupe logic.
- Analysis UI with tabs:
  - Score
  - Tee
  - Approach
  - Short Game
  - Putting
- Insight unit component.

Acceptance Criteria:

- 동일한 원인에서 나온 코멘트가 여러 카드로 반복 표시되지 않는다.
- Dashboard에는 우선순위 insight가 최대 3개만 기본 노출된다.
- 각 insight는 문제, 근거 수치, 영향, 다음 행동을 가진다.
- 샘플 수가 부족한 insight는 confidence가 낮게 표시된다.
- 사용자가 insight를 dismiss할 수 있다.
- 모바일 Analysis는 필터 sheet와 탭 구조로 사용할 수 있다.

## M6. Public Home & Link Sharing

Goal: 로그인 전 경험과 안전한 공유 기능을 제공한다.

Deliverables:

- Public Home.
- sample analysis data.
- `GET /api/v1/public/home`.
- `GET /api/v1/sample-analysis`.
- `POST /api/v1/shares`.
- `GET /api/v1/shares`.
- `PATCH /api/v1/shares/{id}`.
- `GET /api/v1/shared/{token}`.
- shared round page `/s/[token]`.

Acceptance Criteria:

- 로그인 전 `/`에서 public home이 표시된다.
- 첫 viewport에서 서비스명, CTA, 샘플 분석 일부가 보인다.
- 사용자는 private round를 link-only로 공유할 수 있다.
- link-only 페이지는 token 없이는 접근할 수 없다.
- 공유 화면에 동반자명, private note, original upload file이 노출되지 않는다.
- 공유를 revoke하면 기존 링크가 더 이상 동작하지 않는다.

## M7. Ask LalaGolf MVP

Goal: 사용자가 자신의 라운드 기록에 자연어로 질문할 수 있다.

Deliverables:

- Ollama adapter.
- `POST /api/v1/chat/threads`.
- `GET /api/v1/chat/threads`.
- `GET /api/v1/chat/threads/{id}`.
- `POST /api/v1/chat/threads/{id}/messages`.
- query planner 1차 버전.
- structured SQL context retrieval.
- optional embedding document generation.
- Ask UI.
- mobile Ask UI.

Acceptance Criteria:

- 사용자는 자신의 데이터에 대해 질문하고 답변을 받을 수 있다.
- 응답에는 기간, 라운드 수, 샷 수 등 근거가 포함된다.
- 다른 사용자의 데이터는 검색되지 않는다.
- Ollama 장애 시 사용자는 명확한 오류 메시지를 받는다.
- 답변은 원본 수치 계산을 대체하지 않고 분석 보조 설명으로 표시된다.
- 모바일에서 채팅 입력과 근거 보기 sheet가 동작한다.

## M8. Migration Dry Run

Goal: v1 데이터를 v2로 이전할 수 있음을 검증한다.

Deliverables:

- v1 schema inventory script.
- MySQL export script.
- PostgreSQL import script.
- raw file import validation script.
- analytics recalculation script.
- v1/v2 diff report script.

Acceptance Criteria:

- valid v1 rounds가 v2 owner user로 import된다.
- 모든 imported rounds는 private이다.
- recent 20 rounds의 total score가 v1과 일치한다.
- 주요 지표 diff report가 생성된다.
- skipped rows는 migration issue로 기록된다.
- import는 dry-run과 실제 실행 모드를 구분한다.

## M9. MVP Hardening

Goal: 실제 사용 가능한 품질로 다듬는다.

Deliverables:

- API error handling 정리.
- loading/empty/error UI.
- mobile viewport QA.
- basic admin upload error page.
- backup/restore guide.
- production env checklist.
- security review checklist.

Acceptance Criteria:

- 주요 API endpoint에 테스트가 있다.
- 주요 화면에 loading/empty/error state가 있다.
- 모바일 핵심 화면 Lighthouse 접근성/성능 점수가 90 이상이다.
- private/public serializer 테스트가 있다.
- 업로드 실패와 LLM 실패가 UI에서 복구 가능하게 표시된다.
- production 환경변수 목록이 문서화되어 있다.

## 4. Suggested Build Order

1. M0 Project Bootstrap
2. M1 Database & Auth Foundation
3. M2 Analytics Core Extraction
4. M3 Upload Review Flow
5. M4 Round & Dashboard MVP
6. M5 Analysis & Insight Deduplication
7. M6 Public Home & Link Sharing
8. M7 Ask LalaGolf MVP
9. M8 Migration Dry Run
10. M9 MVP Hardening

Note: M8 migration scripts can start earlier after M1 schema stabilizes, but final diff validation should happen after M2/M5 analytics behavior is stable.

## 5. MVP Release Criteria

- A new user can register, upload a round file, review parsed data, commit it, and see analysis.
- A returning user can view dashboard, round detail, analysis tabs, and priority insights.
- A user can create and revoke a link-only share.
- A logged-out visitor can see public home and sample analysis.
- Ask LalaGolf can answer at least structured-data questions for the current user.
- Imported v1 data can be dry-run migrated and compared.
- Private data is not exposed through public/shared endpoints.
- Mobile core flows are usable on common phone widths.

## 6. Test Plan

Backend:

- auth tests.
- ownership/authorization tests.
- parser regression tests.
- analytics regression tests.
- upload review commit tests.
- sharing serializer tests.
- LLM retrieval scope tests.
- migration dry-run tests.

Frontend:

- smoke tests for public home, login, dashboard, upload review, round detail, analysis, ask.
- mobile viewport tests.
- empty/loading/error state tests.
- share page privacy tests.

Manual QA:

- upload representative v1 files.
- compare v1/v2 metrics.
- check public shared link in logged-out browser.
- ask questions with and without enough data.
- revoke share link and retry.

## 7. MVP Risks

- v1 parser assumptions may not cleanly map to editable upload review.
- expected score and shot_value may differ after data model normalization.
- Ollama latency and Korean answer quality may vary by local model and hardware.
- PostgreSQL/pgvector setup adds operational complexity compared with v1 MySQL.
- Mobile tables and charts can become hard to use if data density is not managed early.
- Public sharing can leak private context if serializers are not tested explicitly.

## 8. Open Decisions Before Implementation

- New repository name and directory structure.
- Auth approach: cookie session vs JWT.
- Worker choice: RQ, Celery, or Arq.
- Initial Ollama chat model and embedding model.
- Whether manual round creation is included in MVP.
- Whether public profile ships with MVP or only link-only sharing.
- Object storage choice for uploaded files.
