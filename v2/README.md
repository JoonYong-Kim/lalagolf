# LalaGolf v2

LalaGolf v2 is the next version of LalaGolf: a private-first multi-user golf performance analysis service with modern web UI, PostgreSQL-backed analytics, safe link sharing, and structured question answering.

This directory is intentionally separate from `../v1`. The v1 app remains the reference implementation and migration source. New development should happen under `v2/`.

## Project Layout

```text
v2/
  web/                    # Next.js App Router frontend
  api/                    # FastAPI backend
  worker/                 # Background jobs for parsing and analytics
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
- `../docs/operations_v2.md`
- `../docs/mvp_release_check_v2.md`
- `../docs/mvp_plan_v2.md`
- `../docs/implementation_plan_v2.md`

Use these documents as the source of truth until implementation-specific docs are added inside `v2/`.

## Planned Stack

- Frontend: Next.js App Router, React 19, TypeScript
- UI: Tailwind CSS and shadcn/ui-style components
- Backend: FastAPI
- Database: PostgreSQL
- Migrations: Alembic
- Worker: RQ
- Queue/cache: Redis
- Optional LLM runtime: Ollama for Ask wording support
- Local orchestration: Docker Compose

## MVP Build Order

1. Project bootstrap
2. Database and auth foundation
3. Analytics core extraction from v1
4. Early migration import spike
5. UI review gate for Dashboard, Round Detail, and Analysis
6. Upload review flow
7. Round list, round detail, and dashboard
8. Analysis and insight deduplication
9. Logged-out entry and link-only sharing
10. Ask LalaGolf structured retrieval
11. v1 migration dry run
12. MVP hardening

See `../docs/mvp_plan_v2.md` for acceptance criteria.

## Development Notes

- Treat `../v1` as read-mostly reference code.
- Do not modify v1 while implementing v2 unless the change is explicitly about migration validation or a documented v1 bug fix.
- Keep analytics logic independent from FastAPI, SQLAlchemy, and Next.js.
- All user-owned data must be scoped by `user_id` or `owner_id`.
- New public or shared responses must use public-safe serializers.

## P0 Local Commands

Start infrastructure dependencies:

```bash
cd v2
docker compose -f infra/docker-compose.yml up
```

Start the API:

```bash
cd v2/api
python -m venv .venv
. .venv/bin/activate
pip install -e ../packages/analytics_core
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Start the web app:

```bash
cd v2/web
npm install
npm run dev
```

Start the worker skeleton:

```bash
cd v2/worker
python -m venv .venv
. .venv/bin/activate
pip install -e .
WORKER_USE_RQ=true python -m app.main
```

Install v2 as systemd services:

```bash
cd v2
sudo bash scripts/install_systemd.sh
```

This installs three services:

- `lalagolf-v2-api.service`
- `lalagolf-v2-worker.service`
- `lalagolf-v2-web.service`

The installer writes `/etc/lalagolf-v2/lalagolf-v2.env`, installs application files under
`/opt/lalagolf-v2`, stores uploads under `/var/lib/lalagolf-v2/uploads`, builds the web app, and
runs Alembic migrations. Set `SKIP_DB_MIGRATION=true` when running the installer if PostgreSQL is
not ready yet.

Uninstall the systemd deployment:

```bash
cd v2
sudo bash scripts/uninstall_systemd.sh
```

Run API tests:

```bash
cd v2/api
. .venv/bin/activate
pytest -q
```

Run hardening checks:

```bash
cd v2/web
npm run mobile-check
npm run security-check
npm run smoke
```

Run database migrations once PostgreSQL is available:

```bash
cd v2/api
. .venv/bin/activate
alembic upgrade head
```

Import representative v1 raw rounds for local UI/data validation:

```bash
cd v2/api
. .venv/bin/activate
python ../scripts/import_v1_raw_files.py \
  ../../data/2026/파인힐스\ 2026-04-14.txt \
  ../../data/2026/베르힐영종\ 2026-04-11.txt \
  --commit
```

The default local import owner is `owner@example.com` with password `password`.

Operational notes for production environment variables, backups, restore, logs, and admin upload
errors are in `../docs/operations_v2.md`.

## Status

P0 through P2.5 are implemented at the core level. Docker runtime, Redis enqueue/complete flow, and Alembic downgrade/reset remain unverified locally.
