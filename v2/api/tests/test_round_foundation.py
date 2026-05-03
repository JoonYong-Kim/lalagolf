from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.ownership import owner_scoped_select
from app.models import Hole, Round, Shot, SourceFile, User, UserProfile
from app.models.constants import VISIBILITY_PRIVATE


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


def make_user(email: str) -> User:
    return User(
        email=email,
        password_hash="hash",
        display_name=email.split("@")[0],
        profile=UserProfile(),
    )


def test_round_foundation_defaults_and_relationships(db_session: Session) -> None:
    user = make_user("owner@example.com")
    db_session.add(user)
    db_session.flush()

    source_file = SourceFile(
        user_id=user.id,
        filename="round.txt",
        storage_key="uploads/round.txt",
        file_size=120,
        content_hash="hash",
    )
    db_session.add(source_file)
    db_session.flush()

    round_ = Round(
        user_id=user.id,
        course_name="Lala CC",
        play_date=date(2026, 5, 2),
        source_file_id=source_file.id,
    )
    db_session.add(round_)
    db_session.flush()

    hole = Hole(user_id=user.id, round_id=round_.id, hole_number=1, par=4, score=5)
    db_session.add(hole)
    db_session.flush()

    shot = Shot(user_id=user.id, round_id=round_.id, hole_id=hole.id, shot_number=1, club="D")
    db_session.add(shot)
    db_session.commit()

    saved_round = db_session.get(Round, round_.id)

    assert saved_round is not None
    assert saved_round.visibility == VISIBILITY_PRIVATE
    assert saved_round.share_course is False
    assert saved_round.share_exact_date is False
    assert saved_round.computed_status == "pending"
    assert saved_round.hole_count == 18
    assert saved_round.holes[0].shots[0].penalty_strokes == 0
    assert saved_round.holes[0].shots[0].score_cost == 1


def test_owner_scoped_select_excludes_other_users_resources(db_session: Session) -> None:
    user_a = make_user("a@example.com")
    user_b = make_user("b@example.com")
    db_session.add_all([user_a, user_b])
    db_session.flush()

    file_a = SourceFile(
        user_id=user_a.id,
        filename="a.txt",
        storage_key="uploads/a.txt",
        file_size=1,
        content_hash="hash-a",
    )
    file_b = SourceFile(
        user_id=user_b.id,
        filename="b.txt",
        storage_key="uploads/b.txt",
        file_size=1,
        content_hash="hash-b",
    )
    db_session.add_all([file_a, file_b])
    db_session.commit()

    visible_to_a = db_session.scalars(owner_scoped_select(SourceFile, user_a.id)).all()

    assert visible_to_a == [file_a]
