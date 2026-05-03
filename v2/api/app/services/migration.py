from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Hole,
    MigrationIdMap,
    MigrationIssue,
    MigrationRun,
    Round,
    Shot,
    SourceFile,
    UploadReview,
    User,
)
from app.models.constants import VISIBILITY_PRIVATE
from app.services.analytics import recalculate_round_metrics
from app.services.early_import import (
    EarlyImportError,
    ensure_import_owner,
    import_raw_round_file,
    result_to_report_row,
)


def create_migration_run(
    db: Session,
    *,
    owner: User,
    label: str,
    source: str = "v1",
) -> MigrationRun:
    run = MigrationRun(user_id=owner.id, label=label, source=source, status="started", summary={})
    db.add(run)
    db.flush()
    return run


def import_raw_files_for_run(
    db: Session,
    *,
    owner: User,
    run: MigrationRun,
    file_paths: list[Path],
) -> dict[str, Any]:
    rows = []
    for file_path in file_paths:
        try:
            result = import_raw_round_file(db, owner=owner, file_path=file_path)
            row = result_to_report_row(result)
            rows.append(row)
            _upsert_id_map(
                db,
                run=run,
                owner=owner,
                entity_type="round",
                v1_id=file_path.name,
                v2_id=uuid.UUID(result.round_id),
                payload=row,
            )
        except (EarlyImportError, OSError, ValueError) as exc:
            _record_issue(
                db,
                run=run,
                owner=owner,
                severity="error",
                code="raw_import_failed",
                message=str(exc),
                payload={"file": str(file_path)},
            )

    run.summary = {**(run.summary or {}), "imported_rounds": len(rows)}
    run.status = "imported"
    db.flush()
    return {"rounds": rows}


def recalculate_imported_rounds(db: Session, *, owner: User, run: MigrationRun) -> dict[str, Any]:
    maps = db.scalars(
        select(MigrationIdMap).where(
            MigrationIdMap.migration_run_id == run.id,
            MigrationIdMap.entity_type == "round",
        )
    ).all()
    rows = []
    for mapping in maps:
        result = recalculate_round_metrics(db, owner=owner, round_id=mapping.v2_id)
        rows.append(
            {
                "round_id": str(result["round_id"]),
                "computed_status": result["computed_status"],
            }
        )

    run.summary = {**(run.summary or {}), "recalculated_rounds": len(rows)}
    run.status = "recalculated"
    db.flush()
    return {"rounds": rows}


def compare_raw_files_to_v2(
    db: Session,
    *,
    owner: User,
    run: MigrationRun,
    file_paths: list[Path],
) -> dict[str, Any]:
    rows = []
    by_v1_id = {
        mapping.v1_id: mapping
        for mapping in db.scalars(
            select(MigrationIdMap).where(
                MigrationIdMap.migration_run_id == run.id,
                MigrationIdMap.entity_type == "round",
            )
        ).all()
    }
    for file_path in file_paths[:20]:
        mapping = by_v1_id.get(file_path.name)
        if mapping is None:
            _record_issue(
                db,
                run=run,
                owner=owner,
                severity="error",
                code="missing_id_map",
                message="No v2 round mapping for v1 raw file",
                payload={"file": str(file_path)},
            )
            continue
        v2_round = db.get(Round, mapping.v2_id)
        expected_score = (mapping.payload or {}).get("total_score")
        actual_score = v2_round.total_score if v2_round else None
        matched = expected_score == actual_score
        row = {
            "v1_id": file_path.name,
            "v2_round_id": str(mapping.v2_id),
            "v1_total_score": expected_score,
            "v2_total_score": actual_score,
            "total_score_match": matched,
        }
        rows.append(row)
        if not matched:
            _record_issue(
                db,
                run=run,
                owner=owner,
                severity="error",
                code="score_mismatch",
                message="v1/v2 total score mismatch",
                payload=row,
            )

    run.summary = {
        **(run.summary or {}),
        "compared_rounds": len(rows),
        "score_matches": sum(1 for row in rows if row["total_score_match"]),
    }
    run.status = "compared"
    db.flush()
    return {"rounds": rows}


def build_migration_report(db: Session, *, owner: User, run: MigrationRun) -> dict[str, Any]:
    issues = db.scalars(
        select(MigrationIssue).where(MigrationIssue.migration_run_id == run.id)
    ).all()
    id_maps = db.scalars(
        select(MigrationIdMap).where(MigrationIdMap.migration_run_id == run.id)
    ).all()
    row_counts = {
        "rounds": db.scalar(select(func.count(Round.id)).where(Round.user_id == owner.id)) or 0,
        "holes": db.scalar(select(func.count(Hole.id)).where(Hole.user_id == owner.id)) or 0,
        "shots": db.scalar(select(func.count(Shot.id)).where(Shot.user_id == owner.id)) or 0,
        "source_files": db.scalar(
            select(func.count(SourceFile.id)).where(SourceFile.user_id == owner.id)
        )
        or 0,
        "upload_reviews": db.scalar(
            select(func.count(UploadReview.id)).where(UploadReview.user_id == owner.id)
        )
        or 0,
    }
    imported_round_ids = [
        mapping.v2_id for mapping in id_maps if mapping.entity_type == "round"
    ]
    imported_private_count = 0
    if imported_round_ids:
        imported_private_count = db.scalar(
            select(func.count(Round.id)).where(
                Round.id.in_(imported_round_ids),
                Round.user_id == owner.id,
                Round.visibility == VISIBILITY_PRIVATE,
            )
        ) or 0
    ownerless = {
        "rounds": db.scalar(select(func.count(Round.id)).where(Round.user_id.is_(None))) or 0,
        "holes": db.scalar(select(func.count(Hole.id)).where(Hole.user_id.is_(None))) or 0,
        "shots": db.scalar(select(func.count(Shot.id)).where(Shot.user_id.is_(None))) or 0,
    }
    return {
        "migration_run": {
            "id": str(run.id),
            "label": run.label,
            "status": run.status,
            "summary": run.summary or {},
        },
        "schema_inventory": sorted(row_counts.keys()),
        "row_counts": row_counts,
        "privacy": {
            "private_rounds": imported_private_count,
            "imported_round_count": len(imported_round_ids),
            "all_imported_rounds_private": imported_private_count == len(imported_round_ids),
        },
        "ownership": {
            "owner_id": str(owner.id),
            "ownerless_counts": ownerless,
            "all_imported_rows_have_owner": all(count == 0 for count in ownerless.values()),
        },
        "id_map_count": len(id_maps),
        "issues": [_issue_payload(issue) for issue in issues],
    }


def write_reports(report: dict[str, Any], *, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = report["migration_run"]["id"]
    json_path = output_dir / f"migration_report_{run_id}.json"
    md_path = output_dir / f"migration_report_{run_id}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def owner_for_cli(db: Session, *, email: str, name: str, password: str) -> User:
    return ensure_import_owner(db, email=email, display_name=name, password=password)


def get_run(db: Session, *, owner: User, run_id: uuid.UUID) -> MigrationRun:
    run = db.scalars(
        select(MigrationRun).where(MigrationRun.id == run_id, MigrationRun.user_id == owner.id)
    ).first()
    if run is None:
        raise ValueError(f"migration run not found: {run_id}")
    return run


def _upsert_id_map(
    db: Session,
    *,
    run: MigrationRun,
    owner: User,
    entity_type: str,
    v1_id: str,
    v2_id: uuid.UUID,
    payload: dict[str, Any],
) -> MigrationIdMap:
    mapping = db.scalars(
        select(MigrationIdMap).where(
            MigrationIdMap.migration_run_id == run.id,
            MigrationIdMap.entity_type == entity_type,
            MigrationIdMap.v1_id == v1_id,
        )
    ).first()
    if mapping is None:
        mapping = MigrationIdMap(
            migration_run_id=run.id,
            user_id=owner.id,
            entity_type=entity_type,
            v1_id=v1_id,
            v2_id=v2_id,
        )
        db.add(mapping)
    mapping.payload = payload
    return mapping


def _record_issue(
    db: Session,
    *,
    run: MigrationRun,
    owner: User,
    severity: str,
    code: str,
    message: str,
    payload: dict[str, Any],
) -> MigrationIssue:
    issue = MigrationIssue(
        migration_run_id=run.id,
        user_id=owner.id,
        severity=severity,
        code=code,
        message=message,
        payload=payload,
    )
    db.add(issue)
    return issue


def _issue_payload(issue: MigrationIssue) -> dict[str, Any]:
    return {
        "severity": issue.severity,
        "code": issue.code,
        "message": issue.message,
        "payload": issue.payload,
    }


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# LalaGolf Migration Report",
        "",
        f"- Run ID: `{report['migration_run']['id']}`",
        f"- Status: `{report['migration_run']['status']}`",
        f"- ID maps: {report['id_map_count']}",
        "",
        "## Row Counts",
        "",
    ]
    for table, count in report["row_counts"].items():
        lines.append(f"- {table}: {count}")
    lines.extend(
        [
            "",
            "## Acceptance",
            "",
            f"- Imported rounds private: {report['privacy']['all_imported_rounds_private']}",
            f"- Imported rows have owner: {report['ownership']['all_imported_rows_have_owner']}",
            "",
            "## Issues",
            "",
        ]
    )
    if not report["issues"]:
        lines.append("- None")
    for issue in report["issues"]:
        lines.append(f"- [{issue['severity']}] {issue['code']}: {issue['message']}")
    lines.append("")
    return "\n".join(lines)
