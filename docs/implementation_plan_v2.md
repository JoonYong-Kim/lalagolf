# GolfRaiders v2 Implementation Plan

## 1. Purpose

This document turns the v2 PRD, architecture, data model, API proposal, migration plan, and MVP plan into an executable development checklist.

Use this file as the day-to-day tracker. Mark checkboxes as work is completed, and keep implementation decisions in the "Decision Log" section.

## 2. Current Baseline

- [x] v1 code moved under `v1/`.
- [x] v2 planning documents created under `docs/`.
- [x] v2 project root created under `v2/`.
- [x] v2 `README.md` created.
- [x] v2 `AGENTS.md` created.
- [x] v2 web app initialized.
- [x] v2 API app initialized.
- [x] v2 worker initialized.
- [x] v2 Docker Compose created.

## 3. Implementation Principles

- Build vertically whenever possible: database, API, and UI should connect early.
- Keep v1 read-mostly. Use it as a reference, fixture source, and migration source.
- Do not implement social features before private ownership and link-only sharing are correct.
- Do not let LLM answers bypass permission checks or replace deterministic analytics.
- Every milestone must include ownership/privacy tests where user data is involved.
- Mobile layouts are part of MVP, not polish after MVP.
- Confirm the UI direction before building core screens. Dashboard, Round Detail, and Analysis need low-fidelity wireframes or clickable mocks approved before implementation starts.
- Keep MVP Ask deterministic first: structured retrieval and answer templates are required; embeddings/RAG are post-MVP.

## 4. Milestone Overview

| Phase | Name | Primary Outcome | Status |
| --- | --- | --- | --- |
| P0 | Project Foundation | v2 runs locally with web/api/db/worker skeleton | Scaffolded; Docker runtime unverified |
| P1 | Auth & Data Foundation | users, sessions, base schema, ownership tests | Core complete; downgrade/reset unverified |
| P2 | Analytics Core | v1 parser/analytics migrated with regression tests | Core complete |
| P2.5 | Early Migration Import | import enough v1 data to validate UI with real rounds | Representative 2026 rounds imported locally |
| P2.6 | UI Review Gate | confirmed wireframes for core private screens | Confirmed |
| P3 | Upload Review | upload -> parse -> review -> commit flow | Complete |
| P4 | Rounds & Dashboard | core private app screens and APIs | Complete |
| P5 | Analysis & Insights | trend APIs, insight dedupe, analysis UI | Complete |
| P6 | Entry & Sharing | minimal logged-out entry and link-only sharing | Complete |
| P7 | Ask GolfRaiders | structured-data Q&A with optional Ollama wording | Complete |
| P8 | Migration Dry Run | v1 import and diff report | Complete |
| P9 | Hardening | QA, security, mobile, production readiness | Complete |

## 5. P0. Project Foundation

Goal: create a runnable v2 development environment.

### P0.1 Repository Structure

- [x] Confirm `v2/` layout:
  - [x] `v2/web`
  - [x] `v2/api`
  - [x] `v2/worker`
  - [x] `v2/packages/analytics_core`
  - [x] `v2/infra`
  - [x] `v2/scripts`
- [x] Add root-level note or README pointer if needed.
- [x] Keep v1 and v2 commands clearly separated.

### P0.2 Frontend Bootstrap

- [x] Initialize Next.js App Router project in `v2/web`.
- [x] Configure TypeScript.
- [x] Configure Tailwind CSS.
- [x] Add base component structure.
- [x] Add logged-out entry placeholder.
- [x] Add dashboard placeholder.
- [x] Add API client placeholder.
- [x] Add formatting/linting scripts.

Acceptance:

- [x] `web` dev server starts.
- [x] `/` renders logged-out entry placeholder.
- [x] `/dashboard` renders authenticated placeholder or redirect placeholder.
- [x] TypeScript check passes.

### P0.3 API Bootstrap

- [x] Initialize FastAPI project in `v2/api`.
- [x] Add app factory or main app entrypoint.
- [x] Add `/health`.
- [x] Add `/api/v1/health`.
- [x] Add settings module reading environment variables.
- [x] Add database connection placeholder.
- [x] Add test setup.

Acceptance:

- [x] API server starts.
- [x] `/health` returns ok.
- [x] Unit test for health endpoint passes.

### P0.4 Worker Bootstrap

- [x] Choose initial worker framework: RQ.
- [x] Add worker entrypoint.
- [x] Add sample no-op job.
- [ ] Add job status storage strategy.

Acceptance:

- [x] Worker process starts.
- [ ] Sample job can be enqueued and completed locally.

### P0.5 Infrastructure

- [x] Add `v2/infra/docker-compose.yml`.
- [x] Add PostgreSQL service.
- [x] Add Redis service.
- [x] Add optional Ollama service or documented external Ollama host.
- [x] Add web service.
- [x] Add api service.
- [x] Add worker service.
- [x] Add `.env.example`.

Acceptance:

- [ ] `docker compose` starts core dependencies.
- [x] API can connect to PostgreSQL.
- [ ] API or worker can connect to Redis.
- [x] Ollama unavailability does not break API health.

Verification:

```bash
cd v2
docker compose -f infra/docker-compose.yml up
```

## 6. P1. Auth & Data Foundation

Goal: establish multi-user identity and PostgreSQL schema.

### P1.1 Database Setup

- [x] Add SQLAlchemy 2.x.
- [x] Add Alembic.
- [ ] Enable PostgreSQL extensions:
  - [x] `citext`
- [ ] Defer `vector` extension until post-MVP RAG work unless needed by an approved spike.
- [x] Add base model conventions.
- [x] Add timestamp mixins.
- [x] Add UUID primary key convention.

### P1.2 Initial Tables

- [x] `users`
- [x] `user_profiles`
- [x] session or refresh token table, if needed.
- [x] `source_files`
- [x] `upload_reviews`
- [x] `courses`
- [x] `rounds`
- [x] `round_companions`
- [x] `holes`
- [x] `shots`

Acceptance:

- [x] Alembic can upgrade a clean database.
- [ ] Alembic can downgrade or reset in local development.
- [x] Basic model relationships work in tests.

### P1.3 Auth API

- [x] `POST /api/v1/auth/register`
- [x] `POST /api/v1/auth/login`
- [x] `POST /api/v1/auth/logout`
- [x] `GET /api/v1/me`
- [x] `PATCH /api/v1/me/profile`
- [x] Password hashing.
- [x] Secure cookie or token implementation.

Acceptance:

- [x] User can register.
- [x] User can login.
- [x] User can logout.
- [x] Invalid credentials fail safely.
- [x] Current user endpoint returns profile.

### P1.4 Ownership Guardrails

- [x] Add auth dependency.
- [x] Add owner-scoped query helpers.
- [x] Add tests proving user A cannot read user B resources.
- [x] Add private-by-default constants.

Acceptance:

- [x] Private API without auth returns unauthorized.
- [x] Cross-user access returns forbidden or not found.
- [x] New user-owned rows get correct `user_id`.

## 7. P2. Analytics Core

Goal: migrate v1 parser and deterministic analytics into framework-independent package.

### P2.1 Package Structure

- [x] Add Python package under `v2/packages/analytics_core`.
- [x] Add package metadata.
- [x] Add test layout.
- [x] Add fixtures copied or referenced from `v1/tests/data`.

### P2.2 Parser Migration

- [x] Port `v1/src/data_parser.py`.
- [x] Keep parser independent from DB/API.
- [x] Normalize parser output for upload review.
- [x] Return warnings with stable codes and paths.

Acceptance:

- [x] v1 parser fixture tests pass in v2.
- [x] Robust sample files parse.
- [x] Unparsed lines produce warnings.
- [x] 27-hole sample behavior is covered.

### P2.3 Metrics Migration

- [x] Port metrics logic.
- [x] Port shot model logic.
- [x] Port expected value logic.
- [x] Port strokes gained logic.
- [x] Port recommendation logic.
- [x] Add insight dedupe v1 module with deterministic keys.
- [x] Add expected value cold-start fallback policy.

Acceptance:

- [x] score, GIR, putts, penalty metrics match v1 fixtures.
- [x] shot categories match expected tests.
- [x] expected value and shot_value tests pass.
- [x] insights follow problem/evidence/impact/next_action/confidence shape.
- [x] min-sample fallback behavior is covered: user table, global/baseline fallback, lookup-level confidence.

### P2.4 Analytics API Boundary

- [x] Define input dataclasses or typed dicts.
- [x] Define output schemas.
- [x] Add conversion functions from API/plain models to analytics input.
- [x] Add conversion functions from analytics output to persistence rows.

Acceptance:

- [x] Analytics core imports no FastAPI modules.
- [x] Analytics core imports no SQLAlchemy modules.
- [x] API can call analytics through a small service layer.

## 7.5 P2.5 Early Migration Import

Goal: load enough real v1 data early so product and UI decisions are checked against actual rounds.

### P2.5.1 Import Spike

- [x] Create selected owner user fixture.
- [x] Add minimal raw-file import script for representative v1 files.
- [x] Map imported rounds, holes, shots to the v2 schema or import fixture format.
- [x] Default all imported data to private.
- [x] Run analytics core over imported rounds.

Acceptance:

- [x] At least recent representative rounds can be imported before P3/P4 UI work.
- [x] Imported total score, hole count, and shot count can be spot-checked.
- [x] Imported data has owner scope and never appears in public/shared serializers by default.
- [x] P4/P5 screens can be developed against real data instead of empty mock-only states.

## 7.6 P2.6 UI Review Gate

Goal: confirm the intended UI improvement before implementing core app screens.

### P2.6.1 Wireframe Package

- [x] Create low-fidelity Dashboard wireframe.
- [x] Create low-fidelity Round Detail wireframe.
- [x] Create low-fidelity Analysis wireframe.
- [x] Include desktop and mobile variants for each.
- [x] Use real imported data examples where possible.
- [x] Show how cards are limited and where tables/charts/tabs/panels carry the main information.
- [x] Document empty/loading/error states at a rough layout level.

### P2.6.2 Confirmation Criteria

- [x] User confirms information hierarchy: what appears first, what is drill-down, and what is hidden by default.
- [x] User confirms insight unit shape and dashboard max-3 behavior.
- [x] User confirms mobile navigation and dense table/chart handling.
- [x] Confirmed decisions are recorded in `docs/ui_review_v2.md`.

Acceptance:

- [x] P4 Dashboard/Rounds/Round Detail UI work does not start until relevant wireframes are confirmed.
- [x] P5 Analysis UI work does not start until Analysis wireframe is confirmed.
- [ ] Any major UI direction change after confirmation updates `docs/ui_review_v2.md` before implementation continues.

## 8. P3. Upload Review Flow

Goal: upload a v1-style round file, review parsed data, and commit it.

### P3.1 Upload Storage

- [x] Decide local filesystem vs object storage for MVP.
- [x] Add file size limit.
- [x] Store files outside public static paths.
- [x] Store `source_files` row.
- [x] Compute content hash.

### P3.2 Parse Job

- [x] Implement `parse_upload_file` job.
- [x] Save `upload_reviews.parsed_round`.
- [x] Save warnings.
- [x] Mark status: uploaded, parsed, needs_review, failed.

Note: MVP currently runs parse synchronously inside the upload request and exposes the review id as `job_id`. RQ-backed async execution can replace this without changing the API response shape.

### P3.3 Upload API

- [x] `POST /api/v1/uploads/round-file`
- [x] `GET /api/v1/uploads/{upload_review_id}/review`
- [x] `PATCH /api/v1/uploads/{upload_review_id}/review`
- [x] `POST /api/v1/uploads/{upload_review_id}/commit`
- [x] `GET /api/v1/jobs/{job_id}`

Acceptance:

- [x] User uploads a file and receives review id.
- [x] Review endpoint is owner-scoped.
- [x] User edits are saved.
- [x] Commit creates round, holes, shots in one transaction.
- [x] Commit queues analytics recalculation.

Note: Commit currently marks the round `computed_status = pending`; the worker-side recalculation queue will consume this in P5.

### P3.4 Upload Review UI

- [x] Upload page.
- [x] Review page.
- [x] Warning list.
- [x] Editable round metadata.
- [x] Editable hole/shot rows.
- [x] Mobile-first correction flow.
- [x] Commit confirmation.

Acceptance:

- [x] User can complete upload from browser.
- [x] Mobile screen prioritizes warnings and required edits.
- [x] User sees total holes, total score, warning count before commit.

## 9. P4. Rounds & Dashboard

Goal: provide core private app experience.

Prerequisite: P2.6 Dashboard and Round Detail wireframes are confirmed.

### P4.1 Round APIs

- [x] `GET /api/v1/rounds`
- [x] `GET /api/v1/rounds/{round_id}`
- [x] `PATCH /api/v1/rounds/{round_id}`
- [x] `DELETE /api/v1/rounds/{round_id}`
- [x] `POST /api/v1/rounds/{round_id}/recalculate`
- [x] `GET /api/v1/rounds/{round_id}/holes`
- [x] `GET /api/v1/rounds/{round_id}/shots`
- [x] `PATCH /api/v1/holes/{hole_id}`
- [x] `PATCH /api/v1/shots/{shot_id}`

Acceptance:

- [x] Round list supports pagination.
- [x] Round list supports year/course/companion filters.
- [x] Round detail includes holes, shots, metrics, insights.
- [x] Updates mark analytics stale.

### P4.2 Dashboard API

- [x] `GET /api/v1/analytics/summary`
- [x] Recent rounds block.
- [x] KPI block.
- [x] Score trend block.
- [x] Priority insights block.

### P4.3 App UI

- [x] Authenticated layout.
- [x] Sidebar navigation for desktop.
- [x] Mobile bottom navigation.
- [x] Dashboard page.
- [x] Rounds page.
- [x] Round detail page.
- [x] Scorecard component.
- [x] Shot timeline component.

Acceptance:

- [x] Dashboard loads for logged-in user.
- [x] Round detail shows scorecard and selected-hole shot timeline.
- [x] Mobile layout has no incoherent overlap or horizontal overflow except intentional tables.

## 10. P5. Analysis & Insights

Goal: show useful analysis without duplicated comments.

Prerequisite: P2.6 Analysis wireframe is confirmed.

### P5.1 Analytics Persistence

- [x] `round_metrics`
- [x] `expected_score_tables`
- [x] `shot_values`
- [x] `insights`
- [x] `analysis_snapshots`

### P5.2 Recalculation Jobs

- [x] `recalculate_round_metrics`
- [x] `recalculate_user_expected_table`
- [x] `recalculate_shot_values`
- [x] `generate_insights`
- [x] `dedupe_insights`
- [x] `docs/insight_dedupe_v2.md` examples and deterministic rules.

Acceptance:

- [x] Jobs are idempotent.
- [x] Re-running jobs does not duplicate active insights.
- [x] Failed jobs store error details.
- [x] Dedupe behavior is explainable from the documented key/priority rules.

### P5.3 Analysis APIs

- [x] `GET /api/v1/analytics/trends`
- [x] `GET /api/v1/analytics/rounds/{round_id}`
- [x] `GET /api/v1/analytics/compare` for shot-value group summaries by category or club
- [x] `GET /api/v1/insights`
- [x] `PATCH /api/v1/insights/{insight_id}`

### P5.4 Analysis UI

- [x] Filter bar.
- [x] Mobile filter sheet.
- [x] Score tab.
- [x] Separate `/rounds/compare` page for selected-round scorecard metric comparison.
- [x] Tee tab.
- [x] Approach tab.
- [x] Short Game tab.
- [x] Putting tab.
- [x] Insight unit component.
- [x] Confidence/sample count display.

Acceptance:

- [x] Dashboard defaults to max 3 priority insights.
- [x] Insight unit includes problem, evidence, impact, next action, confidence.
- [x] Same evidence does not appear as multiple duplicate recommendations.

## 11. P6. Entry & Sharing

Goal: support a minimal logged-out first impression and safe link-only sharing.

### P6.1 Logged-out Entry

- [x] Minimal `/` page for logged-out users.
- [x] Login/register CTA.
- [x] Private-first explanation.
- [x] Redirect logged-in `/` visitors to dashboard.

Acceptance:

- [x] Logged-out `/` shows service identity and clear auth entry points.
- [x] Logged-out page does not imply public feed/profile support in MVP.
- [x] Logged-in `/` goes to the private dashboard.

### P6.2 Link Sharing

- [x] `shares` table.
- [x] Opaque token generation.
- [x] `POST /api/v1/shares`
- [x] `GET /api/v1/shares`
- [x] `PATCH /api/v1/shares/{share_id}`
- [x] `GET /api/v1/shared/{token}`
- [x] `/s/[token]` page.

Acceptance:

- [x] Shared page works logged out.
- [x] Revoked token stops working.
- [x] Public-safe serializer hides companion names, private notes, source files, storage keys, and private LLM messages.

## 12. P7. Ask GolfRaiders

Goal: answer user questions using owned structured data. Embeddings are post-MVP.

### P7.1 Ask Foundation

- [x] Supported question inventory.
- [x] Deterministic answer templates.
- [x] Optional Ollama settings.
- [x] Optional Ollama chat adapter.
- [x] Timeout/error handling.
- [x] Model availability check if Ollama is enabled.

### P7.2 Chat Persistence

- [x] `llm_threads`
- [x] `llm_messages`
- [x] Defer `embedding_documents` until post-MVP RAG.
- [x] Defer `embeddings` until post-MVP RAG.

### P7.3 Retrieval

- [x] Query planner for simple filters:
  - [x] window
  - [x] date range
  - [x] course
  - [x] club
  - [x] shot category
- [x] Structured SQL context retrieval.
- [x] Owner-scoped retrieval tests.
- [x] No pgvector retrieval in MVP.

### P7.4 Chat APIs

- [x] `POST /api/v1/chat/threads`
- [x] `GET /api/v1/chat/threads`
- [x] `GET /api/v1/chat/threads/{thread_id}`
- [x] `POST /api/v1/chat/threads/{thread_id}/messages`

### P7.5 Ask UI

- [x] Chat page.
- [x] Evidence panel.
- [x] Mobile evidence sheet.
- [x] Empty state suggestions.
- [x] LLM unavailable state.

Acceptance:

- [x] User can ask about their own recent rounds.
- [x] Answer includes round count, shot count, and applied filters when available.
- [x] Cross-user data cannot appear in retrieval context.
- [x] Supported questions work without Ollama.
- [x] Ollama failure does not break non-LLM pages or deterministic Ask answers.

## 13. P8. Migration Dry Run

Goal: prove v1 data can be imported and validated.

### P8.1 Migration Utilities

- [x] `scripts/migration/export_v1_mysql.py`
- [x] `scripts/migration/import_v2_postgres.py`
- [x] `scripts/migration/import_raw_files.py`
- [x] `scripts/migration/recalculate_analytics.py`
- [x] `scripts/migration/compare_v1_v2.py`
- [x] `scripts/migration/report_migration.py`

### P8.2 Migration Tables

- [x] `migration_runs`
- [x] `migration_id_map`
- [x] `migration_issues`

### P8.3 Validation

- [x] Schema inventory report.
- [x] Row count report.
- [x] Data quality issue report.
- [x] v1/v2 metric diff report.
- [x] Raw file parse comparison.

Acceptance:

- [x] Imported rounds default to private.
- [x] All imported rows have owner.
- [x] Recent 20 rounds match v1 total score exactly.
- [x] Skipped rows have issue records.
- [x] Diff report is generated as JSON and Markdown.

## 14. P9. Hardening & Release Readiness

Goal: make MVP safe to use.

### P9.1 Quality

- [x] Backend test suite.
- [x] Analytics regression suite.
- [x] Frontend smoke tests.
- [x] Mobile viewport checks.
- [x] API error-state tests.
- [x] Loading/empty/error UI states.

### P9.2 Security

- [x] Cookie/token security reviewed.
- [x] Password hashing reviewed.
- [x] File upload size/type checks.
- [x] Public-safe serializer tests.
- [x] Link token entropy reviewed.
- [x] Admin routes protected.
- [x] Secrets absent from repo.

### P9.3 Operations

- [x] `.env.example` complete.
- [x] Backup/restore notes.
- [x] Production environment checklist.
- [x] Logging with request id/job id.
- [x] LLM timeout/error logs.
- [x] Basic admin upload error page.

Acceptance:

- [x] Core mobile pages meet Lighthouse accessibility/performance target where practical.
- [x] MVP release criteria in `docs/mvp_plan_v2.md` are satisfied.
- [x] No known private-data exposure path remains open.

## 15. Cross-Phase Test Matrix

| Area | Required Tests |
| --- | --- |
| Auth | register, login, logout, current user, invalid credentials |
| Ownership | user A cannot read/update/delete user B data |
| Upload | file limit, parse success, parse warning, commit transaction |
| Analytics | v1 fixture regression, expected value, shot value, insight dedupe |
| Sharing | token read, revoke, public-safe serialization |
| Ask | owner-scoped retrieval, deterministic templates, unavailable Ollama, evidence formatting |
| Migration | row counts, skipped issues, v1/v2 metric diff |
| Frontend | entry page, dashboard, upload review, round detail, analysis, ask |
| Mobile | no broken overlap, usable nav, upload review correction flow |

## 16. Suggested First Sprint

Target: finish P0 and start P1.

- [x] Initialize `v2/web` with Next.js, TypeScript, Tailwind.
- [x] Initialize `v2/api` with FastAPI, pytest, settings, health endpoint.
- [x] Choose worker framework.
- [x] Add Docker Compose with PostgreSQL and Redis.
- [x] Add `.env.example`.
- [x] Add Alembic skeleton.
- [x] Add first database connection test.
- [x] Draft `docs/ui_review_v2.md` skeleton.
- [x] Update `v2/README.md` with actual commands.

Exit criteria:

- [ ] One command starts dependencies.
- [x] One command starts API.
- [x] One command starts web.
- [x] Health checks pass.
- [x] README commands are accurate.

## 17. Decision Log

Record decisions here as they are made.

| Date | Decision | Reason | Owner |
| --- | --- | --- | --- |
| 2026-04-28 | Use `v2/` inside the current repository for new development | Keeps v1 available as migration source while isolating v2 implementation | TBD |
| 2026-04-28 | Use PostgreSQL for v2 | Better fit for analytics, JSONB, and future pgvector-backed RAG | TBD |
| 2026-05-02 | Keep MVP Ask structured-first and defer embeddings/RAG | Reduces MVP scope while preserving owner-scoped natural-language access to metrics | TBD |
| 2026-05-02 | Require UI confirmation before building core private screens | Ensures Dashboard/Round Detail/Analysis improvements are visible and agreed before implementation | TBD |
| 2026-05-02 | Use RQ for MVP background jobs | Fits synchronous parser/analytics jobs and keeps worker operations simple | TBD |
| 2026-05-02 | Use secure server-managed sessions for MVP auth | Keeps browser token handling simple and aligns with private-first web app usage | TBD |

## 18. Open Decisions

- [ ] Uploaded file storage: local filesystem vs S3-compatible object storage.
- [ ] Initial supported Ask question set.
- [ ] Whether manual round creation is MVP.
- [ ] Whether to use a monorepo task runner after web/api initialization.
