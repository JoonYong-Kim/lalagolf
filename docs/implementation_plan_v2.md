# LalaGolf v2 Implementation Plan

## 1. Purpose

This document turns the v2 PRD, architecture, data model, API proposal, migration plan, and MVP plan into an executable development checklist.

Use this file as the day-to-day tracker. Mark checkboxes as work is completed, and keep implementation decisions in the "Decision Log" section.

## 2. Current Baseline

- [x] v1 code moved under `v1/`.
- [x] v2 planning documents created under `docs/`.
- [x] v2 project root created under `v2/`.
- [x] v2 `README.md` created.
- [x] v2 `AGENTS.md` created.
- [ ] v2 web app initialized.
- [ ] v2 API app initialized.
- [ ] v2 worker initialized.
- [ ] v2 Docker Compose created.

## 3. Implementation Principles

- Build vertically whenever possible: database, API, and UI should connect early.
- Keep v1 read-mostly. Use it as a reference, fixture source, and migration source.
- Do not implement social features before private ownership and link-only sharing are correct.
- Do not let LLM answers bypass permission checks or replace deterministic analytics.
- Every milestone must include ownership/privacy tests where user data is involved.
- Mobile layouts are part of MVP, not polish after MVP.

## 4. Milestone Overview

| Phase | Name | Primary Outcome | Status |
| --- | --- | --- | --- |
| P0 | Project Foundation | v2 runs locally with web/api/db/worker skeleton | Not started |
| P1 | Auth & Data Foundation | users, sessions, base schema, ownership tests | Not started |
| P2 | Analytics Core | v1 parser/analytics migrated with regression tests | Not started |
| P3 | Upload Review | upload -> parse -> review -> commit flow | Not started |
| P4 | Rounds & Dashboard | core private app screens and APIs | Not started |
| P5 | Analysis & Insights | trend APIs, insight dedupe, analysis UI | Not started |
| P6 | Public Home & Sharing | logged-out home and link-only sharing | Not started |
| P7 | Ask LalaGolf | Ollama-backed structured-data Q&A | Not started |
| P8 | Migration Dry Run | v1 import and diff report | Not started |
| P9 | Hardening | QA, security, mobile, production readiness | Not started |

## 5. P0. Project Foundation

Goal: create a runnable v2 development environment.

### P0.1 Repository Structure

- [ ] Confirm `v2/` layout:
  - [ ] `v2/web`
  - [ ] `v2/api`
  - [ ] `v2/worker`
  - [ ] `v2/packages/analytics_core`
  - [ ] `v2/infra`
  - [ ] `v2/scripts`
- [ ] Add root-level note or README pointer if needed.
- [ ] Keep v1 and v2 commands clearly separated.

### P0.2 Frontend Bootstrap

- [ ] Initialize Next.js App Router project in `v2/web`.
- [ ] Configure TypeScript.
- [ ] Configure Tailwind CSS.
- [ ] Add base component structure.
- [ ] Add public home placeholder.
- [ ] Add dashboard placeholder.
- [ ] Add API client placeholder.
- [ ] Add formatting/linting scripts.

Acceptance:

- [ ] `web` dev server starts.
- [ ] `/` renders public placeholder.
- [ ] `/dashboard` renders authenticated placeholder or redirect placeholder.
- [ ] TypeScript check passes.

### P0.3 API Bootstrap

- [ ] Initialize FastAPI project in `v2/api`.
- [ ] Add app factory or main app entrypoint.
- [ ] Add `/health`.
- [ ] Add `/api/v1/health`.
- [ ] Add settings module reading environment variables.
- [ ] Add database connection placeholder.
- [ ] Add test setup.

Acceptance:

- [ ] API server starts.
- [ ] `/health` returns ok.
- [ ] Unit test for health endpoint passes.

### P0.4 Worker Bootstrap

- [ ] Choose initial worker framework: RQ, Arq, or Celery.
- [ ] Add worker entrypoint.
- [ ] Add sample no-op job.
- [ ] Add job status storage strategy.

Acceptance:

- [ ] Worker process starts.
- [ ] Sample job can be enqueued and completed locally.

### P0.5 Infrastructure

- [ ] Add `v2/infra/docker-compose.yml`.
- [ ] Add PostgreSQL service.
- [ ] Add Redis service.
- [ ] Add Ollama service or documented external Ollama host.
- [ ] Add web service.
- [ ] Add api service.
- [ ] Add worker service.
- [ ] Add `.env.example`.

Acceptance:

- [ ] `docker compose` starts core dependencies.
- [ ] API can connect to PostgreSQL.
- [ ] API or worker can connect to Redis.
- [ ] Ollama unavailability does not break API health.

Verification:

```bash
cd v2
docker compose -f infra/docker-compose.yml up
```

## 6. P1. Auth & Data Foundation

Goal: establish multi-user identity and PostgreSQL schema.

### P1.1 Database Setup

- [ ] Add SQLAlchemy 2.x.
- [ ] Add Alembic.
- [ ] Enable PostgreSQL extensions:
  - [ ] `citext`
  - [ ] `vector`
- [ ] Add base model conventions.
- [ ] Add timestamp mixins.
- [ ] Add UUID primary key convention.

### P1.2 Initial Tables

- [ ] `users`
- [ ] `user_profiles`
- [ ] session or refresh token table, if needed.
- [ ] `source_files`
- [ ] `upload_reviews`
- [ ] `courses`
- [ ] `rounds`
- [ ] `round_companions`
- [ ] `holes`
- [ ] `shots`

Acceptance:

- [ ] Alembic can upgrade a clean database.
- [ ] Alembic can downgrade or reset in local development.
- [ ] Basic model relationships work in tests.

### P1.3 Auth API

- [ ] `POST /api/v1/auth/register`
- [ ] `POST /api/v1/auth/login`
- [ ] `POST /api/v1/auth/logout`
- [ ] `GET /api/v1/me`
- [ ] `PATCH /api/v1/me/profile`
- [ ] Password hashing.
- [ ] Secure cookie or token implementation.

Acceptance:

- [ ] User can register.
- [ ] User can login.
- [ ] User can logout.
- [ ] Invalid credentials fail safely.
- [ ] Current user endpoint returns profile.

### P1.4 Ownership Guardrails

- [ ] Add auth dependency.
- [ ] Add owner-scoped query helpers.
- [ ] Add tests proving user A cannot read user B resources.
- [ ] Add private-by-default constants.

Acceptance:

- [ ] Private API without auth returns unauthorized.
- [ ] Cross-user access returns forbidden or not found.
- [ ] New user-owned rows get correct `user_id`.

## 7. P2. Analytics Core

Goal: migrate v1 parser and deterministic analytics into framework-independent package.

### P2.1 Package Structure

- [ ] Add Python package under `v2/packages/analytics_core`.
- [ ] Add package metadata.
- [ ] Add test layout.
- [ ] Add fixtures copied or referenced from `v1/tests/data`.

### P2.2 Parser Migration

- [ ] Port `v1/src/data_parser.py`.
- [ ] Keep parser independent from DB/API.
- [ ] Normalize parser output for upload review.
- [ ] Return warnings with stable codes and paths.

Acceptance:

- [ ] v1 parser fixture tests pass in v2.
- [ ] Robust sample files parse.
- [ ] Unparsed lines produce warnings.
- [ ] 27-hole sample behavior is covered.

### P2.3 Metrics Migration

- [ ] Port metrics logic.
- [ ] Port shot model logic.
- [ ] Port expected value logic.
- [ ] Port strokes gained logic.
- [ ] Port recommendation logic.
- [ ] Add insight dedupe module.

Acceptance:

- [ ] score, GIR, putts, penalty metrics match v1 fixtures.
- [ ] shot categories match expected tests.
- [ ] expected value and shot_value tests pass.
- [ ] insights follow problem/evidence/impact/next_action/confidence shape.

### P2.4 Analytics API Boundary

- [ ] Define input dataclasses or typed dicts.
- [ ] Define output schemas.
- [ ] Add conversion functions from DB models to analytics input.
- [ ] Add conversion functions from analytics output to persistence rows.

Acceptance:

- [ ] Analytics core imports no FastAPI modules.
- [ ] Analytics core imports no SQLAlchemy modules.
- [ ] API can call analytics through a small service layer.

## 8. P3. Upload Review Flow

Goal: upload a v1-style round file, review parsed data, and commit it.

### P3.1 Upload Storage

- [ ] Decide local filesystem vs object storage for MVP.
- [ ] Add file size limit.
- [ ] Store files outside public static paths.
- [ ] Store `source_files` row.
- [ ] Compute content hash.

### P3.2 Parse Job

- [ ] Implement `parse_upload_file` job.
- [ ] Save `upload_reviews.parsed_round`.
- [ ] Save warnings.
- [ ] Mark status: uploaded, parsed, needs_review, failed.

### P3.3 Upload API

- [ ] `POST /api/v1/uploads/round-file`
- [ ] `GET /api/v1/uploads/{upload_review_id}/review`
- [ ] `PATCH /api/v1/uploads/{upload_review_id}/review`
- [ ] `POST /api/v1/uploads/{upload_review_id}/commit`
- [ ] `GET /api/v1/jobs/{job_id}`

Acceptance:

- [ ] User uploads a file and receives review id.
- [ ] Review endpoint is owner-scoped.
- [ ] User edits are saved.
- [ ] Commit creates round, holes, shots in one transaction.
- [ ] Commit queues analytics recalculation.

### P3.4 Upload Review UI

- [ ] Upload page.
- [ ] Review page.
- [ ] Warning list.
- [ ] Editable round metadata.
- [ ] Editable hole/shot rows.
- [ ] Mobile-first correction flow.
- [ ] Commit confirmation.

Acceptance:

- [ ] User can complete upload from browser.
- [ ] Mobile screen prioritizes warnings and required edits.
- [ ] User sees total holes, total score, warning count before commit.

## 9. P4. Rounds & Dashboard

Goal: provide core private app experience.

### P4.1 Round APIs

- [ ] `GET /api/v1/rounds`
- [ ] `GET /api/v1/rounds/{round_id}`
- [ ] `PATCH /api/v1/rounds/{round_id}`
- [ ] `DELETE /api/v1/rounds/{round_id}`
- [ ] `POST /api/v1/rounds/{round_id}/recalculate`
- [ ] `GET /api/v1/rounds/{round_id}/holes`
- [ ] `GET /api/v1/rounds/{round_id}/shots`
- [ ] `PATCH /api/v1/holes/{hole_id}`
- [ ] `PATCH /api/v1/shots/{shot_id}`

Acceptance:

- [ ] Round list supports pagination.
- [ ] Round list supports year/course/companion filters.
- [ ] Round detail includes holes, shots, metrics, insights.
- [ ] Updates mark analytics stale.

### P4.2 Dashboard API

- [ ] `GET /api/v1/analytics/summary`
- [ ] Recent rounds block.
- [ ] KPI block.
- [ ] Score trend block.
- [ ] Priority insights block.

### P4.3 App UI

- [ ] Authenticated layout.
- [ ] Sidebar navigation for desktop.
- [ ] Mobile bottom navigation.
- [ ] Dashboard page.
- [ ] Rounds page.
- [ ] Round detail page.
- [ ] Scorecard component.
- [ ] Shot timeline component.

Acceptance:

- [ ] Dashboard loads for logged-in user.
- [ ] Round detail shows scorecard and selected-hole shot timeline.
- [ ] Mobile layout has no incoherent overlap or horizontal overflow except intentional tables.

## 10. P5. Analysis & Insights

Goal: show useful analysis without duplicated comments.

### P5.1 Analytics Persistence

- [ ] `round_metrics`
- [ ] `expected_score_tables`
- [ ] `shot_values`
- [ ] `insights`
- [ ] `analysis_snapshots`

### P5.2 Recalculation Jobs

- [ ] `recalculate_round_metrics`
- [ ] `recalculate_user_expected_table`
- [ ] `recalculate_shot_values`
- [ ] `generate_insights`
- [ ] `dedupe_insights`

Acceptance:

- [ ] Jobs are idempotent.
- [ ] Re-running jobs does not duplicate active insights.
- [ ] Failed jobs store error details.

### P5.3 Analysis APIs

- [ ] `GET /api/v1/analytics/trends`
- [ ] `GET /api/v1/analytics/rounds/{round_id}`
- [ ] `GET /api/v1/analytics/compare`
- [ ] `GET /api/v1/insights`
- [ ] `PATCH /api/v1/insights/{insight_id}`

### P5.4 Analysis UI

- [ ] Filter bar.
- [ ] Mobile filter sheet.
- [ ] Score tab.
- [ ] Tee tab.
- [ ] Approach tab.
- [ ] Short Game tab.
- [ ] Putting tab.
- [ ] Insight unit component.
- [ ] Confidence/sample count display.

Acceptance:

- [ ] Dashboard defaults to max 3 priority insights.
- [ ] Insight unit includes problem, evidence, impact, next action, confidence.
- [ ] Same evidence does not appear as multiple duplicate recommendations.

## 11. P6. Public Home & Sharing

Goal: support logged-out first impression and safe link-only sharing.

### P6.1 Public Home

- [ ] `GET /api/v1/public/home`
- [ ] `GET /api/v1/sample-analysis`
- [ ] `GET /api/v1/public/rounds`
- [ ] Public home page.
- [ ] Sample dashboard preview.
- [ ] Mobile public home.

Acceptance:

- [ ] Logged-out `/` shows service identity, CTA, sample analysis preview.
- [ ] Hero does not consume the whole mobile viewport.
- [ ] Sample data is clearly not private user data.

### P6.2 Link Sharing

- [ ] `shares` table.
- [ ] Opaque token generation.
- [ ] `POST /api/v1/shares`
- [ ] `GET /api/v1/shares`
- [ ] `PATCH /api/v1/shares/{share_id}`
- [ ] `GET /api/v1/shared/{token}`
- [ ] `/s/[token]` page.

Acceptance:

- [ ] Shared page works logged out.
- [ ] Revoked token stops working.
- [ ] Public-safe serializer hides companion names, private notes, source files, storage keys, and private LLM messages.

## 12. P7. Ask LalaGolf

Goal: answer user questions using owned structured data and, later, embeddings.

### P7.1 LLM Foundation

- [ ] Ollama settings.
- [ ] Ollama chat adapter.
- [ ] Ollama embed adapter.
- [ ] Timeout/error handling.
- [ ] Model availability check.

### P7.2 Chat Persistence

- [ ] `llm_threads`
- [ ] `llm_messages`
- [ ] `embedding_documents`
- [ ] `embeddings`

### P7.3 Retrieval

- [ ] Query planner for simple filters:
  - [ ] window
  - [ ] date range
  - [ ] course
  - [ ] club
  - [ ] shot category
- [ ] Structured SQL context retrieval.
- [ ] Owner-scoped retrieval tests.
- [ ] Optional pgvector retrieval.

### P7.4 Chat APIs

- [ ] `POST /api/v1/chat/threads`
- [ ] `GET /api/v1/chat/threads`
- [ ] `GET /api/v1/chat/threads/{thread_id}`
- [ ] `POST /api/v1/chat/threads/{thread_id}/messages`

### P7.5 Ask UI

- [ ] Chat page.
- [ ] Evidence panel.
- [ ] Mobile evidence sheet.
- [ ] Empty state suggestions.
- [ ] LLM unavailable state.

Acceptance:

- [ ] User can ask about their own recent rounds.
- [ ] Answer includes round count, shot count, and applied filters when available.
- [ ] Cross-user data cannot appear in retrieval context.
- [ ] Ollama failure does not break non-LLM pages.

## 13. P8. Migration Dry Run

Goal: prove v1 data can be imported and validated.

### P8.1 Migration Utilities

- [ ] `scripts/migration/export_v1_mysql.py`
- [ ] `scripts/migration/import_v2_postgres.py`
- [ ] `scripts/migration/import_raw_files.py`
- [ ] `scripts/migration/recalculate_analytics.py`
- [ ] `scripts/migration/compare_v1_v2.py`
- [ ] `scripts/migration/report_migration.py`

### P8.2 Migration Tables

- [ ] `migration_runs`
- [ ] `migration_id_map`
- [ ] `migration_issues`

### P8.3 Validation

- [ ] Schema inventory report.
- [ ] Row count report.
- [ ] Data quality issue report.
- [ ] v1/v2 metric diff report.
- [ ] Raw file parse comparison.

Acceptance:

- [ ] Imported rounds default to private.
- [ ] All imported rows have owner.
- [ ] Recent 20 rounds match v1 total score exactly.
- [ ] Skipped rows have issue records.
- [ ] Diff report is generated as JSON and Markdown.

## 14. P9. Hardening & Release Readiness

Goal: make MVP safe to use.

### P9.1 Quality

- [ ] Backend test suite.
- [ ] Analytics regression suite.
- [ ] Frontend smoke tests.
- [ ] Mobile viewport checks.
- [ ] API error-state tests.
- [ ] Loading/empty/error UI states.

### P9.2 Security

- [ ] Cookie/token security reviewed.
- [ ] Password hashing reviewed.
- [ ] File upload size/type checks.
- [ ] Public-safe serializer tests.
- [ ] Link token entropy reviewed.
- [ ] Admin routes protected.
- [ ] Secrets absent from repo.

### P9.3 Operations

- [ ] `.env.example` complete.
- [ ] Backup/restore notes.
- [ ] Production environment checklist.
- [ ] Logging with request id/job id.
- [ ] LLM timeout/error logs.
- [ ] Basic admin upload error page.

Acceptance:

- [ ] Core mobile pages meet Lighthouse accessibility/performance target where practical.
- [ ] MVP release criteria in `docs/mvp_plan_v2.md` are satisfied.
- [ ] No known private-data exposure path remains open.

## 15. Cross-Phase Test Matrix

| Area | Required Tests |
| --- | --- |
| Auth | register, login, logout, current user, invalid credentials |
| Ownership | user A cannot read/update/delete user B data |
| Upload | file limit, parse success, parse warning, commit transaction |
| Analytics | v1 fixture regression, expected value, shot value, insight dedupe |
| Sharing | token read, revoke, public-safe serialization |
| LLM | owner-scoped retrieval, unavailable Ollama, evidence formatting |
| Migration | row counts, skipped issues, v1/v2 metric diff |
| Frontend | public home, dashboard, upload review, round detail, analysis, ask |
| Mobile | no broken overlap, usable nav, upload review correction flow |

## 16. Suggested First Sprint

Target: finish P0 and start P1.

- [ ] Initialize `v2/web` with Next.js, TypeScript, Tailwind.
- [ ] Initialize `v2/api` with FastAPI, pytest, settings, health endpoint.
- [ ] Choose worker framework.
- [ ] Add Docker Compose with PostgreSQL and Redis.
- [ ] Add `.env.example`.
- [ ] Add Alembic skeleton.
- [ ] Add first database connection test.
- [ ] Update `v2/README.md` with actual commands.

Exit criteria:

- [ ] One command starts dependencies.
- [ ] One command starts API.
- [ ] One command starts web.
- [ ] Health checks pass.
- [ ] README commands are accurate.

## 17. Decision Log

Record decisions here as they are made.

| Date | Decision | Reason | Owner |
| --- | --- | --- | --- |
| 2026-04-28 | Use `v2/` inside the current repository for new development | Keeps v1 available as migration source while isolating v2 implementation | TBD |
| 2026-04-28 | Use PostgreSQL for v2 | Better fit for analytics, JSONB, and pgvector-backed RAG | TBD |

## 18. Open Decisions

- [ ] Auth mechanism: secure cookie session vs JWT access/refresh.
- [ ] Worker framework: RQ vs Arq vs Celery.
- [ ] Uploaded file storage: local filesystem vs S3-compatible object storage.
- [ ] Initial Ollama chat model.
- [ ] Initial Ollama embedding model and vector dimension.
- [ ] Whether manual round creation is MVP.
- [ ] Whether public profile ships in MVP or after MVP.
- [ ] Whether to use a monorepo task runner after web/api initialization.
