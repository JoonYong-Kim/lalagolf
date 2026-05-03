from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ChatThreadCreateRequest(BaseModel):
    title: str | None = None


class ChatMessageCreateRequest(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    evidence: dict
    created_at: datetime


class ChatThreadResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatThreadDetailResponse(ChatThreadResponse):
    messages: list[ChatMessageResponse]


class ChatMessagePairResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
