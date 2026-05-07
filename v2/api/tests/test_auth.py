from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import User, UserProfile, UserSession


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


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


def test_register_sets_session_cookie_and_returns_current_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "USER@example.com",
            "password": "strong-password",
            "display_name": "Lala Golfer",
        },
    )

    assert response.status_code == 201
    assert response.cookies.get("lalagolf_session")
    assert response.json()["data"]["user"]["email"] == "user@example.com"
    assert response.json()["data"]["user"]["profile"]["privacy_default"] == "private"

    me_response = client.get("/api/v1/me")

    assert me_response.status_code == 200
    assert me_response.json()["data"]["user"]["display_name"] == "Lala Golfer"


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    payload = {
        "email": "user@example.com",
        "password": "strong-password",
        "display_name": "Lala Golfer",
    }

    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409


def test_login_rejects_invalid_credentials(client: TestClient, db_session: Session) -> None:
    db_session.add(
        User(
            email="user@example.com",
            password_hash=hash_password("right-password"),
            display_name="Lala Golfer",
            profile=UserProfile(),
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_and_logout_revokes_session(client: TestClient, db_session: Session) -> None:
    db_session.add(
        User(
            email="user@example.com",
            password_hash=hash_password("right-password"),
            display_name="Lala Golfer",
            profile=UserProfile(),
        )
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "right-password"},
    )

    assert login_response.status_code == 200
    assert client.get("/api/v1/me").status_code == 200

    logout_response = client.post("/api/v1/auth/logout")

    assert logout_response.status_code == 200
    assert client.get("/api/v1/me").status_code == 401
    assert db_session.query(UserSession).filter(UserSession.revoked_at.is_not(None)).count() == 1


def test_google_start_requires_oauth_configuration(client: TestClient) -> None:
    settings = get_settings()
    previous_client_id = settings.google_oauth_client_id
    previous_client_secret = settings.google_oauth_client_secret
    settings.google_oauth_client_id = None
    settings.google_oauth_client_secret = None
    try:
        response = client.get("/api/v1/auth/google/start", follow_redirects=False)
    finally:
        settings.google_oauth_client_id = previous_client_id
        settings.google_oauth_client_secret = previous_client_secret

    assert response.status_code == 503


def test_google_oauth_callback_creates_session(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    previous_client_id = settings.google_oauth_client_id
    previous_client_secret = settings.google_oauth_client_secret
    previous_redirect_uri = settings.google_oauth_redirect_uri
    previous_web_base_url = settings.web_base_url
    settings.google_oauth_client_id = "google-client"
    settings.google_oauth_client_secret = "google-secret"
    settings.google_oauth_redirect_uri = "http://testserver/api/v1/auth/google/callback"
    settings.web_base_url = "http://localhost:2323"

    def fake_google_userinfo(*, code: str, settings: object) -> dict[str, object]:
        assert code == "oauth-code"
        return {
            "email": "google@example.com",
            "email_verified": True,
            "name": "Google Golfer",
            "picture": "https://example.com/avatar.png",
        }

    monkeypatch.setattr("app.api.v1.auth.fetch_google_userinfo", fake_google_userinfo)

    try:
        start_response = client.get("/api/v1/auth/google/start", follow_redirects=False)
        state = start_response.cookies.get(settings.google_oauth_state_cookie_name)
        assert start_response.status_code == 307
        assert state

        callback_response = client.get(
            f"/api/v1/auth/google/callback?code=oauth-code&state={state}",
            follow_redirects=False,
        )
    finally:
        settings.google_oauth_client_id = previous_client_id
        settings.google_oauth_client_secret = previous_client_secret
        settings.google_oauth_redirect_uri = previous_redirect_uri
        settings.web_base_url = previous_web_base_url

    assert callback_response.status_code == 307
    assert callback_response.headers["location"] == "http://localhost:2323/upload"
    assert callback_response.cookies.get("lalagolf_session")
    assert client.get("/api/v1/me").json()["data"]["user"]["email"] == "google@example.com"


def test_update_profile_requires_auth_and_updates_profile(client: TestClient) -> None:
    unauthenticated_response = client.patch(
        "/api/v1/me/profile",
        json={"display_name": "Blocked"},
    )

    assert unauthenticated_response.status_code == 401

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "strong-password",
            "display_name": "Lala Golfer",
        },
    )

    response = client.patch(
        "/api/v1/me/profile",
        json={
            "display_name": "Updated Golfer",
            "bio": "Weekend rounds",
            "home_course": "Lala CC",
            "share_course_by_default": True,
        },
    )

    assert response.status_code == 200
    user = response.json()["data"]["user"]
    assert user["display_name"] == "Updated Golfer"
    assert user["profile"]["bio"] == "Weekend rounds"
    assert user["profile"]["home_course"] == "Lala CC"
    assert user["profile"]["share_course_by_default"] is True
