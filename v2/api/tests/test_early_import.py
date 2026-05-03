from collections.abc import Generator
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Hole, Round, RoundCompanion, Shot, SourceFile, UploadReview
from app.models.constants import VISIBILITY_PRIVATE
from app.services.early_import import (
    ensure_import_owner,
    import_raw_round_file,
    result_to_report_row,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with SessionLocal() as session:
        yield session

    Base.metadata.drop_all(engine)


def test_import_raw_round_file_creates_private_v2_rows(tmp_path, db_session: Session) -> None:
    raw_file = tmp_path / "sample-round.txt"
    raw_file.write_text(
        "\n".join(
            [
                "2026-04-11 13:23",
                "베르힐 영종",
                "홍성걸 양명욱 임길수",
                "1P4",
                "D C C",
                "I7 C C",
                "IP B B",
                "P B B 12 OK",
                "2P5",
                "D C C OB",
                "UW B B",
                "56 B B 50",
                "P C C 8",
                "P C C 2 OK",
            ]
        ),
        encoding="utf-8",
    )
    owner = ensure_import_owner(db_session, email="owner@example.com", display_name="Owner")

    result = import_raw_round_file(db_session, owner=owner, file_path=raw_file)
    db_session.commit()

    round_ = db_session.get(Round, UUID(result.round_id))
    assert round_ is not None
    assert round_.user_id == owner.id
    assert round_.visibility == VISIBILITY_PRIVATE
    assert round_.share_course is False
    assert round_.share_exact_date is False
    assert round_.course_name == "베르힐 영종"
    assert round_.hole_count == 2
    assert round_.total_score == 13
    assert result.shot_count == 9
    assert result.shot_fact_count == 9

    source_file = db_session.get(SourceFile, UUID(result.source_file_id))
    upload_review = db_session.get(UploadReview, UUID(result.upload_review_id))
    assert source_file is not None
    assert source_file.status == "committed"
    assert upload_review is not None
    assert upload_review.status == "committed"
    assert str(upload_review.committed_round_id) == result.round_id
    assert upload_review.parsed_round["course_name"] == "베르힐 영종"

    companions = db_session.scalars(
        select(RoundCompanion).where(RoundCompanion.round_id == round_.id)
    ).all()
    assert [companion.name for companion in companions] == ["홍성걸", "양명욱", "임길수"]

    holes = db_session.scalars(
        select(Hole).where(Hole.round_id == round_.id).order_by(Hole.hole_number)
    ).all()
    assert [hole.par for hole in holes] == [4, 5]
    assert holes[1].penalties == 2

    shots = db_session.scalars(
        select(Shot).where(Shot.round_id == round_.id).order_by(Shot.shot_number)
    ).all()
    assert any(shot.penalty_type == "OB" and shot.penalty_strokes == 2 for shot in shots)
    assert all(shot.user_id == owner.id for shot in shots)


def test_result_to_report_row_is_ui_fixture_friendly(tmp_path, db_session: Session) -> None:
    raw_file = tmp_path / "sample-round.txt"
    raw_file.write_text(
        "\n".join(
            [
                "2026-04-14 13:30",
                "파인힐스",
                "조인",
                "1P4",
                "D B C",
                "I8 C B",
                "P B B 6 OK",
            ]
        ),
        encoding="utf-8",
    )
    owner = ensure_import_owner(db_session)

    result = import_raw_round_file(db_session, owner=owner, file_path=raw_file)
    report_row = result_to_report_row(result)

    assert report_row["course_name"] == "파인힐스"
    assert report_row["play_date"] == "2026-04-14"
    assert report_row["visibility"] == "private"
    assert report_row["shot_count"] == report_row["shot_fact_count"]


def test_import_raw_round_file_reuses_existing_content_hash(tmp_path, db_session: Session) -> None:
    raw_file = tmp_path / "sample-round.txt"
    raw_file.write_text(
        "\n".join(
            [
                "2026-04-14 13:30",
                "파인힐스",
                "조인",
                "1P4",
                "D B C",
                "I8 C B",
                "P B B 6 OK",
            ]
        ),
        encoding="utf-8",
    )
    owner = ensure_import_owner(db_session)

    first = import_raw_round_file(db_session, owner=owner, file_path=raw_file)
    second = import_raw_round_file(db_session, owner=owner, file_path=raw_file)

    assert second.round_id == first.round_id
    assert db_session.scalar(select(func.count(Round.id))) == 1
    assert db_session.scalar(select(func.count(SourceFile.id))) == 1
