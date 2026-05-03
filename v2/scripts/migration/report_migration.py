from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

from _bootstrap import API_ROOT  # noqa: F401
from app.db.session import SessionLocal
from app.services.migration import build_migration_report, get_run, owner_for_cli, write_reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate JSON and Markdown migration reports.")
    parser.add_argument("migration_run_id", type=UUID)
    parser.add_argument("--output-dir", type=Path, default=Path("migration_reports"))
    parser.add_argument("--owner-email", default="owner@example.com")
    parser.add_argument("--owner-name", default="Import Owner")
    parser.add_argument("--owner-password", default="password")
    args = parser.parse_args()

    with SessionLocal() as db:
        owner = owner_for_cli(
            db,
            email=args.owner_email,
            name=args.owner_name,
            password=args.owner_password,
        )
        run = get_run(db, owner=owner, run_id=args.migration_run_id)
        report = build_migration_report(db, owner=owner, run=run)
        json_path, md_path = write_reports(report, output_dir=args.output_dir)

    print(
        json.dumps(
            {"json_report": str(json_path), "markdown_report": str(md_path)},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
