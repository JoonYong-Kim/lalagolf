import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MigrationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "migration_runs"
    __table_args__ = (Index("ix_migration_runs_user_created_at", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="started", nullable=False)
    source: Mapped[str] = mapped_column(Text, default="v1", nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class MigrationIdMap(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "migration_id_map"
    __table_args__ = (
        UniqueConstraint("migration_run_id", "entity_type", "v1_id", name="uq_migration_id_map_v1"),
        Index("ix_migration_id_map_run_entity", "migration_run_id", "entity_type"),
    )

    migration_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("migration_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    v1_id: Mapped[str] = mapped_column(Text, nullable=False)
    v2_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class MigrationIssue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "migration_issues"
    __table_args__ = (Index("ix_migration_issues_run_severity", "migration_run_id", "severity"),)

    migration_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("migration_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
