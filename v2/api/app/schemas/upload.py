from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UploadRoundFileResponse(BaseModel):
    source_file_id: UUID
    upload_review_id: UUID
    status: str
    job_id: UUID


class UploadReviewResponse(BaseModel):
    id: UUID
    status: str
    parsed_round: dict[str, Any]
    warnings: list[dict[str, Any]]
    user_edits: dict[str, Any]
    committed_round_id: UUID | None
    raw_content: str | None = None


class UploadReviewUpdateRequest(BaseModel):
    user_edits: dict[str, Any] = Field(default_factory=dict)


class UploadReviewRawUpdateRequest(BaseModel):
    raw_content: str = Field(min_length=1, max_length=1_000_000)


class UploadCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    share_course: bool = False
    share_exact_date: bool = False


class UploadCommitResponse(BaseModel):
    round_id: UUID
    computed_status: str
    analytics_job_id: UUID
    analytics_job_status: str = "queued"


class JobResponse(BaseModel):
    id: UUID
    status: str
    kind: str
    resource_id: UUID
