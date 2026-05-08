from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class CompanionResponse(BaseModel):
    id: UUID
    name: str


class ShotResponse(BaseModel):
    id: UUID
    round_id: UUID
    hole_id: UUID
    shot_number: int
    club: str | None
    club_normalized: str | None
    distance: int | None
    start_lie: str | None
    end_lie: str | None
    result_grade: str | None
    feel_grade: str | None
    penalty_type: str | None
    penalty_strokes: int
    score_cost: int
    raw_text: str | None


class HoleResponse(BaseModel):
    id: UUID
    round_id: UUID
    hole_number: int
    par: int
    score: int | None
    putts: int | None
    fairway_hit: bool | None
    gir: bool | None
    up_and_down: bool | None
    sand_save: bool | None
    penalties: int
    shots: list[ShotResponse] = Field(default_factory=list)


class RoundListItem(BaseModel):
    id: UUID
    course_name: str
    play_date: date
    total_score: int | None
    total_par: int | None
    score_to_par: int | None
    hole_count: int
    computed_status: str
    companions: list[str] = Field(default_factory=list)


class RoundListResponse(BaseModel):
    items: list[RoundListItem]
    total: int
    limit: int
    offset: int


class RoundDetailResponse(RoundListItem):
    upload_review_id: UUID | None = None
    tee: str | None
    weather: str | None
    target_score: int | None
    visibility: str
    notes_private: str | None
    holes: list[HoleResponse] = Field(default_factory=list)
    insights: list[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class RoundUpdateRequest(BaseModel):
    course_name: str | None = None
    play_date: date | None = None
    tee: str | None = None
    weather: str | None = None
    target_score: int | None = None
    notes_private: str | None = None


class HoleUpdateRequest(BaseModel):
    par: int | None = None
    score: int | None = None
    putts: int | None = None
    fairway_hit: bool | None = None
    gir: bool | None = None
    up_and_down: bool | None = None
    sand_save: bool | None = None
    penalties: int | None = None


class ShotUpdateRequest(BaseModel):
    club: str | None = None
    club_normalized: str | None = None
    distance: int | None = None
    start_lie: str | None = None
    end_lie: str | None = None
    result_grade: str | None = None
    feel_grade: str | None = None
    penalty_type: str | None = None
    penalty_strokes: int | None = None
    score_cost: int | None = None
    raw_text: str | None = None


class RecalculateResponse(BaseModel):
    round_id: UUID
    computed_status: str
    analytics_job_id: UUID


class DashboardSummaryResponse(BaseModel):
    kpis: dict
    recent_rounds: list[RoundListItem]
    score_trend: list[dict]
    priority_insights: list[dict]


class InsightResponse(BaseModel):
    id: UUID
    round_id: UUID | None
    scope_type: str
    scope_key: str
    category: str
    root_cause: str
    primary_evidence_metric: str
    dedupe_key: str
    problem: str
    evidence: str
    impact: str
    next_action: str
    confidence: str
    priority_score: float
    status: str


class InsightUpdateRequest(BaseModel):
    status: str


class AnalyticsTrendResponse(BaseModel):
    kpis: dict
    score_trend: list[dict]
    category_summary: list[dict]
    shot_quality_summary: dict = Field(default_factory=dict)
    insights: list[InsightResponse]


class RoundAnalyticsResponse(BaseModel):
    round_id: UUID
    metrics: dict
    shot_quality_summary: dict = Field(default_factory=dict)
    shot_values: list[dict]
    insights: list[InsightResponse]


class AnalyticsCompareResponse(BaseModel):
    group_by: str
    rows: list[dict]
