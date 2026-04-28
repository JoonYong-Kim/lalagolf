# LalaGolf v2

LalaGolf v2 is the next version of LalaGolf: a multi-user golf performance analysis service with modern web UI, PostgreSQL-backed analytics, safe sharing, and Ollama-powered question answering.

This directory is intentionally separate from `../v1`. The v1 app remains the reference implementation and migration source. New development should happen under `v2/`.

## Project Layout

```text
v2/
  web/                    # Next.js App Router frontend
  api/                    # FastAPI backend
  worker/                 # Background jobs for parsing, analytics, embeddings
  packages/
    analytics_core/       # Framework-independent parser and analytics logic
  infra/                  # Docker Compose, deployment, database infrastructure
  scripts/                # Developer and migration helper scripts
  README.md
  AGENTS.md
```

## Reference Documents

The v2 requirements and design documents live in the repository-level `docs/` directory:

- `../docs/prd_v2.md`
- `../docs/architecture_v2.md`
- `../docs/data_model_v2.md`
- `../docs/api_v2.md`
- `../docs/migration_v2.md`
- `../docs/mvp_plan_v2.md`
- `../docs/implementation_plan_v2.md`

Use these documents as the source of truth until implementation-specific docs are added inside `v2/`.

## Planned Stack

- Frontend: Next.js App Router, React 19, TypeScript
- UI: Tailwind CSS and shadcn/ui-style components
- Backend: FastAPI
- Database: PostgreSQL with pgvector
- Migrations: Alembic
- Worker: RQ, Arq, or Celery; final choice is still open
- Queue/cache: Redis
- LLM runtime: Ollama
- Local orchestration: Docker Compose

## MVP Build Order

1. Project bootstrap
2. Database and auth foundation
3. Analytics core extraction from v1
4. Upload review flow
5. Round list, round detail, and dashboard
6. Analysis and insight deduplication
7. Public home and link sharing
8. Ask LalaGolf with Ollama
9. v1 migration dry run
10. MVP hardening

See `../docs/mvp_plan_v2.md` for acceptance criteria.

## Development Notes

- Treat `../v1` as read-mostly reference code.
- Do not modify v1 while implementing v2 unless the change is explicitly about migration validation or a documented v1 bug fix.
- Keep analytics logic independent from FastAPI, SQLAlchemy, and Next.js.
- All user-owned data must be scoped by `user_id` or `owner_id`.
- New public or shared responses must use public-safe serializers.

## Status

This project is currently scaffold-only. The first implementation step is to initialize `web`, `api`, `worker`, and local infrastructure according to the architecture and MVP plan.
