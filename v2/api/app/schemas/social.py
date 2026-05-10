from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PublicShotResponse(BaseModel):
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


class PublicHoleResponse(BaseModel):
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
    shots: list[PublicShotResponse] = Field(default_factory=list)


class PublicRoundCardResponse(BaseModel):
    id: UUID
    owner_id: UUID
    owner_display_name: str
    owner_handle: str | None
    course_name: str
    play_date: date
    total_score: int | None
    total_par: int | None
    score_to_par: int | None
    hole_count: int
    visibility: str
    notes_public: str | None = None


class PublicRoundDetailResponse(PublicRoundCardResponse):
    tee_off_time: str | None = None
    tee: str | None = None
    weather: str | None = None
    target_score: int | None = None
    metrics: dict = Field(default_factory=dict)
    holes: list[PublicHoleResponse] = Field(default_factory=list)
    insights: list[dict] = Field(default_factory=list)
    like_count: int = 0
    comment_count: int = 0


class FollowCreateRequest(BaseModel):
    following_id: UUID


class FollowStatusUpdateRequest(BaseModel):
    status: str


class FollowResponse(BaseModel):
    follower_id: UUID
    following_id: UUID
    status: str
    requested_at: datetime
    accepted_at: datetime | None = None
    blocked_at: datetime | None = None
    follower_display_name: str | None = None
    follower_handle: str | None = None
    following_display_name: str | None = None
    following_handle: str | None = None


class RoundLikeResponse(BaseModel):
    round_id: UUID
    like_count: int
    liked: bool


class RoundCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_comment_id: UUID | None = None


class RoundCommentResponse(BaseModel):
    id: UUID
    round_id: UUID
    user_id: UUID
    parent_comment_id: UUID | None = None
    body: str
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    author_display_name: str | None = None
    author_handle: str | None = None


class CompareCandidateResponse(BaseModel):
    round_id: UUID
    course_name: str
    play_date: str
    tee_off_time: str | None = None
    companion_name: str
    visibility: str
    owner_display_name: str
    owner_handle: str | None = None
