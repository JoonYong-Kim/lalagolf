from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Hole, Round, RoundCompanion, Shot, SourceFile, UploadReview, User
from app.models.constants import (
    COMPUTED_STATUS_PENDING,
    SOURCE_FILE_STATUS_COMMITTED,
    SOURCE_FILE_STATUS_FAILED,
    SOURCE_FILE_STATUS_PARSED,
    UPLOAD_REVIEW_STATUS_COMMITTED,
    UPLOAD_REVIEW_STATUS_FAILED,
    UPLOAD_REVIEW_STATUS_NEEDS_REVIEW,
    UPLOAD_REVIEW_STATUS_READY,
    VISIBILITY_PRIVATE,
)
from app.services.analytics import build_shot_facts_from_upload_preview, parse_upload_preview


class UploadError(Exception):
    pass


class UploadNotFoundError(Exception):
    pass


class UploadNotReadyError(Exception):
    pass


ALLOWED_UPLOAD_CONTENT_TYPES = {
    "text/plain",
    "text/x-log",
    "application/octet-stream",
}


def create_round_file_upload(
    db: Session,
    *,
    owner: User,
    filename: str,
    content_type: str | None,
    content: bytes,
    settings: Settings,
) -> UploadReview:
    if len(content) > settings.upload_max_bytes:
        raise UploadError("Uploaded file is too large")
    normalized_content_type = content_type.split(";", 1)[0].strip().lower() if content_type else ""
    if normalized_content_type and normalized_content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise UploadError("Uploaded file must be a text file")

    safe_filename = Path(filename).name or "round.txt"
    content_hash = hashlib.sha256(content).hexdigest()
    storage_dir = Path(settings.upload_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    source_file = SourceFile(
        user_id=owner.id,
        filename=safe_filename,
        content_type=content_type,
        storage_key="",
        file_size=len(content),
        content_hash=content_hash,
        status=SOURCE_FILE_STATUS_PARSED,
    )
    db.add(source_file)
    db.flush()

    storage_key = f"{owner.id}/{source_file.id}-{safe_filename}"
    storage_path = storage_dir / storage_key
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(content)
    source_file.storage_key = storage_key

    try:
        parse_result = parse_upload_preview(
            content.decode("utf-8"),
            file_name=safe_filename,
        )
    except UnicodeDecodeError as exc:
        source_file.status = SOURCE_FILE_STATUS_FAILED
        source_file.parse_error = "Uploaded file must be UTF-8 text"
        review = UploadReview(
            user_id=owner.id,
            source_file_id=source_file.id,
            status=UPLOAD_REVIEW_STATUS_FAILED,
            parsed_round={},
            warnings=[
                {
                    "code": "invalid_encoding",
                    "message": "Uploaded file must be UTF-8 text.",
                    "path": "file",
                }
            ],
            user_edits={},
        )
        db.add(review)
        db.commit()
        raise UploadError("Uploaded file must be UTF-8 text") from exc

    warnings = parse_result["warnings"]
    review = UploadReview(
        user_id=owner.id,
        source_file_id=source_file.id,
        status=UPLOAD_REVIEW_STATUS_NEEDS_REVIEW if warnings else UPLOAD_REVIEW_STATUS_READY,
        parsed_round=parse_result["parsed_round"],
        warnings=warnings,
        user_edits={},
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_upload_review(db: Session, *, owner: User, upload_review_id: UUID) -> UploadReview:
    review = db.scalars(
        select(UploadReview).where(
            UploadReview.id == upload_review_id,
            UploadReview.user_id == owner.id,
        )
    ).first()
    if review is None:
        raise UploadNotFoundError
    return review


def get_upload_review_raw_content(
    review: UploadReview,
    *,
    settings: Settings,
) -> str | None:
    source_file = review.source_file
    if source_file is None or not source_file.storage_key:
        return _render_review_raw_content(review.parsed_round)
    storage_path = Path(settings.upload_storage_dir) / source_file.storage_key
    if not storage_path.exists():
        return _render_review_raw_content(review.parsed_round)
    return storage_path.read_text(encoding="utf-8")


def update_upload_review_edits(
    db: Session,
    *,
    owner: User,
    upload_review_id: UUID,
    user_edits: dict[str, Any],
) -> UploadReview:
    review = get_upload_review(db, owner=owner, upload_review_id=upload_review_id)
    review.user_edits = user_edits
    review.parsed_round = _apply_review_edits(review.parsed_round, user_edits)
    db.commit()
    db.refresh(review)
    return review


def update_upload_review_raw_content(
    db: Session,
    *,
    owner: User,
    upload_review_id: UUID,
    raw_content: str,
    settings: Settings,
) -> UploadReview:
    review = get_upload_review(db, owner=owner, upload_review_id=upload_review_id)
    source_file = review.source_file
    if source_file is None:
        raise UploadNotFoundError

    encoded = raw_content.encode("utf-8")
    if len(encoded) > settings.upload_max_bytes:
        raise UploadError("Uploaded file is too large")

    storage_path = Path(settings.upload_storage_dir) / source_file.storage_key
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(encoded)

    source_file.file_size = len(encoded)
    source_file.content_hash = hashlib.sha256(encoded).hexdigest()
    source_file.status = SOURCE_FILE_STATUS_PARSED
    source_file.parse_error = None

    parse_result = parse_upload_preview(raw_content, file_name=source_file.filename)
    warnings = parse_result["warnings"]
    review.parsed_round = parse_result["parsed_round"]
    review.warnings = warnings
    review.user_edits = {}
    review.status = UPLOAD_REVIEW_STATUS_NEEDS_REVIEW if warnings else UPLOAD_REVIEW_STATUS_READY
    db.commit()
    db.refresh(review)
    return review


def _render_review_raw_content(parsed_round: dict[str, Any]) -> str | None:
    if not isinstance(parsed_round, dict) or not parsed_round:
        return None

    lines: list[str] = []
    tee_off_time = parsed_round.get("tee_off_time")
    play_date = parsed_round.get("play_date")
    if isinstance(tee_off_time, str) and tee_off_time.strip():
        lines.append(tee_off_time.strip())
    elif isinstance(play_date, str) and play_date.strip():
        lines.append(play_date.strip())

    course_name = parsed_round.get("course_name")
    if isinstance(course_name, str) and course_name.strip():
        lines.append(course_name.strip())

    companions = parsed_round.get("companions") or []
    if isinstance(companions, list) and companions:
        lines.append(" ".join(str(name).strip() for name in companions if str(name).strip()))
    elif len(lines) > 0:
        lines.append("")

    holes = parsed_round.get("holes") or []
    if not isinstance(holes, list) or not holes:
        return "\n".join(line for line in lines if line is not None).strip() or None

    if lines and lines[-1] != "":
        lines.append("")

    for hole in holes:
        if not isinstance(hole, dict):
            continue
        hole_number = hole.get("hole_number")
        par = hole.get("par")
        if hole_number is None or par is None:
            continue
        lines.append(f"{hole_number} P{par}")
        for shot in hole.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            raw_text = shot.get("raw_text")
            if isinstance(raw_text, str) and raw_text.strip():
                lines.append(raw_text.strip())
                continue
            parts: list[str] = []
            for key in ("club", "feel_grade", "result_grade"):
                value = shot.get(key)
                if isinstance(value, str) and value.strip():
                    parts.append(value.strip())
            distance = shot.get("distance")
            if distance is not None:
                parts.append(str(distance))
            penalty_type = shot.get("penalty_type")
            if isinstance(penalty_type, str) and penalty_type.strip():
                parts.append(penalty_type.strip())
            if parts:
                lines.append(" ".join(parts))
        lines.append("")

    return "\n".join(lines).strip() or None


def commit_upload_review(
    db: Session,
    *,
    owner: User,
    upload_review_id: UUID,
    share_course: bool = False,
    share_exact_date: bool = False,
) -> Round:
    review = get_upload_review(db, owner=owner, upload_review_id=upload_review_id)
    if review.status == UPLOAD_REVIEW_STATUS_COMMITTED and review.committed_round_id:
        round_ = db.get(Round, review.committed_round_id)
        if round_ is None:
            raise UploadNotReadyError
        return round_

    if review.status not in {UPLOAD_REVIEW_STATUS_READY, UPLOAD_REVIEW_STATUS_NEEDS_REVIEW}:
        raise UploadNotReadyError

    parsed_round = review.parsed_round
    holes = parsed_round.get("holes") or []
    if not holes:
        raise UploadNotReadyError

    round_ = db.get(Round, review.committed_round_id) if review.committed_round_id else None
    if round_ is None:
        round_ = Round(user_id=owner.id, source_file_id=review.source_file_id)
        db.add(round_)
    elif round_.user_id != owner.id:
        raise UploadNotFoundError
    else:
        _clear_round_children(db, round_)

    _apply_parsed_round_to_round(
        db,
        owner=owner,
        round_=round_,
        parsed_round=parsed_round,
        visibility=VISIBILITY_PRIVATE,
        share_course=share_course,
        share_exact_date=share_exact_date,
    )

    review.status = UPLOAD_REVIEW_STATUS_COMMITTED
    review.committed_round_id = round_.id
    source_file = db.get(SourceFile, review.source_file_id)
    if source_file is not None:
        source_file.status = SOURCE_FILE_STATUS_COMMITTED

    build_shot_facts_from_upload_preview(parsed_round, round_ref=str(round_.id))
    db.commit()
    db.refresh(round_)
    return round_


def _apply_parsed_round_to_round(
    db: Session,
    *,
    owner: User,
    round_: Round,
    parsed_round: dict[str, Any],
    visibility: str,
    share_course: bool,
    share_exact_date: bool,
) -> None:
    holes = parsed_round.get("holes") or []
    round_.source_file_id = round_.source_file_id
    round_.course_name = _required_text(parsed_round.get("course_name"), "course_name")
    round_.play_date = _required_play_date(parsed_round)
    round_.tee_off_time = parsed_round.get("tee_off_time")
    round_.total_score = parsed_round.get("total_score")
    round_.total_par = parsed_round.get("total_par")
    round_.score_to_par = parsed_round.get("score_to_par")
    round_.hole_count = parsed_round.get("hole_count") or len(holes)
    round_.visibility = visibility
    round_.share_course = share_course
    round_.share_exact_date = share_exact_date
    round_.computed_status = COMPUTED_STATUS_PENDING
    db.flush()

    for companion_name in parsed_round.get("companions", []):
        db.add(RoundCompanion(round_id=round_.id, user_id=owner.id, name=companion_name))

    for hole_payload in holes:
        hole = Hole(
            user_id=owner.id,
            round_id=round_.id,
            hole_number=hole_payload.get("hole_number"),
            par=hole_payload.get("par"),
            score=hole_payload.get("score"),
            putts=hole_payload.get("putts"),
            fairway_hit=hole_payload.get("fairway_hit")
            if hole_payload.get("fairway_hit") is not None
            else _derive_fairway_hit(hole_payload),
            gir=hole_payload.get("gir"),
            penalties=hole_payload.get("penalties") or 0,
        )
        db.add(hole)
        db.flush()

        for shot_payload in hole_payload.get("shots", []):
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


def _clear_round_children(db: Session, round_: Round) -> None:
    for companion in db.scalars(select(RoundCompanion).where(RoundCompanion.round_id == round_.id)):
        db.delete(companion)
    for hole in db.scalars(select(Hole).where(Hole.round_id == round_.id)):
        db.delete(hole)
    db.flush()


def get_upload_job(db: Session, *, owner: User, job_id: UUID) -> dict[str, Any]:
    review = get_upload_review(db, owner=owner, upload_review_id=job_id)
    if review.status == UPLOAD_REVIEW_STATUS_FAILED:
        status = "failed"
    elif review.status in {UPLOAD_REVIEW_STATUS_READY, UPLOAD_REVIEW_STATUS_NEEDS_REVIEW}:
        status = "completed"
    else:
        status = review.status
    return {
        "id": review.id,
        "status": status,
        "kind": "parse_upload_file",
        "resource_id": review.id,
    }


def _required_play_date(parsed_round: dict[str, Any]) -> date:
    value = parsed_round.get("play_date")
    if not value:
        raise UploadNotReadyError
    return date.fromisoformat(value)


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UploadNotReadyError(f"{field_name} is required")
    return value.strip()


def _apply_review_edits(
    parsed_round: dict[str, Any],
    user_edits: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(parsed_round)
    for field in ("course_name", "play_date", "tee_off_time"):
        value = user_edits.get(field)
        if isinstance(value, str) and value.strip():
            updated[field] = value.strip()

    companions = user_edits.get("companions")
    if isinstance(companions, list):
        updated["companions"] = [
            str(name).strip()
            for name in companions
            if str(name).strip()
        ]

    holes = user_edits.get("holes")
    if isinstance(holes, list):
        updated["holes"] = [
            _normalize_review_hole(hole) for hole in holes if isinstance(hole, dict)
        ]
        updated["hole_count"] = len(updated["holes"])
        updated["total_score"] = sum((hole.get("score") or 0) for hole in updated["holes"])
        updated["total_par"] = sum((hole.get("par") or 0) for hole in updated["holes"])
        updated["score_to_par"] = updated["total_score"] - updated["total_par"]

    return updated


def _normalize_review_hole(hole: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(hole)
    normalized["hole_number"] = _int_or_none(hole.get("hole_number"))
    normalized["par"] = _int_or_none(hole.get("par"))
    normalized["score"] = _int_or_none(hole.get("score"))
    normalized["putts"] = _int_or_none(hole.get("putts"))

    shots = []
    for shot in hole.get("shots") or []:
        if isinstance(shot, dict):
            shots.append(_normalize_review_shot(shot))
    normalized["shots"] = shots
    normalized["penalties"] = sum((shot.get("penalty_strokes") or 0) for shot in shots)
    normalized["gir"] = _is_gir(
        normalized.get("par"),
        normalized.get("score"),
        normalized.get("putts"),
    )
    return normalized


def _normalize_review_shot(shot: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(shot)
    penalty_type = normalized.get("penalty_type")
    if isinstance(penalty_type, str):
        penalty_type = penalty_type.strip().upper() or None
    else:
        penalty_type = None
    normalized["penalty_type"] = penalty_type
    normalized["penalty_strokes"] = {"H": 1, "UN": 1, "OB": 2}.get(penalty_type, 0)
    normalized["shot_number"] = _int_or_none(normalized.get("shot_number"))
    normalized["distance"] = _int_or_none(normalized.get("distance"))
    normalized["score_cost"] = _int_or_none(normalized.get("score_cost")) or 1
    for field in ("club", "club_normalized", "start_lie", "end_lie", "result_grade", "feel_grade"):
        value = normalized.get(field)
        normalized[field] = (
            value.strip().upper() if isinstance(value, str) and value.strip() else None
        )
    return normalized


def _int_or_none(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _is_gir(par: int | None, score: int | None, putts: int | None) -> bool | None:
    if par is None or score is None or putts is None:
        return None
    return par >= score - putts + 2


def _derive_fairway_hit(hole: dict[str, Any]) -> bool | None:
    if hole.get("par") not in {4, 5}:
        return None
    first_shot = next(
        (
            shot
            for shot in hole.get("shots") or []
            if isinstance(shot, dict) and shot.get("shot_number") == 1
        ),
        None,
    )
    if not first_shot or first_shot.get("start_lie") != "T":
        return None
    end_lie = first_shot.get("end_lie")
    if end_lie is None:
        return None
    return end_lie == "F"
