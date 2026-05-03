from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    PASSWORD_ALGORITHM,
    PASSWORD_ITERATIONS,
    SESSION_TOKEN_BYTES,
    generate_session_token,
    hash_password,
    verify_password,
)
from app.models import ShareLink, User
from tests.test_rounds_api import create_committed_round
from tests.test_uploads_api import register


def test_session_cookie_uses_secure_http_only_defaults(client: TestClient) -> None:
    settings = get_settings()
    previous_secure = settings.session_cookie_secure
    settings.session_cookie_secure = True

    try:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "cookie@example.com",
                "password": "strong-password",
                "display_name": "Cookie Golfer",
            },
        )
    finally:
        settings.session_cookie_secure = previous_secure

    assert response.status_code == 201
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie


def test_password_hashing_uses_salted_pbkdf2_and_constant_verify() -> None:
    first_hash = hash_password("strong-password")
    second_hash = hash_password("strong-password")

    assert first_hash != second_hash
    assert first_hash.startswith(f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}$")
    assert verify_password("strong-password", first_hash)
    assert not verify_password("wrong-password", first_hash)
    assert not verify_password("strong-password", "plaintext")


def test_session_token_has_expected_entropy() -> None:
    token = generate_session_token()

    assert len(token) >= SESSION_TOKEN_BYTES
    assert token != generate_session_token()


def test_upload_rejects_non_text_content_type(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/api/v1/uploads/round-file",
        files={"file": ("round.png", b"not a text round", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file must be a text file"


def test_share_token_is_opaque_and_only_hash_is_stored(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    round_id = create_committed_round(client)

    response = client.post("/api/v1/shares", json={"round_id": round_id})

    assert response.status_code == 201
    token = response.json()["data"]["token"]
    share_id = response.json()["data"]["id"]
    share = db_session.get(ShareLink, UUID(share_id))
    assert share is not None
    assert len(token) >= 43
    assert share.token_hash != token
    assert len(share.token_hash) == 64


def test_public_share_payload_does_not_expose_private_fields(client: TestClient) -> None:
    register(client)
    round_id = create_committed_round(client)

    response = client.post("/api/v1/shares", json={"round_id": round_id})
    token = response.json()["data"]["token"]
    client.post("/api/v1/auth/logout")

    shared_response = client.get(f"/api/v1/shared/{token}")

    assert shared_response.status_code == 200
    payload_text = shared_response.text
    assert "홍성걸" not in payload_text
    assert "양명욱" not in payload_text
    assert "임길수" not in payload_text
    assert "storage_key" not in payload_text
    assert "source_file_id" not in payload_text
    assert "notes_private" not in payload_text
    assert "llm_messages" not in payload_text


def test_admin_upload_error_route_requires_admin(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "user@example.com")

    user_response = client.get("/api/v1/admin/uploads/errors")
    assert user_response.status_code == 403

    client.post("/api/v1/auth/logout")
    register(client, "admin@example.com")
    admin = db_session.scalars(select(User).where(User.email == "admin@example.com")).one()
    admin.role = "admin"
    db_session.commit()

    response = client.get("/api/v1/admin/uploads/errors")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_admin_upload_error_route_lists_failed_uploads(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "admin@example.com")
    admin = db_session.scalars(select(User).where(User.email == "admin@example.com")).one()
    admin.role = "admin"
    db_session.commit()

    upload_response = client.post(
        "/api/v1/uploads/round-file",
        files={"file": ("bad.txt", b"\xff\xfe\xfa", "text/plain")},
    )
    assert upload_response.status_code == 400

    response = client.get("/api/v1/admin/uploads/errors")

    assert response.status_code == 200
    errors = response.json()["data"]
    assert len(errors) == 1
    assert errors[0]["filename"] == "bad.txt"
    assert errors[0]["status"] == "failed"
    assert errors[0]["warnings"][0]["code"] == "invalid_encoding"
