import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.constants import (
    SOURCE_FILE_STATUS_UPLOADED,
    UPLOAD_REVIEW_STATUS_PENDING,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SourceFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_files"
    __table_args__ = (
        CheckConstraint(
            "status in ('uploaded', 'parsed', 'committed', 'failed')",
            name="status",
        ),
        Index("ix_source_files_user_created_at", "user_id", "created_at"),
        Index("ix_source_files_user_content_hash", "user_id", "content_hash"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        default=SOURCE_FILE_STATUS_UPLOADED,
        nullable=False,
    )
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    upload_reviews: Mapped[list["UploadReview"]] = relationship(
        back_populates="source_file",
        cascade="all, delete-orphan",
    )


class UploadReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "upload_reviews"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'needs_review', 'ready', 'committed', 'failed')",
            name="status",
        ),
        Index("ix_upload_reviews_user_created_at", "user_id", "created_at"),
        Index("ix_upload_reviews_source_file_id", "source_file_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Text,
        default=UPLOAD_REVIEW_STATUS_PENDING,
        nullable=False,
    )
    parsed_round: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    user_edits: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    committed_round_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rounds.id"),
        nullable=True,
    )

    source_file: Mapped[SourceFile] = relationship(back_populates="upload_reviews")
