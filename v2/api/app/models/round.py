import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.constants import COMPUTED_STATUS_PENDING, VISIBILITY_PRIVATE
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.models.analytics import Insight


class Course(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "courses"

    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    rounds: Mapped[list["Round"]] = relationship(back_populates="course")


class Round(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rounds"
    __table_args__ = (
        CheckConstraint(
            "visibility in ('private', 'link_only', 'public', 'followers')",
            name="visibility",
        ),
        CheckConstraint(
            "computed_status in ('draft', 'pending', 'ready', 'stale', 'failed')",
            name="computed_status",
        ),
        Index("ix_rounds_user_play_date", "user_id", "play_date"),
        Index("ix_rounds_user_course_name", "user_id", "course_name"),
        Index("ix_rounds_user_visibility", "user_id", "visibility"),
        Index(
            "ix_rounds_public_play_date",
            "visibility",
            "play_date",
            postgresql_where=text("visibility = 'public'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_files.id"),
        nullable=True,
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    course_name: Mapped[str] = mapped_column(Text, nullable=False)
    course_variant: Mapped[str | None] = mapped_column(Text, nullable=True)
    play_date: Mapped[date] = mapped_column(Date, nullable=False)
    tee_off_time: Mapped[str | None] = mapped_column(Text, nullable=True)
    tee: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_score: Mapped[int | None] = mapped_column(nullable=True)
    total_par: Mapped[int | None] = mapped_column(nullable=True)
    score_to_par: Mapped[int | None] = mapped_column(nullable=True)
    hole_count: Mapped[int] = mapped_column(default=18, nullable=False)
    weather: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_score: Mapped[int | None] = mapped_column(nullable=True)
    visibility: Mapped[str] = mapped_column(Text, default=VISIBILITY_PRIVATE, nullable=False)
    share_course: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    share_exact_date: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes_private: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_public: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_status: Mapped[str] = mapped_column(
        Text,
        default=COMPUTED_STATUS_PENDING,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    course: Mapped[Course | None] = relationship(back_populates="rounds")
    companions: Mapped[list["RoundCompanion"]] = relationship(
        back_populates="round",
        cascade="all, delete-orphan",
    )
    shared_insights: Mapped[list["Insight"]] = relationship(
        primaryjoin="Round.id == Insight.round_id",
        viewonly=True,
    )
    holes: Mapped[list["Hole"]] = relationship(back_populates="round", cascade="all, delete-orphan")


class RoundCompanion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "round_companions"
    __table_args__ = (
        Index("ix_round_companions_user_name", "user_id", "name"),
        Index("ix_round_companions_round_id", "round_id"),
    )

    round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    round: Mapped[Round] = relationship(back_populates="companions")


class Hole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "holes"
    __table_args__ = (
        UniqueConstraint("round_id", "hole_number", name="uq_holes_round_hole_number"),
        Index("ix_holes_user_round", "user_id", "round_id"),
    )

    round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    hole_number: Mapped[int] = mapped_column(nullable=False)
    par: Mapped[int] = mapped_column(nullable=False)
    score: Mapped[int | None] = mapped_column(nullable=True)
    putts: Mapped[int | None] = mapped_column(nullable=True)
    fairway_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    gir: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    up_and_down: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    sand_save: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    penalties: Mapped[int] = mapped_column(default=0, nullable=False)

    round: Mapped[Round] = relationship(back_populates="holes")
    shots: Mapped[list["Shot"]] = relationship(back_populates="hole", cascade="all, delete-orphan")


class Shot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shots"
    __table_args__ = (
        UniqueConstraint("hole_id", "shot_number", name="uq_shots_hole_shot_number"),
        Index("ix_shots_user_round", "user_id", "round_id"),
        Index("ix_shots_user_club_normalized", "user_id", "club_normalized"),
        Index("ix_shots_user_lies", "user_id", "start_lie", "end_lie"),
        Index("ix_shots_user_penalty_type", "user_id", "penalty_type"),
    )

    round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    hole_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("holes.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    shot_number: Mapped[int] = mapped_column(nullable=False)
    club: Mapped[str | None] = mapped_column(Text, nullable=True)
    club_normalized: Mapped[str | None] = mapped_column(Text, nullable=True)
    distance: Mapped[int | None] = mapped_column(nullable=True)
    start_lie: Mapped[str | None] = mapped_column(Text, nullable=True)
    end_lie: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_grade: Mapped[str | None] = mapped_column(Text, nullable=True)
    feel_grade: Mapped[str | None] = mapped_column(Text, nullable=True)
    penalty_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    penalty_strokes: Mapped[int] = mapped_column(default=0, nullable=False)
    score_cost: Mapped[int] = mapped_column(default=1, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    hole: Mapped[Hole] = relationship(back_populates="shots")
