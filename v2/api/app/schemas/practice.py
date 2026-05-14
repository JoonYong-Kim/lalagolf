from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PracticePlanCreateRequest(BaseModel):
    source_insight_id: UUID | None = None
    title: str
    purpose: str | None = None
    category: str | None = None
    scheduled_for: date | None = None
    drill_json: dict = Field(default_factory=dict)
    target_json: dict = Field(default_factory=dict)


class PracticePlanUpdateRequest(BaseModel):
    title: str | None = None
    purpose: str | None = None
    category: str | None = None
    scheduled_for: date | None = None
    drill_json: dict | None = None
    target_json: dict | None = None
    status: str | None = None
    completed_at: datetime | None = None


class PracticePlanResponse(BaseModel):
    id: UUID
    source_insight_id: UUID | None
    title: str
    purpose: str | None
    category: str
    root_cause: str | None
    drill_json: dict
    target_json: dict
    scheduled_for: date | None
    status: str
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PracticeDiaryCreateRequest(BaseModel):
    practice_plan_id: UUID | None = None
    source_insight_id: UUID | None = None
    round_id: UUID | None = None
    entry_date: date
    title: str
    body: str
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: str | None = None
    mood: str | None = None
    visibility: str | None = Field(default=None, pattern="^(private|followers|public)$")


class PracticeDiaryUpdateRequest(BaseModel):
    entry_date: date | None = None
    title: str | None = None
    body: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    confidence: str | None = None
    mood: str | None = None
    visibility: str | None = Field(default=None, pattern="^(private|followers|public)$")


class PracticeDiaryResponse(BaseModel):
    id: UUID
    practice_plan_id: UUID | None
    source_insight_id: UUID | None
    round_id: UUID | None
    entry_date: date
    title: str
    body: str
    category: str | None
    tags: list[str]
    confidence: str | None
    mood: str | None
    visibility: str
    social_published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RoundGoalCreateRequest(BaseModel):
    source_insight_id: UUID | None = None
    practice_plan_id: UUID | None = None
    title: str
    description: str | None = None
    category: str | None = None
    metric_key: str
    target_operator: str
    target_value: Decimal | None = None
    target_value_max: Decimal | None = None
    target_json: dict = Field(default_factory=dict)
    applies_to: str = "next_round"
    due_round_id: UUID | None = None
    due_date: date | None = None
    visibility: str | None = Field(default=None, pattern="^(private|followers|public)$")


class RoundGoalUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    metric_key: str | None = None
    target_operator: str | None = None
    target_value: Decimal | None = None
    target_value_max: Decimal | None = None
    target_json: dict | None = None
    applies_to: str | None = None
    due_round_id: UUID | None = None
    due_date: date | None = None
    status: str | None = None
    visibility: str | None = Field(default=None, pattern="^(private|followers|public)$")


class RoundGoalResponse(BaseModel):
    id: UUID
    source_insight_id: UUID | None
    practice_plan_id: UUID | None
    title: str
    description: str | None
    category: str
    metric_key: str
    target_operator: str
    target_value: Decimal | None
    target_value_max: Decimal | None
    target_json: dict
    applies_to: str
    due_round_id: UUID | None
    due_date: date | None
    status: str
    visibility: str
    social_published_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GoalEvaluationRequest(BaseModel):
    round_id: UUID | None = None


class ManualGoalEvaluationRequest(BaseModel):
    round_id: UUID | None = None
    evaluation_status: str
    note: str | None = None


class GoalEvaluationResponse(BaseModel):
    id: UUID
    goal_id: UUID
    round_id: UUID | None
    evaluation_status: str
    actual_value: Decimal | None
    actual_json: dict
    evaluated_by: str
    note: str | None
    evaluated_at: datetime
    created_at: datetime
