from datetime import date, datetime
from decimal import Decimal
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


class CompanionAccountLinkCreateRequest(BaseModel):
    companion_name: str = Field(min_length=1, max_length=200)
    companion_user_id: UUID | None = None
    companion_email: str | None = Field(default=None, max_length=320)


class CompanionAccountLinkResponse(BaseModel):
    id: UUID
    companion_name: str
    companion_user_id: UUID
    companion_email: str
    companion_display_name: str
    companion_handle: str | None = None
    created_at: datetime
    updated_at: datetime


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


class SocialFeedOwnerResponse(BaseModel):
    id: UUID
    display_name: str
    handle: str | None = None


class SocialFeedLinkedRoundResponse(BaseModel):
    round_id: UUID
    course_name: str
    play_month: str


class SocialFeedTargetResponse(BaseModel):
    metric_key: str
    operator: str
    value: Decimal | None = None
    value_max: Decimal | None = None


class SocialFeedItemResponse(BaseModel):
    item_type: str
    item_id: UUID
    owner: SocialFeedOwnerResponse
    visibility: str
    social_published_at: datetime
    round_id: UUID | None = None
    course_name: str | None = None
    play_date: date | None = None
    play_month: str | None = None
    total_score: int | None = None
    score_to_par: int | None = None
    hole_count: int | None = None
    metrics: dict = Field(default_factory=dict)
    top_insight: dict | None = None
    like_count: int = 0
    comment_count: int = 0
    liked_by_me: bool = False
    viewer_can_react: bool = False
    entry_date: date | None = None
    title: str | None = None
    body_preview: str | None = None
    description: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    linked_round: SocialFeedLinkedRoundResponse | None = None
    target: SocialFeedTargetResponse | None = None
    status: str | None = None
    due_date: date | None = None
    latest_evaluation: dict | None = None


class SocialFeedMetaResponse(BaseModel):
    next_cursor: str | None = None
    has_more: bool = False
