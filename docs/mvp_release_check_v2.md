# LalaGolf v2 MVP Release Check

Date: 2026-05-03

## Automated Verification

- API tests: `cd v2/api && .venv/bin/pytest -q` -> 52 passed.
- API lint: `cd v2/api && ruff check app tests` -> passed.
- Analytics regression: `cd v2/packages/analytics_core && PYTHONPATH=src ../../api/.venv/bin/pytest -q` -> 61 passed.
- Frontend typecheck: `cd v2/web && npm run typecheck` -> passed.
- Frontend build: `cd v2/web && npm run build` -> passed.
- Frontend smoke: `cd v2/web && npm run smoke` -> 10 routes checked.
- Mobile guardrails: `cd v2/web && npm run mobile-check` -> 9 core pages checked.
- Secret scan: `cd v2/web && npm run security-check` -> 163 files checked.

## MVP Release Criteria Mapping

| Criterion | Status | Evidence |
| --- | --- | --- |
| New user can register, upload, review, commit, and see analysis | Satisfied | `test_auth.py`, `test_uploads_api.py`, `test_rounds_api.py`, `test_analytics_api.py` |
| Returning user can view dashboard, round detail, analysis tabs, and priority insights | Satisfied | API tests plus `npm run smoke` routes for `/dashboard`, `/rounds/[id]`, `/analysis` |
| User can create and revoke link-only share with a top public-safe round issue | Satisfied | `test_shares_api.py` |
| Logged-out visitor can reach private-first entry page | Satisfied | `npm run smoke` route `/` |
| Ask can answer structured-data questions for current user | Satisfied | `test_chat_api.py`, `test_operations.py` |
| Imported v1 data can be dry-run migrated and compared | Satisfied | migration reports in `v2/migration_reports/`, `test_migration_service.py` |
| Private data is not exposed through public/shared endpoints | Satisfied | `test_shares_api.py`, `test_security_hardening.py` |
| Mobile core flows are usable on common phone widths | Satisfied within current tooling | `npm run mobile-check`; actual Lighthouse/browser scoring remains a manual follow-up |
| Dashboard, Round Detail, and Analysis were implemented after UI confirmation | Satisfied | `docs/ui_review_v2.md` |

## M9 Acceptance Mapping

| Acceptance | Status | Evidence |
| --- | --- | --- |
| Major API endpoints have tests | Satisfied | 52 API tests |
| Major screens have loading/empty/error states | Satisfied | Dashboard, Rounds, Round Detail, Analysis, Ask, Upload Review, Shared, Admin page implementations |
| Core mobile Lighthouse accessibility/performance target | Practical fallback complete | `mobile-check` source guardrails; Lighthouse requires browser tooling not currently installed |
| Private/public serializer tests exist | Satisfied | share/public serializer tests |
| Upload failure and LLM failure are recoverable in UI/logs | Satisfied | upload error UI states, admin upload error page, deterministic Ask fallback logs |
| Production env vars are documented | Satisfied | `v2/.env.example`, `docs/operations_v2.md` |

## Private Data Exposure Review

Known public/shared surfaces:

- `GET /api/v1/shared/{token}`
- `/s/[token]`
- logged-out `/`

The shared serializer returns only title, public-safe round summary, scorecard hole rows, aggregate
metrics, and at most one public-safe top issue for the shared round. Tests assert that companion
names, private notes, source file ids, storage keys, and LLM message tables are absent. All private
API routes require authenticated owner-scoped access; cross-user round, upload, analytics, chat,
and share management tests return 404 or 401/403 as appropriate.

No known private-data exposure path remains open after the current automated checks.

## Manual Follow-Up

- Run Lighthouse on mobile profiles once browser tooling is installed.
- Exercise upload/review/commit/share/revoke in a real browser against the local API.
- Restore a backup into a staging database before production launch.
