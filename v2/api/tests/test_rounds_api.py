from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Round
from app.services.analysis_jobs import run_analysis_job_in_session
from tests.test_uploads_api import register, sample_round_text


def create_committed_round(client: TestClient) -> str:
    upload_response = client.post(
        "/api/v1/uploads/round-file",
        files={"file": ("round.txt", sample_round_text().encode("utf-8"), "text/plain")},
    )
    assert upload_response.status_code == 201
    upload_id = upload_response.json()["data"]["upload_review_id"]

    commit_response = client.post(
        f"/api/v1/uploads/{upload_id}/commit",
        json={"share_course": False, "share_exact_date": False},
    )
    assert commit_response.status_code == 200
    return commit_response.json()["data"]["round_id"]


def test_round_list_detail_and_summary(client: TestClient) -> None:
    register(client)
    round_id = create_committed_round(client)

    list_response = client.get("/api/v1/rounds?limit=10&year=2026&course=베르힐")
    assert list_response.status_code == 200
    list_data = list_response.json()["data"]
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == round_id

    detail_response = client.get(f"/api/v1/rounds/{round_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["hole_count"] == 2
    assert len(detail["holes"]) == 2
    assert detail["holes"][0]["shots"]
    assert "penalties_total" in detail["metrics"]

    holes_response = client.get(f"/api/v1/rounds/{round_id}/holes")
    assert holes_response.status_code == 200
    assert len(holes_response.json()["data"]) == 2

    shots_response = client.get(f"/api/v1/rounds/{round_id}/shots")
    assert shots_response.status_code == 200
    assert len(shots_response.json()["data"]) > 0

    summary_response = client.get("/api/v1/analytics/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()["data"]
    assert summary["kpis"]["round_count"] == 1
    assert summary["recent_rounds"][0]["id"] == round_id
    assert summary["score_trend"]
    assert len(summary["priority_insights"]) <= 3


def test_round_filters_update_and_recalculate(client: TestClient, db_session: Session) -> None:
    register(client)
    round_id = create_committed_round(client)

    no_match_response = client.get("/api/v1/rounds?companion=없는사람")
    assert no_match_response.status_code == 200
    assert no_match_response.json()["data"]["total"] == 0

    match_response = client.get("/api/v1/rounds?companion=홍성걸")
    assert match_response.status_code == 200
    assert match_response.json()["data"]["total"] == 1

    patch_response = client.patch(
        f"/api/v1/rounds/{round_id}",
        json={"course_name": "Updated Course", "weather": "Cloudy"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["course_name"] == "Updated Course"
    assert patch_response.json()["data"]["computed_status"] == "stale"

    detail = client.get(f"/api/v1/rounds/{round_id}").json()["data"]
    hole_id = detail["holes"][0]["id"]
    shot_id = detail["holes"][0]["shots"][0]["id"]

    hole_response = client.patch(f"/api/v1/holes/{hole_id}", json={"score": 7, "putts": 3})
    assert hole_response.status_code == 200
    assert hole_response.json()["data"]["score"] == 7

    shot_response = client.patch(f"/api/v1/shots/{shot_id}", json={"club": "3W", "distance": 210})
    assert shot_response.status_code == 200
    assert shot_response.json()["data"]["club"] == "3W"

    recalculate_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")
    assert recalculate_response.status_code == 200
    assert recalculate_response.json()["data"]["computed_status"] == "pending"
    assert recalculate_response.json()["data"]["analytics_job_status"] == "queued"
    run_analysis_job_in_session(
        db_session,
        UUID(recalculate_response.json()["data"]["analytics_job_id"]),
    )

    round_ = db_session.get(Round, UUID(round_id))
    assert round_ is not None
    assert round_.total_score is not None
    assert round_.computed_status == "ready"


def test_rounds_are_owner_scoped(client: TestClient) -> None:
    register(client, "a@example.com")
    round_id = create_committed_round(client)
    client.post("/api/v1/auth/logout")

    register(client, "b@example.com")

    assert client.get(f"/api/v1/rounds/{round_id}").status_code == 404
    denied_patch = client.patch(f"/api/v1/rounds/{round_id}", json={"course_name": "Nope"})
    assert denied_patch.status_code == 404
    assert client.delete(f"/api/v1/rounds/{round_id}").status_code == 404


def test_delete_round_hides_it_from_list(client: TestClient) -> None:
    register(client)
    round_id = create_committed_round(client)

    delete_response = client.delete(f"/api/v1/rounds/{round_id}")
    assert delete_response.status_code == 204

    list_response = client.get("/api/v1/rounds")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["total"] == 0
