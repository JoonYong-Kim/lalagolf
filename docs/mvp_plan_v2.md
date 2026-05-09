# GolfRaiders v2 MVP Plan

## 1. MVP Objective

GolfRaiders v2 MVP는 단일 사용자 중심 v1을 멀티 유저 분석 서비스로 재구성하는 첫 번째 릴리스다. MVP의 목표는 사용자가 계정을 만들고, 라운드 파일을 업로드하고, 파싱 결과를 검토한 뒤, 개인 대시보드/라운드 상세/분석 화면에서 신뢰 가능한 인사이트를 확인하고, 선택적으로 링크 공유와 구조화된 질의를 사용할 수 있게 하는 것이다.

MVP는 "SaaS 전체 기능"이 아니라 private-first 개인 골프 분석 앱이다. Public/social/RAG는 핵심 분석 경험이 검증된 뒤 v2.1 이후로 확장한다.

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
- 중복 정리된 insight unit의 1차 버전.
- 인사이트에서 만드는 연습 계획, 연습 다이어리, 다음 라운드 목표의 1차 버전.
- link-only 공유.
- 로그인 전 `/` placeholder 또는 간단한 제품 진입 화면.
- Ask GolfRaiders 1차 버전: 구조화된 SQL/metric retrieval과 템플릿 답변.
- v1 데이터 migration dry-run 및 diff report.
- Dashboard, Round Detail, Analysis 저충실도 UI 와이어프레임 작성 및 구현 전 사용자 확인.

### Should Have

- 관리자용 업로드 오류 확인 화면.
- Lighthouse 접근성/성능 점수 90 이상을 목표로 한 모바일 검증.
- Ollama adapter를 통한 답변 문장 다듬기. 단, deterministic metric retrieval이 기본 동작이어야 한다.
- 향후 논의용 백로그: 업로드 파일 상세도를 `Score only`, `Scorecard`, `Shot detail`로 나누고,
  데이터 상세도에 따라 활성 기능과 비활성 기능의 안내를 다르게 제공한다.

### Not in MVP

- 댓글, 좋아요, 팔로우.
- followers visibility.
- public profile.
- public round 목록.
- public feed.
- 업로드 상세도별 공식 파일 포맷과 단계별 기능 게이팅의 최종 구현.
- 코치/그룹 기능.
- 네이티브 모바일 앱.
- 복잡한 public feed ranking.
- 실시간 알림.
- 외부 상용 LLM 연동.
- embedding 기반 RAG 검색.
- pgvector index 및 embedding pipeline.
- Public social login providers other than the configured Google sign-in path.

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
- Web app이 health page 또는 logged-out entry placeholder를 표시한다.
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
- expected value cold-start fallback policy.
- v1 fixture 기반 regression tests.

Acceptance Criteria:

- v1 sample files를 v2 parser가 파싱한다.
- score, GIR, putts, penalty strokes가 v1 테스트 기대값과 일치한다.
- shot category와 shot_value 계산이 기존 테스트 기준을 통과한다.
- analytics core는 FastAPI나 DB에 의존하지 않는다.
- low sample confidence 처리가 가능하다.
- user sample이 부족할 때 global baseline 또는 configured baseline으로 fallback하는 규칙이 테스트된다.

## M2.5 Early Migration Import Spike

Goal: 실제 v1 데이터를 빠르게 v2 화면 검증에 사용할 수 있게 한다.

Deliverables:

- owner user를 지정해 v1 raw round files를 v2 normalized input으로 변환하는 최소 import script.
- recent rounds import smoke test.
- imported data를 analytics core에 통과시키는 recalculation smoke test.

Acceptance Criteria:

- 본인 v1 데이터 일부가 v2 DB 또는 fixture store에 private owner scope로 들어간다.
- M3~M5 UI는 빈 mock이 아니라 실제 라운드 데이터로 검증할 수 있다.
- import 결과의 total score, hole count, shot count가 spot-check 가능하다.

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
- 스코어카드는 동일 폭 홀 컬럼과 score outcome 배지로 par/birdie/bogey 등을 구분한다.
- 라운드 상세는 라운드 분석 요약을 스코어카드보다 먼저 보여주고, stroke-gained 양수/음수를
  green/red 계열로 구분한다.
- 라운드 상세 스코어카드 헤더는 `공유`, `수정`, `재계산` 액션을 제공한다. `수정`은 기존 업로드
  검토 화면으로 이동하며, raw 재파싱 후 다시 저장하면 기존 라운드를 갱신하고 재계산 대상으로 만든다.
- 모바일에서 Dashboard와 Round Detail이 overflow 없이 사용 가능하다.
- 라운드 수정 시 analytics status가 stale 또는 recalculation 대상이 된다.

## M5. Analysis & Insight Deduplication

Goal: 중복된 추천과 코멘트를 최소 규칙으로 정리한 분석 화면을 제공한다.

Deliverables:

- `GET /api/v1/analytics/trends`.
- `GET /api/v1/analytics/rounds/{id}`.
- `GET /api/v1/insights`.
- `PATCH /api/v1/insights/{id}`.
- insight dedupe v1 logic.
- `docs/insight_dedupe_v2.md` rules and examples.
- Analysis UI with tabs:
  - All
  - Tee
  - Short Game
  - Control Shot
  - Iron Shot
  - Putting
  - Recovery
  - Penalty
- Insight unit component.
- Locale-aware insight API rendering for Korean and English MVP templates.

Acceptance Criteria:

- 동일한 원인에서 나온 코멘트가 여러 카드로 반복 표시되지 않는다.
- Dashboard에는 우선순위 insight가 최대 3개만 기본 노출된다.
- Analysis는 현재 필터/탭의 deduplicated insight를 하나의 전환형 위젯에서 1개씩 표시한다.
- 선택 라운드 분석은 분석 페이지에서 기존 카테고리/인사이트 흐름으로 운영한다.
- 라운드 비교는 별도 `/rounds/compare` 페이지에서 제공한다. 2개 라운드는 head-to-head로,
  3개 이상은 날짜상 마지막/최근 라운드를 나머지 선택 라운드 평균과 비교한다.
- 비교 테이블은 스코어, 퍼트, 홀당 퍼트, 3퍼트 홀, GIR `홀 수 (비율)`, 페어웨이 안착률,
  페널티, 페널티 홀, 버디 이상, 파, 보기, 더블보기 이상을 표시한다. `파 대비`와 `총 파`는 제외한다.
- 각 insight는 문제, 근거 수치, 영향, 다음 행동을 가진다.
- 샘플 수가 부족한 insight는 confidence가 낮게 표시된다.
- 사용자가 insight를 dismiss할 수 있다.
- 사용자가 UI 언어를 영어로 바꾸면 지원되는 MVP insight 문구도 영어로 표시된다.
- 모바일 Analysis는 필터 sheet와 탭 구조로 사용할 수 있다.
- 고급 clustering, semantic similarity, LLM 기반 dedupe는 MVP 이후로 남긴다.

## M6. Entry Placeholder & Link Sharing

Goal: 로그인 전 최소 진입 화면과 안전한 link-only 공유 기능을 제공한다.

Deliverables:

- Logged-out entry placeholder.
- `POST /api/v1/shares`.
- `GET /api/v1/shares`.
- `PATCH /api/v1/shares/{id}`.
- `GET /api/v1/shared/{token}`.
- shared round page `/s/[token]`.

Acceptance Criteria:

- 로그인 전 `/`에서 제품명, 로그인/가입 CTA, private-first 설명이 표시된다.
- 사용자는 private round를 link-only로 공유할 수 있다.
- link-only 페이지는 token 없이는 접근할 수 없다.
- 공유 화면에 동반자명, private note, original upload file이 노출되지 않는다.
- 공유 스코어카드에는 해당 라운드에서 발견된 public-safe 최우선 이슈 1개가 함께 표시된다.
- 공유 스코어카드도 private 라운드 상세과 동일한 홀 폭과 score outcome 배지를 사용한다.
- 공유를 revoke하면 기존 링크가 더 이상 동작하지 않는다.
- public home, sample analysis, public round 목록은 v2.1 이후로 남긴다.

## M7. Practice Plans, Diary & Goals

Goal: 인사이트를 실제 연습 행동과 다음 라운드 검증으로 연결한다.

Deliverables:

- `POST /api/v1/practice/plans`.
- `GET /api/v1/practice/plans`.
- `PATCH /api/v1/practice/plans/{plan_id}`.
- `POST /api/v1/practice/diary`.
- `GET /api/v1/practice/diary`.
- `POST /api/v1/goals`.
- `GET /api/v1/goals`.
- `PATCH /api/v1/goals/{goal_id}`.
- `POST /api/v1/goals/{goal_id}/evaluate`.
- Insight card actions:
  - select practice plan.
  - select next-round goal.
- Practice page:
  - plan list.
  - calendar/diary toggle widget.
  - date-scoped diary entry form.
- Goals page:
  - active goals.
  - recent evaluations.
- first-pass system evaluator for supported metric keys:
  - `score_to_par`
  - `total_score`
  - `putts_total`
  - `three_putt_holes`
  - `penalties_total`
  - `tee_penalties`
  - `gir_count`

Acceptance Criteria:

- 사용자는 insight에서 연습 계획을 만들 수 있다.
- 사용자는 Analysis 인사이트 제안에서 `플랜 선택` 또는 `목표 선택`을 같은 레벨의 액션으로 실행할 수 있다.
- 사용자는 연습 후 발견한 내용을 private diary로 남길 수 있다.
- 사용자는 다음 라운드 목표를 측정 가능한 metric rule로 만들 수 있다.
- 라운드 commit 또는 recalculation 후 지원되는 목표는 자동 평가된다.
- 자동 평가가 불가능한 목표는 `not_evaluable`로 표시되고 수동 평가할 수 있다.
- 목표 평가는 다른 사용자의 라운드를 참조하지 않는다.
- Dashboard는 활성 연습 계획과 다음 라운드 목표를 요약 표시한다.
- Ask GolfRaiders는 practice diary와 goal evaluation을 소유자 scope 안에서 근거로 사용할 수 있다.

## M8. Ask GolfRaiders MVP

Goal: 사용자가 자신의 라운드 기록에 대해 구조화된 질문을 할 수 있다.

Deliverables:

- optional Ollama chat adapter.
- `POST /api/v1/chat/threads`.
- `GET /api/v1/chat/threads`.
- `GET /api/v1/chat/threads/{id}`.
- `POST /api/v1/chat/threads/{id}/messages`.
- query planner 1차 버전.
- structured SQL context retrieval.
- deterministic answer templates.
- Ask UI.
- mobile Ask UI.

Acceptance Criteria:

- 사용자는 자신의 데이터에 대해 질문하고 답변을 받을 수 있다.
- 응답에는 기간, 라운드 수, 샷 수 등 근거가 포함된다.
- 다른 사용자의 데이터는 검색되지 않는다.
- Ollama가 없어도 지원 질문은 템플릿 답변으로 동작한다.
- 답변은 원본 수치 계산을 대체하지 않고 분석 보조 설명으로 표시된다.
- 모바일에서 채팅 입력과 근거 보기 sheet가 동작한다.
- embedding/RAG/citation framework는 v2.1 이후로 남긴다.

## M9. Migration Dry Run

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

## M10. MVP Hardening

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
4. M2.5 Early Migration Import Spike
5. UI Review Gate: Dashboard, Round Detail, Analysis wireframes reviewed and confirmed
6. M3 Upload Review Flow
7. M4 Round & Dashboard MVP
8. M5 Analysis & Insight Deduplication
9. M6 Entry Placeholder & Link Sharing
10. M7 Practice Plans, Diary & Goals
11. M8 Ask GolfRaiders MVP
12. M9 Migration Dry Run
13. M10 MVP Hardening

Note: M9 final diff validation still happens after M2/M5 analytics behavior is stable, but import work starts earlier so M3~M5 can be checked with real user data.

## 5. MVP Release Criteria

- A new user can register, upload a round file, review parsed data, commit it, and see analysis.
- A returning user can view dashboard, round detail, analysis tabs, and priority insights.
- A user can create and revoke a link-only share.
- A logged-out visitor can reach a minimal private-first entry page.
- Ask GolfRaiders can answer at least structured-data questions for the current user.
- A user can convert an insight into a practice plan and next-round goal, then evaluate that goal
  against a later round.
- Imported v1 data can be dry-run migrated and compared.
- Private data is not exposed through public/shared endpoints.
- Mobile core flows are usable on common phone widths.
- Dashboard, Round Detail, and Analysis UI are implemented only after wireframes or clickable mockups are reviewed and confirmed.

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

- smoke tests for entry page, login, dashboard, upload review, round detail, analysis, ask.
- mobile viewport tests.
- empty/loading/error state tests.
- share page privacy tests.

Manual QA:

- upload representative v1 files.
- compare v1/v2 metrics.
- check link-only shared page in logged-out browser.
- ask questions with and without enough data.
- revoke share link and retry.

## 7. MVP Risks

- v1 parser assumptions may not cleanly map to editable upload review.
- expected score and shot_value may differ after data model normalization.
- Ask scope can expand too quickly if RAG is pulled back into MVP.
- Mobile tables and charts can become hard to use if data density is not managed early.
- Public sharing can leak private context if serializers are not tested explicitly.
- UI implementation can drift toward card-heavy pages unless wireframes are confirmed before feature development.

## 8. Open Decisions Before Implementation

- New repository name and directory structure.
- Auth approach: cookie session vs JWT.
- Worker choice: RQ, Celery, or Arq.
- Whether manual round creation is included in MVP.
- Object storage choice for uploaded files.
- Initial supported Ask question set.
