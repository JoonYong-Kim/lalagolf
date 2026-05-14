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
    assert "companions" not in list_response.json()["data"][0]

    detail_response = client.get(f"/api/v1/rounds/public/{round_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["id"] == round_id
    assert detail["owner_display_name"] == "Lala Golfer"
    assert "companions" not in detail
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

    link_response = client.post(
        "/api/v1/companions/links",
        json={"companion_name": "홍성걸", "companion_email": "b@example.com"},
    )
    assert link_response.status_code == 201
    link = link_response.json()["data"]
    assert link["companion_user_id"] == str(b_user_id)
    assert link["companion_email"] == "b@example.com"

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


def test_comparison_candidates_require_explicit_companion_link(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "a-no-link@example.com")
    round_a_id = create_committed_round(client)
    a_user_id = _user_id(db_session, "a-no-link@example.com")
    client.post("/api/v1/auth/logout")

    register(client, "b-no-link@example.com")
    round_b_id = create_committed_round(client)
    b_user_id = _user_id(db_session, "b-no-link@example.com")
    client.patch(f"/api/v1/rounds/{round_b_id}", json={"visibility": "followers"})
    client.post("/api/v1/auth/logout")

    client.post(
        "/api/v1/auth/login",
        json={"email": "a-no-link@example.com", "password": "strong-password"},
    )
    client.post("/api/v1/follows", json={"following_id": str(b_user_id)})
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login",
        json={"email": "b-no-link@example.com", "password": "strong-password"},
    )
    client.patch(f"/api/v1/follows/{a_user_id}/{b_user_id}", json={"status": "accepted"})
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login",
        json={"email": "a-no-link@example.com", "password": "strong-password"},
    )

    candidates_response = client.get(f"/api/v1/rounds/{round_a_id}/comparison-candidates")

    assert candidates_response.status_code == 200
    assert candidates_response.json()["data"] == []


def test_comparison_candidates_do_not_expose_other_round_companions(
    client: TestClient,
) -> None:
    register(client, "owner-public-compare@example.com")
    public_round_id = create_committed_round(client)
    client.patch(f"/api/v1/rounds/{public_round_id}", json={"visibility": "public"})
    client.post("/api/v1/auth/logout")

    register(client, "viewer-public-compare@example.com")

    candidates_response = client.get(f"/api/v1/rounds/{public_round_id}/comparison-candidates")

    assert candidates_response.status_code == 400
    assert "홍성걸" not in candidates_response.text


def test_follow_requester_cannot_self_accept(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "a-self@example.com")
    a_user_id = _user_id(db_session, "a-self@example.com")
    client.post("/api/v1/auth/logout")

    register(client, "b-self@example.com")
    b_user_id = _user_id(db_session, "b-self@example.com")
    client.post("/api/v1/auth/logout")

    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": "a-self@example.com", "password": "strong-password"},
    )
    assert login_a.status_code == 200
    follow_request = client.post("/api/v1/follows", json={"following_id": str(b_user_id)})
    assert follow_request.status_code == 201

    self_accept = client.patch(
        f"/api/v1/follows/{a_user_id}/{b_user_id}",
        json={"status": "accepted"},
    )
    assert self_accept.status_code == 400


def test_social_feed_pending_follow_does_not_expose_followers_round(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "owner-pending@example.com")
    owner_id = _user_id(db_session, "owner-pending@example.com")
    followers_round_id = create_committed_round(client)
    patch = client.patch(
        f"/api/v1/rounds/{followers_round_id}",
        json={"visibility": "followers"},
    )
    assert patch.status_code == 200
    client.post("/api/v1/auth/logout")

    register(client, "requester-pending@example.com")
    follow_request = client.post("/api/v1/follows", json={"following_id": str(owner_id)})
    assert follow_request.status_code == 201

    feed = client.get("/api/v1/social/feed?scope=following&limit=10")
    assert feed.status_code == 200
    items = feed.json()["data"]
    assert all(item.get("round_id") != followers_round_id for item in items)


def test_social_feed_blocked_follow_does_not_expose_followers_round(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "owner-blocked@example.com")
    owner_id = _user_id(db_session, "owner-blocked@example.com")
    followers_round_id = create_committed_round(client)
    patch = client.patch(
        f"/api/v1/rounds/{followers_round_id}",
        json={"visibility": "followers"},
    )
    assert patch.status_code == 200
    client.post("/api/v1/auth/logout")

    register(client, "requester-blocked@example.com")
    requester_id = _user_id(db_session, "requester-blocked@example.com")
    follow_request = client.post("/api/v1/follows", json={"following_id": str(owner_id)})
    assert follow_request.status_code == 201
    client.post("/api/v1/auth/logout")

    client.post(
        "/api/v1/auth/login",
        json={"email": "owner-blocked@example.com", "password": "strong-password"},
    )
    block = client.patch(
        f"/api/v1/follows/{requester_id}/{owner_id}",
        json={"status": "blocked"},
    )
    assert block.status_code == 200
    client.post("/api/v1/auth/logout")

    client.post(
        "/api/v1/auth/login",
        json={"email": "requester-blocked@example.com", "password": "strong-password"},
    )
    feed = client.get("/api/v1/social/feed?scope=following&limit=10")
    assert feed.status_code == 200
    items = feed.json()["data"]
    assert all(item.get("round_id") != followers_round_id for item in items)

    self_reopen = client.patch(
        f"/api/v1/follows/{requester_id}/{owner_id}",
        json={"status": "pending"},
    )
    assert self_reopen.status_code == 400


def test_social_feed_excludes_private_and_link_only_rounds(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "owner-private@example.com")
    private_round_id = create_committed_round(client)
    link_round_id = create_committed_round(client)
    link_patch = client.patch(
        f"/api/v1/rounds/{link_round_id}",
        json={"visibility": "link_only"},
    )
    assert link_patch.status_code == 200
    client.post("/api/v1/auth/logout")

    feed = client.get("/api/v1/social/feed?scope=all&limit=20")
    assert feed.status_code == 200
    items = feed.json()["data"]
    forbidden = {private_round_id, link_round_id}
    assert all(item.get("round_id") not in forbidden for item in items)


def test_social_feed_cursor_pagination_has_no_duplicates(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "paginator@example.com")
    round_ids: list[str] = []
    for _ in range(3):
        round_id = create_committed_round(client)
        patch = client.patch(
            f"/api/v1/rounds/{round_id}",
            json={"visibility": "public"},
        )
        assert patch.status_code == 200
        round_ids.append(round_id)
    client.post("/api/v1/auth/logout")

    first = client.get("/api/v1/social/feed?scope=public&limit=2")
    assert first.status_code == 200
    first_body = first.json()
    first_items = first_body["data"]
    assert len(first_items) == 2
    assert first_body["meta"]["has_more"] is True
    cursor = first_body["meta"]["next_cursor"]
    assert cursor

    second = client.get(f"/api/v1/social/feed?scope=public&limit=2&cursor={cursor}")
    assert second.status_code == 200
    second_body = second.json()
    second_items = second_body["data"]
    assert len(second_items) >= 1

    seen_round_ids = {item.get("round_id") for item in first_items if item.get("round_id")}
    for item in second_items:
        if item.get("round_id"):
            assert item["round_id"] not in seen_round_ids, "cursor must not duplicate items"
            seen_round_ids.add(item["round_id"])

    combined = {item["round_id"] for item in first_items + second_items if item.get("round_id")}
    assert set(round_ids).issubset(combined)


def test_social_feed_public_followers_diary_and_goal(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "feed-owner@example.com")
    owner_id = _user_id(db_session, "feed-owner@example.com")
    public_round_id = create_committed_round(client)
    public_patch = client.patch(
        f"/api/v1/rounds/{public_round_id}",
        json={"visibility": "public", "share_exact_date": False},
    )
    assert public_patch.status_code == 200

    diary_response = client.post(
        "/api/v1/practice/diary",
        json={
            "entry_date": "2026-05-10",
            "title": "Lag putting discovery",
            "body": "8m uphill putts were consistently short during practice.",
            "category": "putting",
            "tags": ["lag-putt"],
            "visibility": "public",
        },
    )
    assert diary_response.status_code == 201

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Keep 3-putts to one or fewer",
            "category": "putting",
            "metric_key": "three_putt_holes",
            "target_operator": "<=",
            "target_value": 1,
            "applies_to": "next_round",
            "visibility": "public",
        },
    )
    assert goal_response.status_code == 201

    client.post("/api/v1/auth/logout")

    public_feed = client.get("/api/v1/social/feed?scope=public&limit=10")
    assert public_feed.status_code == 200
    items = public_feed.json()["data"]
    item_types = {item["item_type"] for item in items}
    assert {"round", "practice_diary", "round_goal"}.issubset(item_types)
    round_item = next(item for item in items if item["item_type"] == "round")
    assert round_item["course_name"] == "베르힐 영종"
    assert round_item["play_date"] is None
    assert round_item["play_month"] == "2026-04"
    assert round_item["top_insight"] is not None
    assert "companions" not in round_item

    register(client, "feed-follower@example.com")
    follower_id = _user_id(db_session, "feed-follower@example.com")
    client.post("/api/v1/follows", json={"following_id": str(owner_id)})
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login",
        json={"email": "feed-owner@example.com", "password": "strong-password"},
    )
    accept = client.patch(
        f"/api/v1/follows/{follower_id}/{owner_id}",
        json={"status": "accepted"},
    )
    assert accept.status_code == 200
    follower_round_id = create_committed_round(client)
    follower_patch = client.patch(
        f"/api/v1/rounds/{follower_round_id}",
        json={"visibility": "followers"},
    )
    assert follower_patch.status_code == 200

    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login",
        json={"email": "feed-follower@example.com", "password": "strong-password"},
    )
    following_feed = client.get("/api/v1/social/feed?scope=following&limit=10")
    assert following_feed.status_code == 200
    following_items = following_feed.json()["data"]
    assert any(item.get("round_id") == follower_round_id for item in following_items)
