from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

from _bootstrap import API_ROOT  # noqa: F401
from app.db.session import SessionLocal
from app.services.migration import compare_raw_files_to_v2, get_run, owner_for_cli


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare v1 raw file parse totals with imported v2 rows.")
    parser.add_argument("migration_run_id", type=UUID)
    parser.add_argument("files", nargs="+", type=Path)
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
        result = compare_raw_files_to_v2(
            db,
            owner=owner,
            run=run,
            file_paths=[path.resolve() for path in args.files],
        )
        db.commit()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
