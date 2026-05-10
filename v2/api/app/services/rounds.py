import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Hole, Round, RoundCompanion, Shot, UploadReview, User
from app.models.constants import COMPUTED_STATUS_PENDING, COMPUTED_STATUS_STALE
from app.schemas.round import (
    DashboardSummaryResponse,
    HoleResponse,
    RoundDetailResponse,
    RoundListItem,
    RoundListResponse,
    ShotResponse,
)
from app.services.analytics import active_priority_insights
from app.services.social import SocialNotFoundError, load_viewable_round


class RoundNotFoundError(Exception):
    pass


def list_rounds(
    db: Session,
    *,
    owner: User,
    limit: int = 20,
    offset: int = 0,
    year: int | None = None,
    course: str | None = None,
    companion: str | None = None,
) -> RoundListResponse:
    base = _rounds_select(owner)
    base = _apply_round_filters(base, year=year, course=course, companion=companion)
    count_query = select(func.count()).select_from(base.order_by(None).subquery())
    total = db.scalar(count_query) or 0

    rounds = db.scalars(
        base.options(selectinload(Round.companions))
        .order_by(Round.play_date.desc(), Round.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return RoundListResponse(
        items=[_round_item(round_) for round_ in rounds],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_round_detail(db: Session, *, owner: User, round_id: uuid.UUID) -> RoundDetailResponse:
    round_ = _get_viewable_round(db, viewer=owner, round_id=round_id)
    return _round_detail(
        round_,
        viewer=owner,
        upload_review_id=_upload_review_id(db, owner=owner, round_id=round_.id)
        if round_.user_id == owner.id
        else None,
    )


def list_round_holes(db: Session, *, owner: User, round_id: uuid.UUID) -> list[HoleResponse]:
    round_ = _get_viewable_round(db, viewer=owner, round_id=round_id)
    return [
        _hole_response(hole, include_shots=True, include_raw_text=round_.user_id == owner.id)
        for hole in _sorted_holes(round_)
    ]


def list_round_shots(db: Session, *, owner: User, round_id: uuid.UUID) -> list[ShotResponse]:
    round_ = _get_viewable_round(db, viewer=owner, round_id=round_id)
    return [
        _shot_response(shot, include_raw_text=round_.user_id == owner.id)
        for hole in _sorted_holes(round_)
        for shot in sorted(hole.shots, key=lambda item: item.shot_number)
    ]


def update_round(
    db: Session,
    *,
    owner: User,
    round_id: uuid.UUID,
    values: dict,
) -> RoundDetailResponse:
    round_ = _get_round(db, owner=owner, round_id=round_id)
    changed_fields: set[str] = set()
    for field in (
        "course_name",
        "play_date",
        "tee_off_time",
        "tee",
        "weather",
        "target_score",
        "notes_private",
        "visibility",
        "share_course",
        "share_exact_date",
    ):
        if field in values:
            setattr(round_, field, values[field])
            changed_fields.add(field)
    if changed_fields & {
        "course_name",
        "play_date",
        "tee_off_time",
        "tee",
        "weather",
        "target_score",
        "notes_private",
    }:
        _mark_round_stale(round_)
    db.commit()
    db.refresh(round_)
    return _round_detail(_get_round(db, owner=owner, round_id=round_id), viewer=owner)


def delete_round(db: Session, *, owner: User, round_id: uuid.UUID) -> None:
    round_ = _get_round(db, owner=owner, round_id=round_id)
    round_.deleted_at = datetime.now(UTC)
    _mark_round_stale(round_)
    db.commit()


def request_recalculation(db: Session, *, owner: User, round_id: uuid.UUID) -> Round:
    round_ = _get_round(db, owner=owner, round_id=round_id)
    round_.computed_status = COMPUTED_STATUS_PENDING
    db.commit()
    db.refresh(round_)
    return round_


def update_hole(db: Session, *, owner: User, hole_id: uuid.UUID, values: dict) -> HoleResponse:
    hole = db.scalars(
        select(Hole)
        .join(Round)
        .options(selectinload(Hole.shots))
        .where(Hole.id == hole_id, Hole.user_id == owner.id, Round.deleted_at.is_(None))
    ).first()
    if hole is None:
        raise RoundNotFoundError

    for field in (
        "par",
        "score",
        "putts",
        "fairway_hit",
        "gir",
        "up_and_down",
        "sand_save",
        "penalties",
    ):
        if field in values:
            setattr(hole, field, values[field])
    _recompute_round_totals(hole.round)
    _mark_round_stale(hole.round)
    db.commit()
    db.refresh(hole)
    return _hole_response(hole, include_shots=True)


def update_shot(db: Session, *, owner: User, shot_id: uuid.UUID, values: dict) -> ShotResponse:
    shot = db.scalars(
        select(Shot)
        .join(Round, Shot.round_id == Round.id)
        .where(Shot.id == shot_id, Shot.user_id == owner.id, Round.deleted_at.is_(None))
    ).first()
    if shot is None:
        raise RoundNotFoundError

    for field in (
        "club",
        "club_normalized",
        "distance",
        "start_lie",
        "end_lie",
        "result_grade",
        "feel_grade",
        "penalty_type",
        "penalty_strokes",
        "score_cost",
        "raw_text",
    ):
        if field in values:
            setattr(shot, field, values[field])
    _mark_round_stale(shot.hole.round)
    db.commit()
    db.refresh(shot)
    return _shot_response(shot)


def dashboard_summary(
    db: Session,
    *,
    owner: User,
    locale: str | None = None,
) -> DashboardSummaryResponse:
    recent = list_rounds(db, owner=owner, limit=5).items
    all_rounds = db.scalars(
        _rounds_select(owner)
        .options(selectinload(Round.companions))
        .order_by(Round.play_date.asc(), Round.created_at.asc())
    ).all()

    completed = [round_ for round_ in all_rounds if round_.total_score is not None]
    average_score = (
        round(sum(round_.total_score or 0 for round_ in completed) / len(completed), 1)
        if completed
        else None
    )
    best_score = min(
        (round_.total_score for round_ in completed if round_.total_score),
        default=None,
    )
    average_putts = _average_putts(all_rounds)
    score_trend = [
        {
            "round_id": str(round_.id),
            "play_date": round_.play_date.isoformat(),
            "course_name": round_.course_name,
            "total_score": round_.total_score,
            "score_to_par": round_.score_to_par,
        }
        for round_ in completed[-10:]
    ]

    return DashboardSummaryResponse(
        kpis={
            "round_count": len(all_rounds),
            "average_score": average_score,
            "best_score": best_score,
            "average_putts": average_putts,
        },
        recent_rounds=recent,
        score_trend=score_trend,
        priority_insights=active_priority_insights(
            db,
            owner=owner,
            locale=locale,
        )
        or _priority_insights(all_rounds, average_score, locale=locale),
    )


def _rounds_select(owner: User) -> Select[tuple[Round]]:
    return select(Round).where(Round.user_id == owner.id, Round.deleted_at.is_(None))


def _apply_round_filters(
    query: Select[tuple[Round]],
    *,
    year: int | None,
    course: str | None,
    companion: str | None,
) -> Select[tuple[Round]]:
    if year is not None:
        query = query.where(func.extract("year", Round.play_date) == year)
    if course:
        query = query.where(Round.course_name.ilike(f"%{course}%"))
    if companion:
        query = query.join(RoundCompanion).where(RoundCompanion.name.ilike(f"%{companion}%"))
    return query


def _get_round(db: Session, *, owner: User, round_id: uuid.UUID) -> Round:
    round_ = db.scalars(
        select(Round)
        .options(
            selectinload(Round.companions),
            selectinload(Round.holes).selectinload(Hole.shots),
        )
        .where(Round.id == round_id, Round.user_id == owner.id, Round.deleted_at.is_(None))
    ).first()
    if round_ is None:
        raise RoundNotFoundError
    return round_


def _get_viewable_round(db: Session, *, viewer: User, round_id: uuid.UUID) -> Round:
    try:
        return load_viewable_round(db, viewer=viewer, round_id=round_id)
    except SocialNotFoundError as exc:
        raise RoundNotFoundError from exc


def _round_item(round_: Round) -> RoundListItem:
    return RoundListItem(
        id=round_.id,
        course_name=round_.course_name,
        play_date=round_.play_date,
        total_score=round_.total_score,
        total_par=round_.total_par,
        score_to_par=round_.score_to_par,
        hole_count=round_.hole_count,
        computed_status=round_.computed_status,
        visibility=round_.visibility,
        companions=[companion.name for companion in round_.companions],
    )


def _round_detail(
    round_: Round,
    *,
    viewer: User,
    upload_review_id: uuid.UUID | None = None,
) -> RoundDetailResponse:
    is_owner = round_.user_id == viewer.id
    return RoundDetailResponse(
        **_round_item(round_).model_dump(),
        upload_review_id=upload_review_id if is_owner else None,
        tee_off_time=round_.tee_off_time,
        tee=round_.tee,
        weather=round_.weather,
        target_score=round_.target_score,
        notes_private=round_.notes_private if is_owner else None,
        holes=[
            _hole_response(hole, include_shots=True, include_raw_text=is_owner)
            for hole in _sorted_holes(round_)
        ],
        insights=[],
        metrics=_round_metrics(round_),
    )


def _upload_review_id(db: Session, *, owner: User, round_id: uuid.UUID) -> uuid.UUID | None:
    return db.scalar(
        select(UploadReview.id).where(
            UploadReview.user_id == owner.id,
            UploadReview.committed_round_id == round_id,
        )
    )


def _hole_response(
    hole: Hole,
    *,
    include_shots: bool,
    include_raw_text: bool = True,
) -> HoleResponse:
    return HoleResponse(
        id=hole.id,
        round_id=hole.round_id,
        hole_number=hole.hole_number,
        par=hole.par,
        score=hole.score,
        putts=hole.putts,
        fairway_hit=hole.fairway_hit,
        gir=hole.gir,
        up_and_down=hole.up_and_down,
        sand_save=hole.sand_save,
        penalties=hole.penalties,
        shots=(
            [
                _shot_response(shot, include_raw_text=include_raw_text)
                for shot in sorted(hole.shots, key=lambda item: item.shot_number)
            ]
            if include_shots
            else []
        ),
    )


def _shot_response(shot: Shot, *, include_raw_text: bool = True) -> ShotResponse:
    return ShotResponse(
        id=shot.id,
        round_id=shot.round_id,
        hole_id=shot.hole_id,
        shot_number=shot.shot_number,
        club=shot.club,
        club_normalized=shot.club_normalized,
        distance=shot.distance,
        start_lie=shot.start_lie,
        end_lie=shot.end_lie,
        result_grade=shot.result_grade,
        feel_grade=shot.feel_grade,
        penalty_type=shot.penalty_type,
        penalty_strokes=shot.penalty_strokes,
        score_cost=shot.score_cost,
        raw_text=shot.raw_text if include_raw_text else None,
    )


def _sorted_holes(round_: Round) -> list[Hole]:
    return sorted(round_.holes, key=lambda item: item.hole_number)


def _round_metrics(round_: Round) -> dict:
    holes = _sorted_holes(round_)
    putts = [hole.putts for hole in holes if hole.putts is not None]
    gir_count = sum(1 for hole in holes if hole.gir is True)
    fairways = [hole for hole in holes if hole.fairway_hit is not None]
    fairway_hits = sum(1 for hole in fairways if hole.fairway_hit is True)
    return {
        "putts_total": sum(putts) if putts else None,
        "gir_count": gir_count,
        "fairway_hit_rate": round(fairway_hits / len(fairways), 3) if fairways else None,
        "penalties_total": sum(hole.penalties for hole in holes),
    }


def _average_putts(rounds: list[Round]) -> float | None:
    totals = []
    for round_ in rounds:
        putts = [hole.putts for hole in round_.holes if hole.putts is not None]
        if putts:
            totals.append(sum(putts))
    return round(sum(totals) / len(totals), 1) if totals else None


def _priority_insights(
    rounds: list[Round],
    average_score: float | None,
    *,
    locale: str | None = None,
) -> list[dict]:
    insights = []
    stale_count = sum(1 for round_ in rounds if round_.computed_status != "ready")
    if stale_count:
        if locale == "en":
            insights.append(
                {
                    "problem": "Analysis recalculation is pending.",
                    "evidence": f"{stale_count} rounds are not in the latest analysis state.",
                    "impact": "Dashboard KPIs are shown first from saved score data.",
                    "next_action": "Request recalculation from the round detail page.",
                    "confidence": "medium",
                }
            )
        else:
            insights.append(
                {
                    "problem": "분석 재계산 대기",
                    "evidence": f"{stale_count}개 라운드가 최신 분석 전 상태입니다.",
                    "impact": "대시보드 KPI는 저장된 스코어 기준으로 먼저 표시됩니다.",
                    "next_action": "라운드 상세에서 재계산을 요청하세요.",
                    "confidence": "medium",
                }
            )
    if average_score is not None:
        if locale == "en":
            insights.append(
                {
                    "problem": "Recent average score is available.",
                    "evidence": f"Your saved-round average score is {average_score}.",
                    "impact": "The MVP first tracks score and putting trends reliably.",
                    "next_action": "Upload more rounds, then enable shot-value analysis.",
                    "confidence": "low" if len(rounds) < 5 else "medium",
                }
            )
        else:
            insights.append(
                {
                    "problem": "최근 평균 스코어 확인",
                    "evidence": f"현재 저장된 라운드 평균은 {average_score}타입니다.",
                    "impact": "초기 MVP에서는 스코어와 퍼팅 흐름부터 안정적으로 추적합니다.",
                    "next_action": "라운드를 더 업로드한 뒤 샷 가치 분석을 활성화합니다.",
                    "confidence": "low" if len(rounds) < 5 else "medium",
                }
            )
    return insights[:3]


def _mark_round_stale(round_: Round) -> None:
    round_.computed_status = COMPUTED_STATUS_STALE


def _recompute_round_totals(round_: Round) -> None:
    holes = _sorted_holes(round_)
    scores = [hole.score for hole in holes if hole.score is not None]
    round_.hole_count = len(holes)
    round_.total_score = sum(scores) if scores else None
    round_.total_par = sum(hole.par for hole in holes) if holes else None
    round_.score_to_par = (
        round_.total_score - round_.total_par
        if round_.total_score is not None and round_.total_par is not None
        else None
    )
