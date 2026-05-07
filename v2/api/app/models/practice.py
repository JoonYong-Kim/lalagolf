import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PracticePlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "practice_plans"
    __table_args__ = (
        Index("ix_practice_plans_user_status_scheduled", "user_id", "status", "scheduled_for"),
        Index("ix_practice_plans_user_category", "user_id", "category"),
        Index("ix_practice_plans_source_insight", "source_insight_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_insight_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("insights.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    drill_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    target_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    scheduled_for: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="planned", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PracticeDiaryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "practice_diary_entries"
    __table_args__ = (
        Index("ix_practice_diary_user_entry_date", "user_id", "entry_date"),
        Index("ix_practice_diary_user_category", "user_id", "category"),
        Index("ix_practice_diary_plan", "practice_plan_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    practice_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("practice_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_insight_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("insights.id", ondelete="SET NULL"),
        nullable=True,
    )
    round_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rounds.id", ondelete="SET NULL"),
        nullable=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    mood: Mapped[str | None] = mapped_column(Text, nullable=True)


class RoundGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "round_goals"
    __table_args__ = (
        Index("ix_round_goals_user_status_due", "user_id", "status", "due_date"),
        Index("ix_round_goals_user_category", "user_id", "category"),
        Index("ix_round_goals_source_insight", "source_insight_id"),
        Index("ix_round_goals_practice_plan", "practice_plan_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_insight_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("insights.id", ondelete="SET NULL"),
        nullable=True,
    )
    practice_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("practice_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    metric_key: Mapped[str] = mapped_column(Text, nullable=False)
    target_operator: Mapped[str] = mapped_column(Text, nullable=False)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    target_value_max: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    target_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    applies_to: Mapped[str] = mapped_column(Text, default="next_round", nullable=False)
    due_round_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rounds.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="active", nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GoalEvaluation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "goal_evaluations"
    __table_args__ = (
        Index("ix_goal_evaluations_user_evaluated", "user_id", "evaluated_at"),
        Index("ix_goal_evaluations_goal_round", "goal_id", "round_id"),
        Index("ix_goal_evaluations_round", "round_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("round_goals.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rounds.id", ondelete="SET NULL"),
        nullable=True,
    )
    evaluation_status: Mapped[str] = mapped_column(Text, nullable=False)
    actual_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    actual_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evaluated_by: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
