from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


V2_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = V2_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.services.early_import import (  # noqa: E402
    ensure_import_owner,
    import_raw_round_files,
    result_to_report_row,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import representative v1 raw round files into v2.")
    parser.add_argument("files", nargs="+", type=Path, help="v1 raw round text files to import.")
    parser.add_argument("--owner-email", default="owner@example.com")
    parser.add_argument("--owner-name", default="Import Owner")
    parser.add_argument("--owner-password", default="password")
    parser.add_argument("--commit", action="store_true", help="Commit imported rows.")
    args = parser.parse_args()

    file_paths = [path.resolve() for path in args.files]
    with SessionLocal() as db:
        owner = ensure_import_owner(
            db,
            email=args.owner_email,
            display_name=args.owner_name,
            password=args.owner_password,
        )
        results = import_raw_round_files(db, owner=owner, file_paths=file_paths)
        report = {
            "owner_id": str(owner.id),
            "owner_email": owner.email,
            "committed": args.commit,
            "rounds": [result_to_report_row(result) for result in results],
        }
        if args.commit:
            db.commit()
        else:
            db.rollback()

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
