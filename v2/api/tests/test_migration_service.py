from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MigrationIdMap, MigrationIssue, Round
from app.services.migration import (
    build_migration_report,
    compare_raw_files_to_v2,
    create_migration_run,
    import_raw_files_for_run,
    owner_for_cli,
    recalculate_imported_rounds,
    write_reports,
)
from tests.test_uploads_api import sample_round_text


def test_migration_dry_run_import_compare_and_report(
    db_session: Session,
    tmp_path: Path,
) -> None:
    raw_file = tmp_path / "round_20260411.txt"
    raw_file.write_text(sample_round_text(), encoding="utf-8")

    owner = owner_for_cli(
        db_session,
        email="owner@example.com",
        name="Import Owner",
        password="password",
    )
    run = create_migration_run(db_session, owner=owner, label="pytest-dry-run")
    import_result = import_raw_files_for_run(
        db_session,
        owner=owner,
        run=run,
        file_paths=[raw_file],
    )
    recalculate_result = recalculate_imported_rounds(db_session, owner=owner, run=run)
    compare_result = compare_raw_files_to_v2(
        db_session,
        owner=owner,
        run=run,
        file_paths=[raw_file],
    )
    report = build_migration_report(db_session, owner=owner, run=run)
    json_path, md_path = write_reports(report, output_dir=tmp_path / "reports")

    assert import_result["rounds"][0]["visibility"] == "private"
    assert recalculate_result["rounds"][0]["computed_status"] == "ready"
    assert compare_result["rounds"][0]["total_score_match"] is True
    assert report["privacy"]["all_imported_rounds_private"] is True
    assert report["ownership"]["all_imported_rows_have_owner"] is True
    assert json_path.exists()
    assert md_path.exists()

    assert db_session.scalars(select(MigrationIdMap)).first() is not None
    assert db_session.scalars(select(MigrationIssue)).first() is None
    assert db_session.scalars(select(Round).where(Round.user_id == owner.id)).first() is not None
