# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo Layout: v1 vs v2

This repository ships **two parallel trees** with very different statuses:

- `v1/` — the working Flask + MySQL app. This is the production reference and the migration source.
- `v2/` — the rewrite target (Next.js App Router + FastAPI + PostgreSQL/pgvector + Redis + Ollama). Currently **scaffold-only**: `web/`, `api/`, `worker/`, `packages/analytics_core/`, `infra/`, `scripts/` directories exist but are empty.
- `docs/` — repo-level planning documents for v2 (PRD, architecture, data model, API, migration, MVP plan, implementation plan).

**Default rule:** new development happens under `v2/`. Treat `v1/` as read-mostly reference. Only modify `v1/` when the task is explicitly migration validation, a documented v1 bug fix, or the user is clearly asking for v1 work. Each tree has its own `AGENTS.md` (`v1/AGENTS.md`, `v2/AGENTS.md`) — read the one matching the tree you are about to touch.

The active v2 todo tracker is `docs/implementation_plan_v2.md` (checkboxed milestones P0–P9).

## v1 — Flask App

### Common commands

All v1 commands run from `v1/` unless noted.

```bash
# setup
python -m venv .venv && source .venv/bin/activate
pip install -r v1/requirements.txt

# run web app (binds 0.0.0.0:2323)
cd v1 && python run_webapp.py

# bulk-load round text files into MySQL
cd v1 && python load_data.py

# tests
cd v1 && pytest -q
cd v1 && pytest tests/test_metrics.py -q                    # single file
cd v1 && pytest tests/test_metrics.py::test_name -q         # single test

# fast syntax check after edits to recommendations or routes
cd v1 && python -m py_compile src/recommendations.py src/webapp/routes.py

# systemd deploy / remove (writes to /opt/lalagolf, /etc/lalagolf)
sudo bash v1/scripts/install_systemd.sh
sudo bash v1/scripts/uninstall_systemd.sh
```

Config: `v1/conf/lalagolf.conf` (JSON) must contain `DB_CONFIG` and `WEBAPP_USERS`. Flask `SECRET_KEY` is read from env; if absent, a dev key is auto-generated.

### v1 data flow and module boundaries

The pipeline is rigid and worth respecting when editing:

```
data/<year>/*.txt
   → v1/src/data_parser.py     (parse_file / parse_content / analyze_shots_and_stats)
   → src/db_loader.py          (init_connection_pool, save_round_data, get_*)
   → src/shot_model.py         (normalize_shot_states)
   → src/expected_value.py     (expected score table, recency weights)
   → src/strokes_gained.py     (shot value, club/strategy comparisons)
   → src/metrics.py            (round + recent + trend summaries)
   → src/recommendations.py    (insight/priority cards, next-action, hybrid action)
   → src/webapp/routes.py      (thin glue) → templates/
```

Hard rules carried over from `v1/AGENTS.md` and `v1/shrimp-rules.md`:

- **All DB logic lives in `src/db_loader.py`.** Routes must not query the DB directly.
- **All parsing lives in `src/data_parser.py`.** Changing the parsed shape ripples into `db_loader.save_round_data` and the analytics modules — update tests in `tests/test_data_parser.py` together.
- **Analytics modules don't know about Flask.** Keep them callable from plain dicts/lists; this is what `v2/packages/analytics_core` will eventually import.
- `src/analytics_config.py` holds minimum-sample thresholds (e.g. `EXPECTED_SCORE_MIN_SAMPLES`, `APPROACH_STRATEGY_MIN_SAMPLES`). Tune confidence gates here, not inline.
- Connection pooling comes from `mysql-connector-python` via `init_connection_pool`; reuse it for any new DB call.

### Round file format

One round per file under repo-root `data/<year>/`. Lines are either hole headers (`1P4`, `2 P5`) or shots (`Club Feel Result [Landing] [Distance] [Penalty|OK]`). Valid clubs and tokens are enumerated in `v1/src/data_parser.py` (`VALID_CLUBS`, `DEFAULT_DISTANCES`) and `v1/README.md` — consult those before adjusting parsing.

## v2 — Planned Architecture

The v2 stack and rules (from `docs/architecture_v2.md` and `v2/AGENTS.md`) constrain implementation choices once code starts landing:

- **Layering:** `web/` (Next.js, TS, Tailwind) ↔ `api/` (FastAPI, SQLAlchemy 2.x, Alembic, Pydantic) ↔ `worker/` (RQ/Arq/Celery — choice still open) ↔ Postgres (+ pgvector) + Redis + Ollama. Frontend, API, worker, and analytics core stay separated.
- **`packages/analytics_core` must stay framework-independent.** No FastAPI, SQLAlchemy, Next.js, Redis, or Ollama imports. Inputs are explicit dicts/dataclasses; outputs are structured dicts. This is the migration target for v1's `data_parser` / `metrics` / `shot_model` / `expected_value` / `strokes_gained` / `recommendations` modules, plus a new `insight_dedupe`.
- **Ownership:** every private query is scoped by `user_id` / `owner_id`. Default new rounds to `private`. Public and link-only views use **explicit public-safe serializers** — never return raw ORM objects, and never expose companion names, private notes, original upload files, storage keys, or LLM messages on shared endpoints.
- **Background-only work:** parsing, analytics recompute, expected/shot-value table refresh, insight generation, summary generation, and embedding generation run in the worker, not request handlers.
- **Insight shape:** `{ problem, evidence, impact, next_action, confidence }`. Surface sample count and confidence whenever expected values or shot values come from limited data.
- **LLM (Ask LalaGolf):** retrieval applies ownership/share scope **before** vector or text search. LLM answers do not bypass permission checks and do not replace deterministic analytics.
- **Migration source of truth:** v1 MySQL + repo-root `data/<year>` files. Maintain a v1→v2 id mapping; record skipped/suspicious rows as migration issues; imported data defaults to `private`. Diff v1 vs v2 outputs for score, GIR, putts, penalty strokes, shot category, expected/shot values, and recommendation category.

When implementing a v2 milestone, mark progress in `docs/implementation_plan_v2.md` and follow the acceptance criteria listed under each `Pn.x` section there.

## Conventions

- Python: 4-space indent, `snake_case` for functions/variables, `UPPER_CASE` for constants, `_helper_name` for module-private helpers. No enforced formatter — match surrounding style.
- Commit subjects in this repo are short and Korean (recent examples: `V2 작업계획 수립`, `분석 메뉴 분리`). Keep them brief and scoped to one change.
- Don't add new dependencies casually — `v1/requirements.txt` is intentionally tiny (`mysql-connector-python`, `Flask`, `pytest`, `numpy`).
