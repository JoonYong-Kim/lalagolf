from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ShareCreateRequest(BaseModel):
    round_id: UUID
    title: str | None = None
    expires_at: datetime | None = None


class ShareUpdateRequest(BaseModel):
    title: str | None = None
    expires_at: datetime | None = None
    revoked: bool | None = None


class ShareResponse(BaseModel):
    id: UUID
    round_id: UUID
    title: str | None
    url_path: str | None
    expires_at: datetime | None
    revoked_at: datetime | None
    last_accessed_at: datetime | None


class ShareCreateResponse(ShareResponse):
    token: str


class SharedRoundResponse(BaseModel):
    title: str
    round: dict
    holes: list[dict]
    metrics: dict
    insights: list[dict]
