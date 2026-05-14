import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Follow(TimestampMixin, Base):
    __tablename__ = "follows"
    __table_args__ = (
        CheckConstraint("status in ('pending', 'accepted', 'blocked')", name="status"),
    )

    follower_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    following_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CompanionAccountLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companion_account_links"
    __table_args__ = (
        UniqueConstraint("owner_id", "companion_name", name="uq_companion_links_owner_name"),
        Index("ix_companion_links_owner", "owner_id"),
        Index("ix_companion_links_companion_user", "companion_user_id"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    companion_name: Mapped[str] = mapped_column(Text, nullable=False)
    companion_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )


class RoundLike(TimestampMixin, Base):
    __tablename__ = "round_likes"

    round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )


class RoundComment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "round_comments"
    __table_args__ = (
        CheckConstraint("status in ('active', 'deleted', 'hidden')", name="status"),
        Index("ix_round_comments_round_created_at", "round_id", "created_at"),
        Index("ix_round_comments_user_created_at", "user_id", "created_at"),
    )

    round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("round_comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="active", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    parent_comment: Mapped["RoundComment | None"] = relationship(
        remote_side="RoundComment.id",
        back_populates="replies",
    )
    replies: Mapped[list["RoundComment"]] = relationship(
        back_populates="parent_comment",
        cascade="all, delete-orphan",
    )
