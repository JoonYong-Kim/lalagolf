"""initial round schema

Revision ID: 20260502_0002
Revises: 20260502_0001
Create Date: 2026-05-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260502_0002"
down_revision: str | None = "20260502_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def user_fk(column_name: str = "user_id") -> sa.Column:
    return sa.Column(column_name, sa.Uuid(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "source_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('uploaded', 'parsed', 'committed', 'failed')",
            name=op.f("ck_source_files_status"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_source_files_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_files")),
    )
    op.create_index("ix_source_files_user_created_at", "source_files", ["user_id", "created_at"])
    op.create_index(
        "ix_source_files_user_content_hash",
        "source_files",
        ["user_id", "content_hash"],
    )

    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
    )
    op.create_index(op.f("ix_courses_name"), "courses", ["name"])

    op.create_table(
        "rounds",
        sa.Column("id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("source_file_id", sa.Uuid(), nullable=True),
        sa.Column("course_id", sa.Uuid(), nullable=True),
        sa.Column("course_name", sa.Text(), nullable=False),
        sa.Column("course_variant", sa.Text(), nullable=True),
        sa.Column("play_date", sa.Date(), nullable=False),
        sa.Column("tee", sa.Text(), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=True),
        sa.Column("total_par", sa.Integer(), nullable=True),
        sa.Column("score_to_par", sa.Integer(), nullable=True),
        sa.Column("hole_count", sa.Integer(), nullable=False),
        sa.Column("weather", sa.Text(), nullable=True),
        sa.Column("target_score", sa.Integer(), nullable=True),
        sa.Column("visibility", sa.Text(), nullable=False),
        sa.Column("share_course", sa.Boolean(), nullable=False),
        sa.Column("share_exact_date", sa.Boolean(), nullable=False),
        sa.Column("notes_private", sa.Text(), nullable=True),
        sa.Column("notes_public", sa.Text(), nullable=True),
        sa.Column("computed_status", sa.Text(), nullable=False),
        *timestamp_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "visibility in ('private', 'link_only', 'public', 'followers')",
            name=op.f("ck_rounds_visibility"),
        ),
        sa.CheckConstraint(
            "computed_status in ('pending', 'ready', 'stale', 'failed')",
            name=op.f("ck_rounds_computed_status"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_rounds_course_id_courses"),
        ),
        sa.ForeignKeyConstraint(
            ["source_file_id"],
            ["source_files.id"],
            name=op.f("fk_rounds_source_file_id_source_files"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_rounds_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rounds")),
    )
    op.create_index("ix_rounds_user_play_date", "rounds", ["user_id", "play_date"])
    op.create_index("ix_rounds_user_course_name", "rounds", ["user_id", "course_name"])
    op.create_index("ix_rounds_user_visibility", "rounds", ["user_id", "visibility"])
    op.create_index(
        "ix_rounds_public_play_date",
        "rounds",
        ["visibility", "play_date"],
        postgresql_where=sa.text("visibility = 'public'"),
    )

    op.create_table(
        "upload_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("source_file_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("parsed_round", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("user_edits", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("committed_round_id", sa.Uuid(), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "status in ('pending', 'needs_review', 'ready', 'committed', 'failed')",
            name=op.f("ck_upload_reviews_status"),
        ),
        sa.ForeignKeyConstraint(
            ["committed_round_id"],
            ["rounds.id"],
            name=op.f("fk_upload_reviews_committed_round_id_rounds"),
        ),
        sa.ForeignKeyConstraint(
            ["source_file_id"],
            ["source_files.id"],
            name=op.f("fk_upload_reviews_source_file_id_source_files"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_upload_reviews_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_upload_reviews")),
    )
    op.create_index(
        "ix_upload_reviews_user_created_at",
        "upload_reviews",
        ["user_id", "created_at"],
    )
    op.create_index("ix_upload_reviews_source_file_id", "upload_reviews", ["source_file_id"])

    op.create_table(
        "round_companions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("round_id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_round_companions_round_id_rounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_round_companions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_round_companions")),
    )
    op.create_index("ix_round_companions_user_name", "round_companions", ["user_id", "name"])
    op.create_index("ix_round_companions_round_id", "round_companions", ["round_id"])

    op.create_table(
        "holes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("round_id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("hole_number", sa.Integer(), nullable=False),
        sa.Column("par", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("putts", sa.Integer(), nullable=True),
        sa.Column("fairway_hit", sa.Boolean(), nullable=True),
        sa.Column("gir", sa.Boolean(), nullable=True),
        sa.Column("up_and_down", sa.Boolean(), nullable=True),
        sa.Column("sand_save", sa.Boolean(), nullable=True),
        sa.Column("penalties", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_holes_round_id_rounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_holes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_holes")),
        sa.UniqueConstraint("round_id", "hole_number", name="uq_holes_round_hole_number"),
    )
    op.create_index("ix_holes_user_round", "holes", ["user_id", "round_id"])

    op.create_table(
        "shots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("round_id", sa.Uuid(), nullable=False),
        sa.Column("hole_id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("shot_number", sa.Integer(), nullable=False),
        sa.Column("club", sa.Text(), nullable=True),
        sa.Column("club_normalized", sa.Text(), nullable=True),
        sa.Column("distance", sa.Integer(), nullable=True),
        sa.Column("start_lie", sa.Text(), nullable=True),
        sa.Column("end_lie", sa.Text(), nullable=True),
        sa.Column("result_grade", sa.Text(), nullable=True),
        sa.Column("feel_grade", sa.Text(), nullable=True),
        sa.Column("penalty_type", sa.Text(), nullable=True),
        sa.Column("penalty_strokes", sa.Integer(), nullable=False),
        sa.Column("score_cost", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["hole_id"],
            ["holes.id"],
            name=op.f("fk_shots_hole_id_holes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_shots_round_id_rounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_shots_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shots")),
        sa.UniqueConstraint("hole_id", "shot_number", name="uq_shots_hole_shot_number"),
    )
    op.create_index("ix_shots_user_round", "shots", ["user_id", "round_id"])
    op.create_index("ix_shots_user_club_normalized", "shots", ["user_id", "club_normalized"])
    op.create_index("ix_shots_user_lies", "shots", ["user_id", "start_lie", "end_lie"])
    op.create_index("ix_shots_user_penalty_type", "shots", ["user_id", "penalty_type"])


def downgrade() -> None:
    op.drop_index("ix_shots_user_penalty_type", table_name="shots")
    op.drop_index("ix_shots_user_lies", table_name="shots")
    op.drop_index("ix_shots_user_club_normalized", table_name="shots")
    op.drop_index("ix_shots_user_round", table_name="shots")
    op.drop_table("shots")
    op.drop_index("ix_holes_user_round", table_name="holes")
    op.drop_table("holes")
    op.drop_index("ix_round_companions_round_id", table_name="round_companions")
    op.drop_index("ix_round_companions_user_name", table_name="round_companions")
    op.drop_table("round_companions")
    op.drop_index("ix_upload_reviews_source_file_id", table_name="upload_reviews")
    op.drop_index("ix_upload_reviews_user_created_at", table_name="upload_reviews")
    op.drop_table("upload_reviews")
    op.drop_index("ix_rounds_public_play_date", table_name="rounds")
    op.drop_index("ix_rounds_user_visibility", table_name="rounds")
    op.drop_index("ix_rounds_user_course_name", table_name="rounds")
    op.drop_index("ix_rounds_user_play_date", table_name="rounds")
    op.drop_table("rounds")
    op.drop_index(op.f("ix_courses_name"), table_name="courses")
    op.drop_table("courses")
    op.drop_index("ix_source_files_user_content_hash", table_name="source_files")
    op.drop_index("ix_source_files_user_created_at", table_name="source_files")
    op.drop_table("source_files")
