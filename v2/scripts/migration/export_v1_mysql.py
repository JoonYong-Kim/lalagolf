from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export v1 MySQL rows to JSON. MVP dry-run supports pre-exported JSON input.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--note",
        default="Direct MySQL export is environment-specific; use raw file import for MVP dry-run.",
    )
    args = parser.parse_args()

    payload = {
        "status": "not_connected",
        "note": args.note,
        "tables": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
