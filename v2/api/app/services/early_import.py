from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Hole,
    Round,
    RoundCompanion,
    Shot,
    SourceFile,
    UploadReview,
    User,
    UserProfile,
)
from app.models.constants import (
    COMPUTED_STATUS_PENDING,
    SOURCE_FILE_STATUS_COMMITTED,
    UPLOAD_REVIEW_STATUS_COMMITTED,
    VISIBILITY_PRIVATE,
)
from app.services.analytics import build_shot_facts_from_upload_preview, parse_upload_preview


class EarlyImportError(Exception):
    pass


@dataclass(frozen=True)
class EarlyImportResult:
    source_file_id: str
    upload_review_id: str
    round_id: str
    course_name: str
    play_date: date
    total_score: int
    total_par: int
    hole_count: int
    shot_count: int
    warning_count: int
    shot_fact_count: int


def ensure_import_owner(
    db: Session,
    *,
    email: str = "owner@example.com",
    display_name: str = "Import Owner",
    password: str = "password",
) -> User:
    user = db.scalars(select(User).where(User.email == email)).first()
    if user is not None:
        return user

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        profile=UserProfile(),
    )
    db.add(user)
    db.flush()
    return user


def import_raw_round_file(
    db: Session,
    *,
    owner: User,
    file_path: Path,
    storage_prefix: str = "migration/raw",
) -> EarlyImportResult:
    raw_content = file_path.read_text(encoding="utf-8")
    content_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
    existing_result = _existing_import_result(db, owner=owner, content_hash=content_hash)
    if existing_result is not None:
        return existing_result

    parse_result = parse_upload_preview(raw_content, file_name=file_path.name)
    parsed_round = parse_result["parsed_round"]
    warnings = parse_result["warnings"]

    play_date = _required_play_date(parsed_round)
    course_name = _required_text(parsed_round.get("course_name"), "course_name")
    holes = parsed_round.get("holes") or []
    if not holes:
        raise EarlyImportError("parsed round has no holes")

    source_file = SourceFile(
        user_id=owner.id,
        filename=file_path.name,
        content_type="text/plain",
        storage_key=f"{storage_prefix}/{file_path.name}",
        file_size=len(raw_content.encode("utf-8")),
        content_hash=content_hash,
        status=SOURCE_FILE_STATUS_COMMITTED,
    )
    db.add(source_file)
    db.flush()

    upload_review = UploadReview(
        user_id=owner.id,
        source_file_id=source_file.id,
        status=UPLOAD_REVIEW_STATUS_COMMITTED,
        parsed_round=parsed_round,
        warnings=warnings,
        user_edits={},
    )
    db.add(upload_review)
    db.flush()

    round_ = Round(
        user_id=owner.id,
        source_file_id=source_file.id,
        course_name=course_name,
        play_date=play_date,
        total_score=parsed_round.get("total_score"),
        total_par=parsed_round.get("total_par"),
        score_to_par=parsed_round.get("score_to_par"),
        hole_count=parsed_round.get("hole_count") or len(holes),
        visibility=VISIBILITY_PRIVATE,
        share_course=False,
        share_exact_date=False,
        computed_status=COMPUTED_STATUS_PENDING,
    )
    db.add(round_)
    db.flush()

    for companion_name in parsed_round.get("companions", []):
        db.add(RoundCompanion(round_id=round_.id, user_id=owner.id, name=companion_name))

    shot_count = 0
    for hole_payload in holes:
        hole = Hole(
            user_id=owner.id,
            round_id=round_.id,
            hole_number=hole_payload.get("hole_number"),
            par=hole_payload.get("par"),
            score=hole_payload.get("score"),
            putts=hole_payload.get("putts"),
            gir=hole_payload.get("gir"),
            penalties=hole_payload.get("penalties") or 0,
        )
        db.add(hole)
        db.flush()

        for shot_payload in hole_payload.get("shots", []):
            shot_count += 1
            db.add(
                Shot(
                    user_id=owner.id,
                    round_id=round_.id,
                    hole_id=hole.id,
                    shot_number=shot_payload.get("shot_number"),
                    club=shot_payload.get("club"),
                    club_normalized=shot_payload.get("club_normalized"),
                    distance=shot_payload.get("distance"),
                    start_lie=shot_payload.get("start_lie"),
                    end_lie=shot_payload.get("end_lie"),
                    result_grade=shot_payload.get("result_grade"),
                    feel_grade=shot_payload.get("feel_grade"),
                    penalty_type=shot_payload.get("penalty_type"),
                    penalty_strokes=shot_payload.get("penalty_strokes") or 0,
                    score_cost=shot_payload.get("score_cost") or 1,
                    raw_text=shot_payload.get("raw_text"),
                )
            )

    upload_review.committed_round_id = round_.id
    shot_facts = build_shot_facts_from_upload_preview(parsed_round, round_ref=str(round_.id))
    db.flush()

    return EarlyImportResult(
        source_file_id=str(source_file.id),
        upload_review_id=str(upload_review.id),
        round_id=str(round_.id),
        course_name=course_name,
        play_date=play_date,
        total_score=parsed_round["total_score"],
        total_par=parsed_round["total_par"],
        hole_count=parsed_round["hole_count"],
        shot_count=shot_count,
        warning_count=len(warnings),
        shot_fact_count=len(shot_facts),
    )


def import_raw_round_files(
    db: Session,
    *,
    owner: User,
    file_paths: list[Path],
) -> list[EarlyImportResult]:
    results = []
    for file_path in file_paths:
        results.append(import_raw_round_file(db, owner=owner, file_path=file_path))
    return results


def result_to_report_row(result: EarlyImportResult) -> dict[str, Any]:
    return {
        "round_id": result.round_id,
        "source_file_id": result.source_file_id,
        "upload_review_id": result.upload_review_id,
        "course_name": result.course_name,
        "play_date": result.play_date.isoformat(),
        "total_score": result.total_score,
        "total_par": result.total_par,
        "hole_count": result.hole_count,
        "shot_count": result.shot_count,
        "warning_count": result.warning_count,
        "shot_fact_count": result.shot_fact_count,
        "visibility": VISIBILITY_PRIVATE,
    }


def _existing_import_result(
    db: Session,
    *,
    owner: User,
    content_hash: str,
) -> EarlyImportResult | None:
    source_file = db.scalars(
        select(SourceFile).where(
            SourceFile.user_id == owner.id,
            SourceFile.content_hash == content_hash,
        )
    ).first()
    if source_file is None:
        return None

    upload_review = db.scalars(
        select(UploadReview).where(UploadReview.source_file_id == source_file.id)
    ).first()
    if upload_review is None or upload_review.committed_round_id is None:
        return None

    round_ = db.get(Round, upload_review.committed_round_id)
    if round_ is None:
        return None

    shot_count = db.scalar(select(func.count(Shot.id)).where(Shot.round_id == round_.id)) or 0
    return EarlyImportResult(
        source_file_id=str(source_file.id),
        upload_review_id=str(upload_review.id),
        round_id=str(round_.id),
        course_name=round_.course_name,
        play_date=round_.play_date,
        total_score=round_.total_score or 0,
        total_par=round_.total_par or 0,
        hole_count=round_.hole_count,
        shot_count=shot_count,
        warning_count=len(upload_review.warnings or []),
        shot_fact_count=shot_count,
    )


def _required_play_date(parsed_round: dict[str, Any]) -> date:
    value = parsed_round.get("play_date")
    if not value:
        raise EarlyImportError("play_date is required")
    return date.fromisoformat(value)


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EarlyImportError(f"{field_name} is required")
    return value.strip()
