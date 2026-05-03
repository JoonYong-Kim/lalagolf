import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RoundMetric(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "round_metrics"
    __table_args__ = (
        UniqueConstraint("round_id", "metric_key", name="uq_round_metrics_round_metric"),
        Index("ix_round_metrics_user_round", "user_id", "round_id"),
        Index("ix_round_metrics_user_category", "user_id", "category"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    metric_key: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[float | None] = mapped_column(nullable=True)
    sample_count: Mapped[int] = mapped_column(default=0, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ExpectedScoreTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "expected_score_tables"
    __table_args__ = (
        UniqueConstraint("user_id", "scope_type", "scope_key", name="uq_expected_tables_scope"),
        Index("ix_expected_tables_user_scope", "user_id", "scope_type", "scope_key"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_key: Mapped[str] = mapped_column(Text, nullable=False)
    sample_count: Mapped[int] = mapped_column(default=0, nullable=False)
    table_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ShotValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shot_values"
    __table_args__ = (
        UniqueConstraint("shot_id", name="uq_shot_values_shot_id"),
        Index("ix_shot_values_user_round", "user_id", "round_id"),
        Index("ix_shot_values_user_category", "user_id", "category"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
    )
    hole_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("holes.id", ondelete="CASCADE"),
        nullable=False,
    )
    shot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    expected_before: Mapped[float | None] = mapped_column(nullable=True)
    expected_after: Mapped[float | None] = mapped_column(nullable=True)
    shot_cost: Mapped[int] = mapped_column(default=1, nullable=False)
    shot_value: Mapped[float | None] = mapped_column(nullable=True)
    expected_lookup_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_sample_count: Mapped[int] = mapped_column(default=0, nullable=False)
    expected_source_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_confidence: Mapped[str] = mapped_column(Text, default="low", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Insight(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "insights"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key", name="uq_insights_user_dedupe"),
        Index("ix_insights_user_status_priority", "user_id", "status", "priority_score"),
        Index("ix_insights_user_category", "user_id", "category"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=True,
    )
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_key: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    primary_evidence_metric: Mapped[str] = mapped_column(Text, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    next_action: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(Text, nullable=False)
    priority_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="active", nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnalysisSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analysis_snapshots"
    __table_args__ = (
        Index("ix_analysis_snapshots_user_scope", "user_id", "scope_type", "scope_key"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_key: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
