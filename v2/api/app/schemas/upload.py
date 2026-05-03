from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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


class UploadReviewUpdateRequest(BaseModel):
    user_edits: dict[str, Any] = Field(default_factory=dict)


class UploadCommitRequest(BaseModel):
    visibility: str = "private"
    share_course: bool = False
    share_exact_date: bool = False


class UploadCommitResponse(BaseModel):
    round_id: UUID
    computed_status: str
    analytics_job_id: UUID


class JobResponse(BaseModel):
    id: UUID
    status: str
    kind: str
    resource_id: UUID
