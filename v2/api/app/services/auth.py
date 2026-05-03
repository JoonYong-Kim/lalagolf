from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models import User, UserProfile, UserSession


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    display_name: str,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        profile=UserProfile(),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEmailError from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = db.scalars(select(User).where(User.email == email, User.status == "active")).first()
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError
    return user


def create_session(
    db: Session,
    *,
    user: User,
    settings: Settings,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, UserSession]:
    token = generate_session_token()
    session = UserSession(
        user=user,
        session_token_hash=hash_session_token(token, settings.secret_key),
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=datetime.now(UTC) + timedelta(days=settings.session_lifetime_days),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return token, session


def revoke_session(db: Session, *, token: str, settings: Settings) -> None:
    token_hash = hash_session_token(token, settings.secret_key)
    session = db.scalars(
        select(UserSession).where(
            UserSession.session_token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
    ).first()
    if session is not None:
        session.revoked_at = datetime.now(UTC)
        db.commit()
