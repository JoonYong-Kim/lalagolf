import uuid
from datetime import UTC, datetime
from datetime import date as date_type
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models import AnalysisJob, Hole, Round, RoundCompanion, Shot, User
from app.models.constants import (
    COMPUTED_STATUS_DRAFT,
    VISIBILITY_PRIVATE,
)
from app.services.analysis_jobs import enqueue_round_analysis_job


class DraftAlreadyExistsError(Exception):
    def __init__(self, round_id: uuid.UUID):
        super().__init__(str(round_id))
        self.round_id = round_id


class DraftNotFoundError(Exception):
    pass


class DraftValidationError(ValueError):
    pass


PENALTY_STROKES = {
    "H": 1,
    "UN": 1,
    "OB": 2,
}


def get_active_draft(db: Session, *, owner: User) -> Round | None:
    return db.scalars(
        select(Round)
        .options(
            selectinload(Round.companions),
            selectinload(Round.holes).selectinload(Hole.shots),
        )
        .where(
            Round.user_id == owner.id,
            Round.computed_status == COMPUTED_STATUS_DRAFT,
            Round.deleted_at.is_(None),
        )
        .order_by(Round.created_at.desc())
        .limit(1)
    ).first()


def create_draft(db: Session, *, owner: User) -> Round:
    existing = get_active_draft(db, owner=owner)
    if existing is not None:
        raise DraftAlreadyExistsError(existing.id)

    round_ = Round(
        user_id=owner.id,
        course_name="",
        play_date=datetime.now(UTC).date(),
        hole_count=18,
        visibility=VISIBILITY_PRIVATE,
        computed_status=COMPUTED_STATUS_DRAFT,
    )
    db.add(round_)
    db.flush()

    for hole_number in range(1, 19):
        db.add(
            Hole(
                round_id=round_.id,
                user_id=owner.id,
                hole_number=hole_number,
                par=4,
                penalties=0,
            )
        )

    db.commit()
    db.refresh(round_)
    return _load_draft(db, owner=owner, round_id=round_.id)


def discard_draft(db: Session, *, owner: User, round_id: uuid.UUID) -> None:
    round_ = _load_draft(db, owner=owner, round_id=round_id)
    db.delete(round_)
    db.commit()


def update_draft_meta(
    db: Session,
    *,
    owner: User,
    round_id: uuid.UUID,
    play_date: date_type | None = None,
    course_name: str | None = None,
    tee_off_time: str | None = None,
    companions: list[str] | None = None,
) -> Round:
    round_ = _load_draft(db, owner=owner, round_id=round_id)
    if play_date is not None:
        round_.play_date = play_date
    if course_name is not None:
        round_.course_name = course_name.strip()
    if tee_off_time is not None:
        round_.tee_off_time = tee_off_time.strip() or None
    if companions is not None:
        for existing in list(round_.companions):
            db.delete(existing)
        db.flush()
        for name in companions:
            stripped = name.strip()
            if stripped:
                db.add(
                    RoundCompanion(
                        round_id=round_.id,
                        user_id=owner.id,
                        name=stripped,
                    )
                )
    db.commit()
    return _load_draft(db, owner=owner, round_id=round_id)


def upsert_hole_shots(
    db: Session,
    *,
    owner: User,
    round_id: uuid.UUID,
    hole_number: int,
    par: int,
    shots: list[dict[str, Any]],
) -> Round:
    round_ = _load_draft(db, owner=owner, round_id=round_id)
    hole = next((h for h in round_.holes if h.hole_number == hole_number), None)
    if hole is None:
        raise DraftNotFoundError(f"Hole {hole_number} not found")

    hole.par = par

    for existing in list(hole.shots):
        db.delete(existing)
    db.flush()

    total_penalties = 0
    for idx, shot_input in enumerate(shots, start=1):
        code = shot_input.get("code")
        penalty_strokes = PENALTY_STROKES.get(code, 0) if code else 0
        end_lie = "bunker" if code == "B" else None

        parts: list[str] = [shot_input["club"], shot_input["feel"], shot_input["result"]]
        if shot_input.get("distance") is not None:
            parts.append(str(shot_input["distance"]))
        if code:
            parts.append(code)
        raw_text = " ".join(parts)

        db.add(
            Shot(
                round_id=round_.id,
                hole_id=hole.id,
                user_id=owner.id,
                shot_number=idx,
                club=shot_input["club"],
                club_normalized=shot_input["club"],
                distance=shot_input.get("distance"),
                end_lie=end_lie,
                feel_grade=shot_input["feel"],
                result_grade=shot_input["result"],
                penalty_type=code if code in {"H", "UN", "OB"} else None,
                penalty_strokes=penalty_strokes,
                score_cost=1,
                raw_text=raw_text,
            )
        )
        total_penalties += penalty_strokes

    hole.score = (len(shots) + total_penalties) if shots else None
    hole.penalties = total_penalties

    _recompute_round_totals(round_)
    db.commit()
    return _load_draft(db, owner=owner, round_id=round_id)


def finalize_draft(
    db: Session,
    *,
    owner: User,
    round_id: uuid.UUID,
    settings: Settings,
) -> tuple[Round, AnalysisJob]:
    round_ = _load_draft(db, owner=owner, round_id=round_id)

    if not (round_.course_name or "").strip():
        raise DraftValidationError("course_name is required to finalize")

    _recompute_round_totals(round_)
    db.commit()
    db.refresh(round_)

    job = enqueue_round_analysis_job(db, owner=owner, round_=round_, settings=settings)
    return round_, job


def _load_draft(db: Session, *, owner: User, round_id: uuid.UUID) -> Round:
    round_ = db.scalars(
        select(Round)
        .options(
            selectinload(Round.companions),
            selectinload(Round.holes).selectinload(Hole.shots),
        )
        .where(
            Round.id == round_id,
            Round.user_id == owner.id,
            Round.computed_status == COMPUTED_STATUS_DRAFT,
            Round.deleted_at.is_(None),
        )
    ).first()
    if round_ is None:
        raise DraftNotFoundError
    return round_


def _recompute_round_totals(round_: Round) -> None:
    holes = sorted(round_.holes, key=lambda h: h.hole_number)
    scores = [h.score for h in holes if h.score is not None]
    round_.total_score = sum(scores) if scores else None
    round_.total_par = sum(h.par for h in holes if h.par)
    round_.score_to_par = (
        round_.total_score - round_.total_par
        if round_.total_score is not None and round_.total_par is not None
        else None
    )
    round_.hole_count = len(holes)
