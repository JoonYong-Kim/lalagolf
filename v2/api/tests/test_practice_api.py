from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import UUID

from app.services.analysis_jobs import run_analysis_job_in_session
from tests.test_rounds_api import create_committed_round
from tests.test_uploads_api import register


def test_practice_plan_diary_goal_and_evaluation_flow(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    round_id = create_committed_round(client)
    recalculate_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")
    assert recalculate_response.status_code == 200
    run_analysis_job_in_session(
        db_session,
        UUID(recalculate_response.json()["data"]["analytics_job_id"]),
    )

    insights = client.get("/api/v1/insights").json()["data"]
    assert insights
    insight_id = insights[0]["id"]

    plan_response = client.post(
        "/api/v1/practice/plans",
        json={
            "source_insight_id": insight_id,
            "title": "Putting control block",
            "scheduled_for": "2026-05-10",
        },
    )
    assert plan_response.status_code == 201
    plan = plan_response.json()["data"]
    assert plan["source_insight_id"] == insight_id
    assert plan["status"] == "planned"

    done_response = client.patch(
        f"/api/v1/practice/plans/{plan['id']}",
        json={"status": "done"},
    )
    assert done_response.status_code == 200
    assert done_response.json()["data"]["completed_at"]

    diary_response = client.post(
        "/api/v1/practice/diary",
        json={
            "practice_plan_id": plan["id"],
            "entry_date": "2026-05-10",
            "title": "Lag putting note",
            "body": "Uphill 8m putts were short.",
            "tags": ["putting", "lag"],
            "confidence": "medium",
        },
    )
    assert diary_response.status_code == 201
    assert diary_response.json()["data"]["practice_plan_id"] == plan["id"]
    assert client.get("/api/v1/practice/diary").json()["data"]

    goal_response = client.post(
        "/api/v1/goals",
        json={
            "source_insight_id": insight_id,
            "practice_plan_id": plan["id"],
            "title": "Keep putts under control",
            "category": "putting",
            "metric_key": "three_putt_holes",
            "target_operator": "<=",
            "target_value": 1,
            "applies_to": "next_round",
        },
    )
    assert goal_response.status_code == 201
    goal = goal_response.json()["data"]
    assert goal["status"] == "active"

    evaluation_response = client.post(
        f"/api/v1/goals/{goal['id']}/evaluate",
        json={"round_id": round_id},
    )
    assert evaluation_response.status_code == 200
    evaluation = evaluation_response.json()["data"]
    assert evaluation["evaluation_status"] in {"achieved", "missed"}
    assert evaluation["actual_json"]["metric_key"] == "three_putt_holes"

    closed_goal = client.get("/api/v1/goals").json()["data"][0]
    assert closed_goal["status"] == evaluation["evaluation_status"]

    delete_response = client.delete(f"/api/v1/goals/{goal['id']}")
    assert delete_response.status_code == 204
    assert client.get("/api/v1/goals").json()["data"] == []


def test_manual_goal_evaluation_and_owner_scope(client: TestClient) -> None:
    register(client, "a@example.com")
    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Commit to conservative targets",
            "category": "off_the_tee",
            "metric_key": "qualitative",
            "target_operator": "=",
            "target_value": 1,
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["data"]["id"]
    client.post("/api/v1/auth/logout")

    register(client, "b@example.com")
    assert client.get("/api/v1/goals").json()["data"] == []
    assert client.patch(f"/api/v1/goals/{goal_id}", json={"status": "cancelled"}).status_code == 404

    own_goal = client.post(
        "/api/v1/goals",
        json={
            "title": "Manual review goal",
            "category": "mental",
            "metric_key": "qualitative",
            "target_operator": "=",
            "target_value": 1,
        },
    ).json()["data"]
    manual_response = client.post(
        f"/api/v1/goals/{own_goal['id']}/manual-evaluation",
        json={"evaluation_status": "partial", "note": "Better routine, still rushed twice."},
    )
    assert manual_response.status_code == 201
    assert manual_response.json()["data"]["evaluated_by"] == "user"
    assert manual_response.json()["data"]["evaluation_status"] == "partial"

    delete_response = client.delete(f"/api/v1/goals/{own_goal['id']}")
    assert delete_response.status_code == 204
    assert client.get("/api/v1/goals").json()["data"] == []
