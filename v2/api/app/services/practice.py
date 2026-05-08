import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    GoalEvaluation,
    Hole,
    Insight,
    PracticeDiaryEntry,
    PracticePlan,
    Round,
    RoundGoal,
    User,
)

PLAN_STATUSES = {"planned", "in_progress", "done", "skipped"}
GOAL_STATUSES = {"active", "achieved", "missed", "partial", "not_evaluable", "cancelled"}
EVALUATION_STATUSES = {"achieved", "missed", "partial", "not_evaluable"}
SUPPORTED_METRICS = {
    "score_to_par",
    "total_score",
    "putts_total",
    "three_putt_holes",
    "penalties_total",
    "tee_penalties",
    "gir_count",
    "fairway_miss_count",
    "driver_result_c_count",
    "strategy_issue_count",
}


class PracticeNotFoundError(Exception):
    pass


class PracticeValidationError(Exception):
    pass


def list_practice_plans(
    db: Session,
    *,
    owner: User,
    status: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    query = select(PracticePlan).where(PracticePlan.user_id == owner.id)
    if status:
        query = query.where(PracticePlan.status == status)
    if category:
        query = query.where(PracticePlan.category == category)
    plans = db.scalars(
        query.order_by(PracticePlan.scheduled_for.asc(), PracticePlan.created_at.desc())
    ).all()
    return [_practice_plan_response(plan) for plan in plans]


def create_practice_plan(
    db: Session,
    *,
    owner: User,
    values: dict[str, Any],
) -> dict[str, Any]:
    insight = _optional_insight(db, owner=owner, insight_id=values.get("source_insight_id"))
    category = values.get("category") or (insight.category if insight else "score")
    plan = PracticePlan(
        user_id=owner.id,
        source_insight_id=insight.id if insight else None,
        title=str(values["title"]),
        purpose=values.get("purpose") or (insight.next_action if insight else None),
        category=category,
        root_cause=insight.root_cause if insight else None,
        drill_json=values.get("drill_json") or _default_drill(insight),
        target_json=values.get("target_json") or {},
        scheduled_for=values.get("scheduled_for"),
        status="planned",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _practice_plan_response(plan)


def update_practice_plan(
    db: Session,
    *,
    owner: User,
    plan_id: uuid.UUID,
    values: dict[str, Any],
) -> dict[str, Any]:
    plan = _practice_plan(db, owner=owner, plan_id=plan_id)
    if "status" in values and values["status"] not in PLAN_STATUSES:
        raise PracticeValidationError("Invalid practice plan status")
    for field in (
        "title",
        "purpose",
        "category",
        "scheduled_for",
        "drill_json",
        "target_json",
        "status",
        "completed_at",
    ):
        if field in values:
            setattr(plan, field, values[field])
    if plan.status == "done" and plan.completed_at is None:
        plan.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(plan)
    return _practice_plan_response(plan)


def list_diary_entries(
    db: Session,
    *,
    owner: User,
    practice_plan_id: uuid.UUID | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    query = select(PracticeDiaryEntry).where(PracticeDiaryEntry.user_id == owner.id)
    if practice_plan_id:
        query = query.where(PracticeDiaryEntry.practice_plan_id == practice_plan_id)
    if category:
        query = query.where(PracticeDiaryEntry.category == category)
    entries = db.scalars(
        query.order_by(PracticeDiaryEntry.entry_date.desc(), PracticeDiaryEntry.created_at.desc())
    ).all()
    return [_diary_response(entry) for entry in entries]


def create_diary_entry(
    db: Session,
    *,
    owner: User,
    values: dict[str, Any],
) -> dict[str, Any]:
    plan = _optional_plan(db, owner=owner, plan_id=values.get("practice_plan_id"))
    insight = _optional_insight(db, owner=owner, insight_id=values.get("source_insight_id"))
    if values.get("round_id") is not None:
        _round(db, owner=owner, round_id=values["round_id"])
    entry = PracticeDiaryEntry(
        user_id=owner.id,
        practice_plan_id=plan.id if plan else None,
        source_insight_id=insight.id if insight else None,
        round_id=values.get("round_id"),
        entry_date=values["entry_date"],
        title=str(values["title"]),
        body=str(values["body"]),
        category=values.get("category") or (plan.category if plan else None),
        tags=values.get("tags") or [],
        confidence=values.get("confidence"),
        mood=values.get("mood"),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _diary_response(entry)


def list_goals(
    db: Session,
    *,
    owner: User,
    status: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    query = select(RoundGoal).where(RoundGoal.user_id == owner.id)
    if status:
        query = query.where(RoundGoal.status == status)
    if category:
        query = query.where(RoundGoal.category == category)
    goals = db.scalars(query.order_by(RoundGoal.created_at.desc())).all()
    return [_goal_response(goal) for goal in goals]


def create_goal(db: Session, *, owner: User, values: dict[str, Any]) -> dict[str, Any]:
    insight = _optional_insight(db, owner=owner, insight_id=values.get("source_insight_id"))
    plan = _optional_plan(db, owner=owner, plan_id=values.get("practice_plan_id"))
    if values.get("due_round_id") is not None:
        _round(db, owner=owner, round_id=values["due_round_id"])
    category = values.get("category") or (plan.category if plan else None) or (
        insight.category if insight else "score"
    )
    goal = RoundGoal(
        user_id=owner.id,
        source_insight_id=insight.id if insight else None,
        practice_plan_id=plan.id if plan else None,
        title=str(values["title"]),
        description=values.get("description"),
        category=category,
        metric_key=str(values["metric_key"]),
        target_operator=str(values["target_operator"]),
        target_value=values.get("target_value"),
        target_value_max=values.get("target_value_max"),
        target_json=values.get("target_json") or {},
        applies_to=values.get("applies_to") or "next_round",
        due_round_id=values.get("due_round_id"),
        due_date=values.get("due_date"),
        status="active",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _goal_response(goal)


def update_goal(
    db: Session,
    *,
    owner: User,
    goal_id: uuid.UUID,
    values: dict[str, Any],
) -> dict[str, Any]:
    goal = _goal(db, owner=owner, goal_id=goal_id)
    if "status" in values and values["status"] not in GOAL_STATUSES:
        raise PracticeValidationError("Invalid goal status")
    if "due_round_id" in values and values["due_round_id"] is not None:
        _round(db, owner=owner, round_id=values["due_round_id"])
    for field in (
        "title",
        "description",
        "category",
        "metric_key",
        "target_operator",
        "target_value",
        "target_value_max",
        "target_json",
        "applies_to",
        "due_round_id",
        "due_date",
        "status",
    ):
        if field in values:
            setattr(goal, field, values[field])
    if goal.status != "active" and goal.closed_at is None:
        goal.closed_at = datetime.now(UTC)
    db.commit()
    db.refresh(goal)
    return _goal_response(goal)


def evaluate_goal(
    db: Session,
    *,
    owner: User,
    goal_id: uuid.UUID,
    round_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    goal = _goal(db, owner=owner, goal_id=goal_id)
    round_ = (
        _round(db, owner=owner, round_id=round_id)
        if round_id
        else _eligible_round(db, owner, goal)
    )
    actual_value = _metric_value(goal.metric_key, round_) if round_ else None
    if actual_value is None:
        status = "not_evaluable"
    else:
        status = "achieved" if _target_met(goal, actual_value) else "missed"
    evaluation = _record_evaluation(
        db,
        owner=owner,
        goal=goal,
        round_=round_,
        status=status,
        actual_value=actual_value,
        actual_json={
            "metric_key": goal.metric_key,
            "target": _target_label(goal),
            "supported": goal.metric_key in SUPPORTED_METRICS,
        },
        evaluated_by="system",
        note=None,
    )
    _close_goal_if_needed(goal, status)
    db.commit()
    db.refresh(evaluation)
    return _evaluation_response(evaluation)


def create_manual_evaluation(
    db: Session,
    *,
    owner: User,
    goal_id: uuid.UUID,
    round_id: uuid.UUID | None,
    evaluation_status: str,
    note: str | None,
) -> dict[str, Any]:
    if evaluation_status not in EVALUATION_STATUSES:
        raise PracticeValidationError("Invalid evaluation status")
    goal = _goal(db, owner=owner, goal_id=goal_id)
    round_ = _round(db, owner=owner, round_id=round_id) if round_id else None
    evaluation = _record_evaluation(
        db,
        owner=owner,
        goal=goal,
        round_=round_,
        status=evaluation_status,
        actual_value=None,
        actual_json={"manual": True},
        evaluated_by="user",
        note=note,
    )
    _close_goal_if_needed(goal, evaluation_status)
    db.commit()
    db.refresh(evaluation)
    return _evaluation_response(evaluation)


def _record_evaluation(
    db: Session,
    *,
    owner: User,
    goal: RoundGoal,
    round_: Round | None,
    status: str,
    actual_value: Decimal | None,
    actual_json: dict[str, Any],
    evaluated_by: str,
    note: str | None,
) -> GoalEvaluation:
    evaluation = GoalEvaluation(
        user_id=owner.id,
        goal_id=goal.id,
        round_id=round_.id if round_ else None,
        evaluation_status=status,
        actual_value=actual_value,
        actual_json=actual_json,
        evaluated_by=evaluated_by,
        note=note,
        evaluated_at=datetime.now(UTC),
    )
    db.add(evaluation)
    return evaluation


def _close_goal_if_needed(goal: RoundGoal, status: str) -> None:
    if goal.applies_to == "next_round" and status in EVALUATION_STATUSES:
        goal.status = status
        goal.closed_at = datetime.now(UTC)


def _metric_value(metric_key: str, round_: Round | None) -> Decimal | None:
    if round_ is None or metric_key not in SUPPORTED_METRICS:
        return None
    holes = list(round_.holes)
    if metric_key == "score_to_par":
        return _decimal(round_.score_to_par)
    if metric_key == "total_score":
        return _decimal(round_.total_score)
    if metric_key == "putts_total":
        putts = [hole.putts for hole in holes if hole.putts is not None]
        return Decimal(sum(putts)) if putts else None
    if metric_key == "three_putt_holes":
        return Decimal(sum(1 for hole in holes if (hole.putts or 0) >= 3))
    if metric_key == "penalties_total":
        return Decimal(sum(hole.penalties for hole in holes))
    if metric_key == "tee_penalties":
        return Decimal(
            sum(
                shot.penalty_strokes or 0
                for hole in holes
                for shot in hole.shots
                if shot.shot_number == 1
            )
        )
    if metric_key == "gir_count":
        return Decimal(sum(1 for hole in holes if hole.gir is True))
    if metric_key == "fairway_miss_count":
        fairways = [hole for hole in holes if hole.fairway_hit is not None]
        return Decimal(sum(1 for hole in fairways if hole.fairway_hit is False))
    if metric_key == "driver_result_c_count":
        return Decimal(
            sum(
                1
                for hole in holes
                for shot in hole.shots
                if shot.shot_number == 1
                and hole.par in {4, 5}
                and (shot.club_normalized or shot.club or "").upper() == "D"
                and (shot.result_grade or "").upper() == "C"
            )
        )
    if metric_key == "strategy_issue_count":
        return Decimal(
            sum(
                1
                for hole in holes
                for shot in hole.shots
                if (shot.feel_grade or "").upper() in {"A", "B"}
                and (shot.result_grade or "").upper() == "C"
            )
        )
    return None


def _target_met(goal: RoundGoal, actual_value: Decimal) -> bool:
    target = goal.target_value
    target_max = goal.target_value_max
    if target is None:
        return False
    if goal.target_operator == "<=":
        return actual_value <= target
    if goal.target_operator == "<":
        return actual_value < target
    if goal.target_operator == ">=":
        return actual_value >= target
    if goal.target_operator == ">":
        return actual_value > target
    if goal.target_operator == "=":
        return actual_value == target
    if goal.target_operator == "between" and target_max is not None:
        return target <= actual_value <= target_max
    return False


def _target_label(goal: RoundGoal) -> str:
    if goal.target_operator == "between":
        return f"between {goal.target_value} and {goal.target_value_max}"
    return f"{goal.target_operator} {goal.target_value}"


def _eligible_round(db: Session, owner: User, goal: RoundGoal) -> Round | None:
    if goal.due_round_id:
        return _round(db, owner=owner, round_id=goal.due_round_id)
    return db.scalars(
        select(Round)
        .options(selectinload(Round.holes).selectinload(Hole.shots))
        .where(
            Round.user_id == owner.id,
            Round.deleted_at.is_(None),
            Round.created_at >= goal.created_at,
        )
        .order_by(Round.play_date.asc(), Round.created_at.asc())
    ).first()


def _round(db: Session, *, owner: User, round_id: uuid.UUID) -> Round:
    round_ = db.scalars(
        select(Round)
        .options(selectinload(Round.holes).selectinload(Hole.shots))
        .where(Round.id == round_id, Round.user_id == owner.id, Round.deleted_at.is_(None))
    ).first()
    if round_ is None:
        raise PracticeNotFoundError
    return round_


def _optional_insight(
    db: Session,
    *,
    owner: User,
    insight_id: uuid.UUID | None,
) -> Insight | None:
    if insight_id is None:
        return None
    insight = db.scalars(
        select(Insight).where(Insight.id == insight_id, Insight.user_id == owner.id)
    ).first()
    if insight is None:
        raise PracticeNotFoundError
    return insight


def _optional_plan(
    db: Session,
    *,
    owner: User,
    plan_id: uuid.UUID | None,
) -> PracticePlan | None:
    if plan_id is None:
        return None
    return _practice_plan(db, owner=owner, plan_id=plan_id)


def _practice_plan(db: Session, *, owner: User, plan_id: uuid.UUID) -> PracticePlan:
    plan = db.scalars(
        select(PracticePlan).where(PracticePlan.id == plan_id, PracticePlan.user_id == owner.id)
    ).first()
    if plan is None:
        raise PracticeNotFoundError
    return plan


def _goal(db: Session, *, owner: User, goal_id: uuid.UUID) -> RoundGoal:
    goal = db.scalars(
        select(RoundGoal).where(RoundGoal.id == goal_id, RoundGoal.user_id == owner.id)
    ).first()
    if goal is None:
        raise PracticeNotFoundError
    return goal


def _default_drill(insight: Insight | None) -> dict[str, Any]:
    if insight is None:
        return {}
    return {
        "source": "insight",
        "next_action": insight.next_action,
        "category": insight.category,
    }


def _decimal(value: int | float | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


def _practice_plan_response(plan: PracticePlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "source_insight_id": plan.source_insight_id,
        "title": plan.title,
        "purpose": plan.purpose,
        "category": plan.category,
        "root_cause": plan.root_cause,
        "drill_json": plan.drill_json,
        "target_json": plan.target_json,
        "scheduled_for": plan.scheduled_for,
        "status": plan.status,
        "completed_at": plan.completed_at,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


def _diary_response(entry: PracticeDiaryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "practice_plan_id": entry.practice_plan_id,
        "source_insight_id": entry.source_insight_id,
        "round_id": entry.round_id,
        "entry_date": entry.entry_date,
        "title": entry.title,
        "body": entry.body,
        "category": entry.category,
        "tags": entry.tags,
        "confidence": entry.confidence,
        "mood": entry.mood,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


def _goal_response(goal: RoundGoal) -> dict[str, Any]:
    return {
        "id": goal.id,
        "source_insight_id": goal.source_insight_id,
        "practice_plan_id": goal.practice_plan_id,
        "title": goal.title,
        "description": goal.description,
        "category": goal.category,
        "metric_key": goal.metric_key,
        "target_operator": goal.target_operator,
        "target_value": goal.target_value,
        "target_value_max": goal.target_value_max,
        "target_json": goal.target_json,
        "applies_to": goal.applies_to,
        "due_round_id": goal.due_round_id,
        "due_date": goal.due_date,
        "status": goal.status,
        "closed_at": goal.closed_at,
        "created_at": goal.created_at,
        "updated_at": goal.updated_at,
    }


def _evaluation_response(evaluation: GoalEvaluation) -> dict[str, Any]:
    return {
        "id": evaluation.id,
        "goal_id": evaluation.goal_id,
        "round_id": evaluation.round_id,
        "evaluation_status": evaluation.evaluation_status,
        "actual_value": evaluation.actual_value,
        "actual_json": evaluation.actual_json,
        "evaluated_by": evaluation.evaluated_by,
        "note": evaluation.note,
        "evaluated_at": evaluation.evaluated_at,
        "created_at": evaluation.created_at,
    }
