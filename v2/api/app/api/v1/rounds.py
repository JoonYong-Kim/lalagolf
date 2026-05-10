from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.models import AnalysisJob, Round
from app.schemas.round import (
    AnalysisJobResponse,
    AnalyticsCompareResponse,
    AnalyticsTrendResponse,
    DashboardSummaryResponse,
    DraftHoleUpsertRequest,
    DraftMetaUpdate,
    HoleResponse,
    HoleUpdateRequest,
    InsightResponse,
    InsightUpdateRequest,
    RecalculateResponse,
    RoundAnalyticsResponse,
    RoundDetailResponse,
    RoundListResponse,
    RoundUpdateRequest,
    ShotResponse,
    ShotUpdateRequest,
)
from app.services.analysis_jobs import (
    AnalysisJobNotFoundError,
    enqueue_round_analysis_job,
    get_analysis_job,
    get_latest_round_analysis_job,
    retry_analysis_job,
)
from app.services.analytics import (
    AnalyticsNotFoundError,
    compare_analytics,
    get_round_analytics,
    get_trends,
    list_insights,
    update_insight_status,
)
from app.services.round_drafts import (
    DraftAlreadyExistsError,
    DraftNotFoundError,
    DraftValidationError,
    create_draft,
    discard_draft,
    finalize_draft,
    get_active_draft,
    update_draft_meta,
    upsert_hole_shots,
)
from app.services.rounds import (
    RoundNotFoundError,
    dashboard_summary,
    delete_round,
    get_round_detail,
    list_round_holes,
    list_round_shots,
    list_rounds,
    update_hole,
    update_round,
    update_shot,
)

router = APIRouter(tags=["rounds"])
analytics_router = APIRouter(tags=["analytics"])


@router.get("/rounds")
def read_rounds(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    year: int | None = Query(default=None, ge=1900, le=2200),
    course: str | None = None,
    companion: str | None = None,
) -> dict[str, RoundListResponse]:
    return {
        "data": list_rounds(
            db,
            owner=current_user,
            limit=limit,
            offset=offset,
            year=year,
            course=course,
            companion=companion,
        )
    }


@router.post("/rounds/draft", status_code=status.HTTP_201_CREATED)
def create_round_draft(
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundDetailResponse]:
    try:
        draft = create_draft(db, owner=current_user)
    except DraftAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Draft already exists", "round_id": str(exc.round_id)},
        ) from exc
    return {"data": get_round_detail(db, owner=current_user, round_id=draft.id)}


@router.get("/rounds/draft")
def read_round_draft(
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundDetailResponse]:
    draft = get_active_draft(db, owner=current_user)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active draft")
    return {"data": get_round_detail(db, owner=current_user, round_id=draft.id)}


@router.delete("/rounds/draft", status_code=status.HTTP_204_NO_CONTENT)
def remove_round_draft(db: DbSession, current_user: CurrentUser) -> None:
    draft = get_active_draft(db, owner=current_user)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active draft")
    try:
        discard_draft(db, owner=current_user, round_id=draft.id)
    except DraftNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        ) from exc


@router.patch("/rounds/{round_id}/meta")
def patch_round_draft_meta(
    round_id: UUID,
    payload: DraftMetaUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundDetailResponse]:
    try:
        update_draft_meta(
            db,
            owner=current_user,
            round_id=round_id,
            **payload.model_dump(exclude_unset=True),
        )
    except DraftNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        ) from exc
    return {"data": get_round_detail(db, owner=current_user, round_id=round_id)}


@router.patch("/rounds/{round_id}/holes/{hole_number}")
def patch_round_draft_hole(
    round_id: UUID,
    hole_number: int,
    payload: DraftHoleUpsertRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundDetailResponse]:
    try:
        upsert_hole_shots(
            db,
            owner=current_user,
            round_id=round_id,
            hole_number=hole_number,
            par=payload.par,
            shots=[shot.model_dump() for shot in payload.shots],
        )
    except DraftNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft or hole not found",
        ) from exc
    return {"data": get_round_detail(db, owner=current_user, round_id=round_id)}


@router.post("/rounds/{round_id}/finalize")
def finalize_round_draft(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> dict[str, RecalculateResponse]:
    try:
        round_, job = finalize_draft(
            db,
            owner=current_user,
            round_id=round_id,
            settings=settings,
        )
    except DraftNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        ) from exc
    except DraftValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return {
        "data": RecalculateResponse(
            round_id=round_.id,
            computed_status=round_.computed_status,
            analytics_job_id=job.id,
            analytics_job_status=job.status,
        )
    }


@router.get("/rounds/{round_id}")
def read_round(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundDetailResponse]:
    try:
        return {"data": get_round_detail(db, owner=current_user, round_id=round_id)}
    except RoundNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc


@router.patch("/rounds/{round_id}")
def patch_round(
    round_id: UUID,
    payload: RoundUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundDetailResponse]:
    try:
        return {
            "data": update_round(
                db,
                owner=current_user,
                round_id=round_id,
                values=payload.model_dump(exclude_unset=True),
            )
        }
    except RoundNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc


@router.delete("/rounds/{round_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_round(round_id: UUID, db: DbSession, current_user: CurrentUser) -> None:
    try:
        delete_round(db, owner=current_user, round_id=round_id)
    except RoundNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc


@router.post("/rounds/{round_id}/recalculate")
def recalculate_round(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> dict[str, RecalculateResponse]:
    round_ = db.get(Round, round_id)
    if round_ is None or round_.user_id != current_user.id or round_.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        )
    job = enqueue_round_analysis_job(db, owner=current_user, round_=round_, settings=settings)

    return {
        "data": RecalculateResponse(
            round_id=round_.id,
            computed_status=round_.computed_status,
            analytics_job_id=job.id,
            analytics_job_status=job.status,
        )
    }


@router.get("/analysis-jobs/{job_id}")
def read_analysis_job(
    job_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, AnalysisJobResponse]:
    try:
        job = get_analysis_job(db, owner=current_user, job_id=job_id)
    except AnalysisJobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    return {"data": _analysis_job_response(job)}


@router.post("/analysis-jobs/{job_id}/retry")
def retry_failed_analysis_job(
    job_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> dict[str, AnalysisJobResponse]:
    try:
        job = retry_analysis_job(db, owner=current_user, job_id=job_id, settings=settings)
    except AnalysisJobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    return {"data": _analysis_job_response(job)}


@router.get("/rounds/{round_id}/analysis-job")
def read_latest_round_analysis_job(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, AnalysisJobResponse]:
    round_ = db.get(Round, round_id)
    if round_ is None or round_.user_id != current_user.id or round_.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        )
    try:
        job = get_latest_round_analysis_job(db, owner=current_user, round_id=round_id)
    except AnalysisJobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    return {"data": _analysis_job_response(job)}


def _analysis_job_response(job: AnalysisJob) -> AnalysisJobResponse:
    return AnalysisJobResponse(
        id=job.id,
        round_id=job.round_id,
        kind=job.kind,
        status=job.status,
        rq_job_id=job.rq_job_id,
        attempts=job.attempts,
        error_message=job.error_message,
        payload=job.payload,
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
    )


@router.get("/rounds/{round_id}/holes")
def read_round_holes(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, list[HoleResponse]]:
    try:
        return {"data": list_round_holes(db, owner=current_user, round_id=round_id)}
    except RoundNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc


@router.get("/rounds/{round_id}/shots")
def read_round_shots(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, list[ShotResponse]]:
    try:
        return {"data": list_round_shots(db, owner=current_user, round_id=round_id)}
    except RoundNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc


@router.patch("/holes/{hole_id}")
def patch_hole(
    hole_id: UUID,
    payload: HoleUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, HoleResponse]:
    try:
        return {
            "data": update_hole(
                db,
                owner=current_user,
                hole_id=hole_id,
                values=payload.model_dump(exclude_unset=True),
            )
        }
    except RoundNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hole not found") from exc


@router.patch("/shots/{shot_id}")
def patch_shot(
    shot_id: UUID,
    payload: ShotUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, ShotResponse]:
    try:
        return {
            "data": update_shot(
                db,
                owner=current_user,
                shot_id=shot_id,
                values=payload.model_dump(exclude_unset=True),
            )
        }
    except RoundNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shot not found") from exc


@analytics_router.get("/analytics/summary")
def read_dashboard_summary(
    db: DbSession,
    current_user: CurrentUser,
    locale: str = Query(default="ko", pattern="^(ko|en)$"),
) -> dict[str, DashboardSummaryResponse]:
    return {"data": dashboard_summary(db, owner=current_user, locale=locale)}


@analytics_router.get("/analytics/trends")
def read_analytics_trends(
    db: DbSession,
    current_user: CurrentUser,
    locale: str = Query(default="ko", pattern="^(ko|en)$"),
) -> dict[str, AnalyticsTrendResponse]:
    return {"data": AnalyticsTrendResponse(**get_trends(db, owner=current_user, locale=locale))}


@analytics_router.get("/analytics/rounds/{round_id}")
def read_round_analytics(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    locale: str = Query(default="ko", pattern="^(ko|en)$"),
) -> dict[str, RoundAnalyticsResponse]:
    try:
        return {
            "data": RoundAnalyticsResponse(
                **get_round_analytics(db, owner=current_user, round_id=round_id, locale=locale)
            )
        }
    except AnalyticsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc


@analytics_router.get("/analytics/compare")
def read_analytics_compare(
    db: DbSession,
    current_user: CurrentUser,
    group_by: str = "category",
) -> dict[str, AnalyticsCompareResponse]:
    return {
        "data": AnalyticsCompareResponse(
            **compare_analytics(db, owner=current_user, group_by=group_by)
        )
    }


@analytics_router.get("/insights")
def read_insights(
    db: DbSession,
    current_user: CurrentUser,
    status: str = "active",
    locale: str = Query(default="ko", pattern="^(ko|en)$"),
) -> dict[str, list[InsightResponse]]:
    insights = list_insights(db, owner=current_user, status=status, locale=locale)
    return {"data": [InsightResponse(**item) for item in insights]}


@analytics_router.patch("/insights/{insight_id}")
def patch_insight(
    insight_id: UUID,
    payload: InsightUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
    locale: str = Query(default="ko", pattern="^(ko|en)$"),
) -> dict[str, InsightResponse]:
    try:
        insight = update_insight_status(
            db,
            owner=current_user,
            insight_id=insight_id,
            status=payload.status,
            locale=locale,
        )
    except AnalyticsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        ) from exc
    return {"data": InsightResponse(**insight)}
