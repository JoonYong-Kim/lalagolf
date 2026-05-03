from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.round import (
    AnalyticsCompareResponse,
    AnalyticsTrendResponse,
    DashboardSummaryResponse,
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
from app.services.analytics import (
    AnalyticsNotFoundError,
    compare_analytics,
    get_round_analytics,
    get_trends,
    list_insights,
    recalculate_round_metrics,
    update_insight_status,
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
) -> dict[str, RecalculateResponse]:
    try:
        result = recalculate_round_metrics(db, owner=current_user, round_id=round_id)
    except (RoundNotFoundError, AnalyticsNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc

    return {
        "data": RecalculateResponse(
            round_id=result["round_id"],
            computed_status=result["computed_status"],
            analytics_job_id=result["round_id"],
        )
    }


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
) -> dict[str, DashboardSummaryResponse]:
    return {"data": dashboard_summary(db, owner=current_user)}


@analytics_router.get("/analytics/trends")
def read_analytics_trends(
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, AnalyticsTrendResponse]:
    return {"data": AnalyticsTrendResponse(**get_trends(db, owner=current_user))}


@analytics_router.get("/analytics/rounds/{round_id}")
def read_round_analytics(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundAnalyticsResponse]:
    try:
        return {
            "data": RoundAnalyticsResponse(
                **get_round_analytics(db, owner=current_user, round_id=round_id)
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
) -> dict[str, list[InsightResponse]]:
    insights = list_insights(db, owner=current_user, status=status)
    return {"data": [InsightResponse(**item) for item in insights]}


@analytics_router.patch("/insights/{insight_id}")
def patch_insight(
    insight_id: UUID,
    payload: InsightUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, InsightResponse]:
    try:
        insight = update_insight_status(
            db,
            owner=current_user,
            insight_id=insight_id,
            status=payload.status,
        )
    except AnalyticsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        ) from exc
    return {"data": InsightResponse(**insight)}
