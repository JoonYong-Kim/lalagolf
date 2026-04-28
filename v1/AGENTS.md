# Repository Guidelines

## Project Structure & Module Organization
Core Python code lives in `src/`. `src/data_parser.py` parses round text files, `src/db_loader.py` handles MySQL persistence, and analytics logic is split across `src/metrics.py`, `src/shot_model.py`, `src/expected_value.py`, `src/strokes_gained.py`, and `src/recommendations.py`. The Flask app lives in `src/webapp/` with routes, templates, and static assets. Entry points are `load_data.py` for imports and `run_webapp.py` for local development. Tests live in `tests/`, sample inputs in `tests/data/`, planning notes in `docs/`, raw golf records in `data/<year>/`, and schema/deployment/config files in `scripts/` and `conf/`. Deployment helpers currently include `scripts/schema.sql`, `scripts/install_systemd.sh`, and `scripts/uninstall_systemd.sh`.

## Build, Test, and Development Commands
Create an environment with `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`. Run the full test suite with `pytest -q`. For a quick syntax check after analytics or route edits, use `python -m py_compile src/recommendations.py src/webapp/routes.py`. Start the app locally with `python run_webapp.py`; it binds to port `2323`. Load round files into MySQL with `python load_data.py` after updating `conf/lalagolf.conf` with valid `DB_CONFIG` and `WEBAPP_USERS`. For systemd deployment, use `sudo bash scripts/install_systemd.sh`; remove it with `sudo bash scripts/uninstall_systemd.sh`.

## Coding Style & Naming Conventions
Use Python with 4-space indentation and group imports by standard library, third-party, and local modules. Follow existing names: `snake_case` for functions and variables, `UPPER_CASE` for constants, and `_helper_name` for internal helpers. Keep Flask routes thin; parsing stays in `src/data_parser.py`, persistence in `src/db_loader.py`, and analytics/recommendation logic in the dedicated `src/*` modules. There is no enforced formatter, so match surrounding style and keep patches focused.

## Testing Guidelines
Tests use `pytest`. Put new coverage in the matching module-level file such as `tests/test_metrics.py`, `tests/test_recommendations.py`, or a new `test_*.py` file. Prefer fixture-backed samples under `tests/data/` for parser edge cases, and small inline dictionaries for analytics/recommendation logic. Run `pytest -q` before opening a PR; if you changed recommendation or route code, also run `python -m py_compile src/recommendations.py src/webapp/routes.py`.

## Commit & Pull Request Guidelines
Recent history uses short Korean subject lines such as `추가 탭`. Keep commit titles brief, imperative, and scoped to one change. Pull requests should include a clear summary, note any schema or config updates, link the relevant issue if one exists, and attach screenshots for template or CSS changes under `src/webapp/templates/` or `src/webapp/static/`.

## Security & Configuration Tips
`conf/lalagolf.conf` contains local credentials and web users; do not commit real secrets. Flask now reads `SECRET_KEY` from the environment and falls back to a generated development key, so keep production values in environment variables rather than source files. The systemd installer creates `/etc/lalagolf/lalagolf.env`; treat that file as secret as well. Sanitize sample config values in shared branches.
