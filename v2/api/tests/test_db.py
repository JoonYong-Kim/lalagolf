from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.health import check_database_connection
from app.models import User, UserProfile, UserSession


def test_database_connection_check_with_sqlite_engine() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    assert check_database_connection(engine) is True


def test_initial_user_model_relationships() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(
            email="user@example.com",
            password_hash="hash",
            display_name="Lala Golfer",
            profile=UserProfile(),
            sessions=[
                UserSession(
                    session_token_hash="token-hash",
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                )
            ],
        )
        session.add(user)
        session.commit()

    with Session(engine) as session:
        saved = session.query(User).filter_by(email="user@example.com").one()

        assert saved.profile is not None
        assert saved.profile.privacy_default == "private"
        assert saved.profile.share_course_by_default is False
        assert len(saved.sessions) == 1
