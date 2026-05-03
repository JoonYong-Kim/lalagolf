import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LlmThread(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "llm_threads"
    __table_args__ = (Index("ix_llm_threads_user_created_at", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)


class LlmMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "llm_messages"
    __table_args__ = (Index("ix_llm_messages_thread_created_at", "thread_id", "created_at"),)

    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("llm_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
