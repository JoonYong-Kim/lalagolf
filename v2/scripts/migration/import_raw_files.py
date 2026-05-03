from __future__ import annotations

import argparse
import json
from pathlib import Path

from _bootstrap import API_ROOT  # noqa: F401
from app.db.session import SessionLocal
from app.services.migration import create_migration_run, import_raw_files_for_run, owner_for_cli


def main() -> None:
    parser = argparse.ArgumentParser(description="Import v1 raw round text files into v2.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--label", default="raw-file-dry-run")
    parser.add_argument("--owner-email", default="owner@example.com")
    parser.add_argument("--owner-name", default="Import Owner")
    parser.add_argument("--owner-password", default="password")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        owner = owner_for_cli(
            db,
            email=args.owner_email,
            name=args.owner_name,
            password=args.owner_password,
        )
        run = create_migration_run(db, owner=owner, label=args.label)
        result = import_raw_files_for_run(
            db,
            owner=owner,
            run=run,
            file_paths=[path.resolve() for path in args.files],
        )
        payload = {
            "migration_run_id": str(run.id),
            "committed": args.commit,
            **result,
        }
        if args.commit:
            db.commit()
        else:
            db.rollback()

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
