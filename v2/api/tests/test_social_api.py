from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from tests.test_rounds_api import create_committed_round
from tests.test_uploads_api import register


def _user_id(db_session: Session, email: str) -> UUID:
    user = db_session.query(User).filter(User.email == email).one()
    return user.id


def test_public_round_search_and_detail(client: TestClient) -> None:
    register(client, "public@example.com")
    round_id = create_committed_round(client)

    patch_response = client.patch(
        f"/api/v1/rounds/{round_id}",
        json={"visibility": "public"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["visibility"] == "public"

    client.post("/api/v1/auth/logout")

    list_response = client.get("/api/v1/rounds/public?course=베르힐")
    assert list_response.status_code == 200
    assert list_response.json()["meta"]["total"] == 1
    assert list_response.json()["data"][0]["id"] == round_id

    detail_response = client.get(f"/api/v1/rounds/public/{round_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["id"] == round_id
    assert detail["owner_display_name"] == "Lala Golfer"
    assert "notes_private" not in detail


def test_follow_visibility_reactions_and_compare_candidates(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "a@example.com")
    round_a_id = create_committed_round(client)
    a_user_id = _user_id(db_session, "a@example.com")

    client.post("/api/v1/auth/logout")

    register(client, "b@example.com")
    round_b_id = create_committed_round(client)
    b_user_id = _user_id(db_session, "b@example.com")

    patch_visibility = client.patch(
        f"/api/v1/rounds/{round_b_id}",
        json={"visibility": "followers"},
    )
    assert patch_visibility.status_code == 200
    assert patch_visibility.json()["data"]["visibility"] == "followers"

    client.post("/api/v1/auth/logout")

    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": "strong-password"},
    )
    assert login_a.status_code == 200

    follow_request = client.post("/api/v1/follows", json={"following_id": str(b_user_id)})
    assert follow_request.status_code == 201

    client.post("/api/v1/auth/logout")

    login_b = client.post(
        "/api/v1/auth/login",
        json={"email": "b@example.com", "password": "strong-password"},
    )
    assert login_b.status_code == 200

    follow_accept = client.patch(
        f"/api/v1/follows/{a_user_id}/{b_user_id}",
        json={"status": "accepted"},
    )
    assert follow_accept.status_code == 200
    assert follow_accept.json()["data"]["status"] == "accepted"

    client.post("/api/v1/auth/logout")

    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": "strong-password"},
    )
    assert login_a.status_code == 200

    viewable_round = client.get(f"/api/v1/rounds/{round_b_id}")
    assert viewable_round.status_code == 200
    assert viewable_round.json()["data"]["visibility"] == "followers"

    like_response = client.post(f"/api/v1/rounds/{round_b_id}/likes")
    assert like_response.status_code == 200
    assert like_response.json()["data"]["liked"] is True

    comment_response = client.post(
        f"/api/v1/rounds/{round_b_id}/comments",
        json={"body": "Nice round"},
    )
    assert comment_response.status_code == 201
    assert comment_response.json()["data"]["body"] == "Nice round"

    comments_response = client.get(f"/api/v1/rounds/{round_b_id}/comments")
    assert comments_response.status_code == 200
    assert len(comments_response.json()["data"]) == 1

    candidates_response = client.get(f"/api/v1/rounds/{round_a_id}/comparison-candidates")
    assert candidates_response.status_code == 200
    candidates = candidates_response.json()["data"]
    assert any(candidate["round_id"] == round_b_id for candidate in candidates)

