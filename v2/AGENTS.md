# Repository Guidelines for LalaGolf v2

## Scope

These instructions apply to work under `v2/`. The legacy application lives under `../v1` and should be treated as reference and migration source unless a task explicitly asks to modify it.

## Project Structure

Use this layout:

- `web/`: Next.js App Router frontend.
- `api/`: FastAPI backend.
- `worker/`: background jobs for parsing, analytics recalculation, summaries, and embeddings.
- `packages/analytics_core/`: framework-independent Python parser and analytics package migrated from v1.
- `infra/`: Docker Compose, database, deployment, and local infrastructure files.
- `scripts/`: development, migration, and verification helper scripts.

Repository-level planning documents are in `../docs/` and should guide implementation:

- `../docs/prd_v2.md`
- `../docs/architecture_v2.md`
- `../docs/data_model_v2.md`
- `../docs/api_v2.md`
- `../docs/migration_v2.md`
- `../docs/mvp_plan_v2.md`

## Architecture Rules

- Keep frontend, API, worker, and analytics core separated.
- Keep route handlers thin; business logic belongs in service modules.
- Keep analytics core independent from FastAPI, SQLAlchemy, Next.js, Redis, and Ollama.
- All private data access must be scoped by the authenticated user's `user_id` or `owner_id`.
- Public and link-only views must use explicit public-safe serializers.
- Long-running work such as parsing, analytics recalculation, embedding generation, and LLM-heavy processing belongs in background jobs.

## Backend Guidelines

- Use Python with 4-space indentation.
- Prefer FastAPI dependency injection for auth/session/database dependencies.
- Use SQLAlchemy 2.x style models and queries.
- Use Alembic for schema changes.
- Use Pydantic models for request and response schemas.
- Keep API response formats consistent with `../docs/api_v2.md`.
- Do not return raw ORM objects from endpoints.
- Do not compute expensive analytics synchronously in request handlers unless explicitly scoped as a small admin/debug action.

## Frontend Guidelines

- Use TypeScript.
- Use Next.js App Router conventions.
- Prefer server components for initial data loading and public pages.
- Use client components for charts, filters, upload review editing, and chat interactions.
- Use Tailwind CSS and reusable components.
- Keep the UI dense, calm, and data-focused. Avoid marketing-style layouts for logged-in screens.
- Mobile core flows must be usable: Dashboard, Round Detail, Upload Review, Analysis, and Ask.

## Data & Privacy Rules

- Default imported and uploaded rounds to `private`.
- Never expose companion names, private notes, original upload files, storage keys, or private LLM messages through public/shared endpoints.
- Link-only pages require a valid opaque token.
- Admin access to user data should be explicit and auditable.
- LLM retrieval must apply ownership or share scope before vector or text search.

## Analytics Rules

- Migrate v1 parser and analytics behavior with regression tests.
- Preserve raw user-entered and uploaded data separately from computed metrics.
- Recompute derived metrics instead of copying stale computed values where possible.
- Insight output should follow the v2 unit shape: problem, evidence, impact, next action, confidence.
- Surface sample count and confidence when expected values or shot values are based on limited data.

## Testing Guidelines

Add tests proportional to the change:

- Backend: auth, ownership, API validation, upload commit, analytics, sharing serializers, LLM retrieval scope.
- Analytics core: parser regression, metrics, shot model, expected value, shot value, recommendations.
- Frontend: smoke tests for public home, login, dashboard, upload review, round detail, analysis, ask, and shared pages.
- Migration: dry-run import and v1/v2 diff report tests.

Before considering a feature complete, run the relevant backend/frontend tests and any type/lint commands available in the initialized project.

## Migration Guidelines

- v1 MySQL data and repo-root `../data/<year>` files are migration sources.
- Maintain a source-to-target id mapping for imports.
- Record skipped or suspicious rows as migration issues.
- Imported data must default to private.
- Compare v1 and v2 outputs for score, GIR, putts, penalty strokes, shot category, expected values, shot values, and recommendation category.

## Security & Configuration

- Use `.env.example` for documented environment variables only.
- Never commit real secrets, database passwords, OAuth secrets, API keys, production cookies, or local credential files.
- File uploads must be size-limited and stored outside public static paths.
- Production secrets must come from environment variables or a secret manager.

## Commit Guidance

- Keep commits focused.
- Separate structural moves, scaffolding, and feature implementation into different commits.
- Prefer short, clear commit titles.
- Include screenshots for meaningful UI changes when opening PRs.
