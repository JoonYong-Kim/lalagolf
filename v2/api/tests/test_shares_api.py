from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Insight, Round
from tests.test_rounds_api import create_committed_round
from tests.test_uploads_api import register


def test_share_round_and_read_logged_out(client: TestClient) -> None:
    register(client)
    round_id = create_committed_round(client)

    create_response = client.post(
        "/api/v1/shares",
        json={"round_id": round_id, "title": "Weekend round"},
    )

    assert create_response.status_code == 201
    share = create_response.json()["data"]
    assert share["token"]
    assert share["url_path"] == f"/s/{share['token']}"

    client.post("/api/v1/auth/logout")
    shared_response = client.get(f"/api/v1/shared/{share['token']}")

    assert shared_response.status_code == 200
    payload = shared_response.json()["data"]
    assert payload["title"] == "Weekend round"
    assert payload["round"]["total_score"] is not None
    assert payload["holes"]
    assert len(payload["insights"]) == 1
    assert payload["insights"][0]["category"] == "penalty_impact"
    assert "페널티" in payload["insights"][0]["problem"]
    assert "companions" not in payload["round"]
    assert "notes_private" not in payload["round"]
    assert "source_file_id" not in payload["round"]
    assert "storage_key" not in payload["round"]


def test_shared_round_includes_top_public_safe_issue(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    round_id = create_committed_round(client)
    round_ = db_session.get(Round, UUID(round_id))
    assert round_ is not None
    db_session.add_all(
        [
            Insight(
                user_id=round_.user_id,
                round_id=round_.id,
                scope_type="round",
                scope_key=str(round_.id),
                category="putting",
                root_cause="three_putt",
                primary_evidence_metric="three_putt_rate",
                dedupe_key=f"{round_.id}:putting",
                problem="3-putt risk is the biggest issue",
                evidence="Two holes required three putts.",
                impact="Putting added avoidable strokes.",
                next_action="Practice 1m lag putts before the next round.",
                confidence="medium",
                priority_score=4.0,
                status="active",
            ),
            Insight(
                user_id=round_.user_id,
                round_id=round_.id,
                scope_type="round",
                scope_key=str(round_.id),
                category="tee",
                root_cause="penalty",
                primary_evidence_metric="penalty_count",
                dedupe_key=f"{round_.id}:tee",
                problem="Lower priority issue",
                evidence="One tee penalty.",
                impact="Penalty added one stroke.",
                next_action="Use safer tee target.",
                confidence="low",
                priority_score=1.0,
                status="active",
            ),
        ]
    )
    db_session.commit()

    share = client.post("/api/v1/shares", json={"round_id": round_id}).json()["data"]
    client.post("/api/v1/auth/logout")

    shared_response = client.get(f"/api/v1/shared/{share['token']}")

    assert shared_response.status_code == 200
    insights = shared_response.json()["data"]["insights"]
    assert len(insights) == 1
    assert insights[0]["problem"] == "3-putt risk is the biggest issue"
    assert insights[0]["category"] == "putting"
    assert "dedupe_key" not in insights[0]
    assert "root_cause" not in insights[0]


def test_revoke_share_stops_logged_out_access(client: TestClient) -> None:
    register(client)
    round_id = create_committed_round(client)
    share = client.post("/api/v1/shares", json={"round_id": round_id}).json()["data"]

    list_response = client.get("/api/v1/shares")
    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["round_id"] == round_id
    assert list_response.json()["data"][0]["url_path"] is None

    revoke_response = client.patch(f"/api/v1/shares/{share['id']}", json={"revoked": True})
    assert revoke_response.status_code == 200
    assert revoke_response.json()["data"]["revoked_at"] is not None

    client.post("/api/v1/auth/logout")
    shared_response = client.get(f"/api/v1/shared/{share['token']}")
    assert shared_response.status_code == 404


def test_share_management_is_owner_scoped(client: TestClient) -> None:
    register(client, "a@example.com")
    round_id = create_committed_round(client)
    share = client.post("/api/v1/shares", json={"round_id": round_id}).json()["data"]
    client.post("/api/v1/auth/logout")

    register(client, "b@example.com")

    assert client.post("/api/v1/shares", json={"round_id": round_id}).status_code == 404
    assert client.patch(f"/api/v1/shares/{share['id']}", json={"revoked": True}).status_code == 404
