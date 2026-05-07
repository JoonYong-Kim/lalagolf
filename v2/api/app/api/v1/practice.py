from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.practice import (
    GoalEvaluationRequest,
    GoalEvaluationResponse,
    ManualGoalEvaluationRequest,
    PracticeDiaryCreateRequest,
    PracticeDiaryResponse,
    PracticePlanCreateRequest,
    PracticePlanResponse,
    PracticePlanUpdateRequest,
    RoundGoalCreateRequest,
    RoundGoalResponse,
    RoundGoalUpdateRequest,
)
from app.services.practice import (
    PracticeNotFoundError,
    PracticeValidationError,
    create_diary_entry,
    create_goal,
    create_manual_evaluation,
    create_practice_plan,
    evaluate_goal,
    list_diary_entries,
    list_goals,
    list_practice_plans,
    update_goal,
    update_practice_plan,
)

router = APIRouter(tags=["practice"])
OptionalUuidQuery = Annotated[UUID | None, Query()]


@router.get("/practice/plans")
def read_practice_plans(
    db: DbSession,
    current_user: CurrentUser,
    status: str | None = None,
    category: str | None = None,
) -> dict[str, list[PracticePlanResponse]]:
    plans = list_practice_plans(db, owner=current_user, status=status, category=category)
    return {"data": [PracticePlanResponse(**plan) for plan in plans]}


@router.post("/practice/plans", status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PracticePlanCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, PracticePlanResponse]:
    try:
        plan = create_practice_plan(
            db,
            owner=current_user,
            values=payload.model_dump(exclude_unset=True),
        )
    except PracticeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        ) from exc
    return {"data": PracticePlanResponse(**plan)}


@router.patch("/practice/plans/{plan_id}")
def patch_plan(
    plan_id: UUID,
    payload: PracticePlanUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, PracticePlanResponse]:
    try:
        plan = update_practice_plan(
            db,
            owner=current_user,
            plan_id=plan_id,
            values=payload.model_dump(exclude_unset=True),
        )
    except PracticeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found") from exc
    except PracticeValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"data": PracticePlanResponse(**plan)}


@router.get("/practice/diary")
def read_diary_entries(
    db: DbSession,
    current_user: CurrentUser,
    practice_plan_id: OptionalUuidQuery = None,
    category: str | None = None,
) -> dict[str, list[PracticeDiaryResponse]]:
    entries = list_diary_entries(
        db,
        owner=current_user,
        practice_plan_id=practice_plan_id,
        category=category,
    )
    return {"data": [PracticeDiaryResponse(**entry) for entry in entries]}


@router.post("/practice/diary", status_code=status.HTTP_201_CREATED)
def create_diary(
    payload: PracticeDiaryCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, PracticeDiaryResponse]:
    try:
        entry = create_diary_entry(
            db,
            owner=current_user,
            values=payload.model_dump(exclude_unset=True),
        )
    except PracticeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        ) from exc
    return {"data": PracticeDiaryResponse(**entry)}


@router.get("/goals")
def read_goals(
    db: DbSession,
    current_user: CurrentUser,
    status: str | None = None,
    category: str | None = None,
) -> dict[str, list[RoundGoalResponse]]:
    goals = list_goals(db, owner=current_user, status=status, category=category)
    return {"data": [RoundGoalResponse(**goal) for goal in goals]}


@router.post("/goals", status_code=status.HTTP_201_CREATED)
def create_round_goal(
    payload: RoundGoalCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundGoalResponse]:
    try:
        goal = create_goal(db, owner=current_user, values=payload.model_dump(exclude_unset=True))
    except PracticeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        ) from exc
    return {"data": RoundGoalResponse(**goal)}


@router.patch("/goals/{goal_id}")
def patch_goal(
    goal_id: UUID,
    payload: RoundGoalUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundGoalResponse]:
    try:
        goal = update_goal(
            db,
            owner=current_user,
            goal_id=goal_id,
            values=payload.model_dump(exclude_unset=True),
        )
    except PracticeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found") from exc
    except PracticeValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"data": RoundGoalResponse(**goal)}


@router.post("/goals/{goal_id}/evaluate")
def evaluate_round_goal(
    goal_id: UUID,
    payload: GoalEvaluationRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, GoalEvaluationResponse]:
    try:
        evaluation = evaluate_goal(
            db,
            owner=current_user,
            goal_id=goal_id,
            round_id=payload.round_id,
        )
    except PracticeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found") from exc
    return {"data": GoalEvaluationResponse(**evaluation)}


@router.post("/goals/{goal_id}/manual-evaluation", status_code=status.HTTP_201_CREATED)
def manually_evaluate_goal(
    goal_id: UUID,
    payload: ManualGoalEvaluationRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, GoalEvaluationResponse]:
    try:
        evaluation = create_manual_evaluation(
            db,
            owner=current_user,
            goal_id=goal_id,
            round_id=payload.round_id,
            evaluation_status=payload.evaluation_status,
            note=payload.note,
        )
    except PracticeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found") from exc
    except PracticeValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"data": GoalEvaluationResponse(**evaluation)}
