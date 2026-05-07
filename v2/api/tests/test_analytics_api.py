from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExpectedScoreTable, Insight, Round, RoundMetric, ShotValue
from app.services.insight_i18n import render_insight_payload
from tests.test_rounds_api import create_committed_round
from tests.test_uploads_api import register


def test_recalculate_persists_analysis_and_is_idempotent(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    round_id = create_committed_round(client)

    first_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")
    second_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["data"]["computed_status"] == "ready"

    round_ = db_session.get(Round, UUID(round_id))
    assert round_ is not None
    assert round_.computed_status == "ready"

    metrics = db_session.scalars(select(RoundMetric).where(RoundMetric.round_id == round_.id)).all()
    shot_values = db_session.scalars(select(ShotValue).where(ShotValue.round_id == round_.id)).all()
    expected_tables = db_session.scalars(
        select(ExpectedScoreTable).where(ExpectedScoreTable.user_id == round_.user_id)
    ).all()
    insights = db_session.scalars(select(Insight).where(Insight.user_id == round_.user_id)).all()

    assert {metric.metric_key for metric in metrics} >= {"total_score", "putts_total"}
    assert len(shot_values) > 0
    assert len(expected_tables) == 1
    assert len([insight for insight in insights if insight.status == "active"]) <= 3
    assert len({insight.dedupe_key for insight in insights}) == len(insights)


def test_analysis_endpoints_and_insight_dismissal(client: TestClient) -> None:
    register(client)
    round_id = create_committed_round(client)
    client.post(f"/api/v1/rounds/{round_id}/recalculate")

    trends_response = client.get("/api/v1/analytics/trends")
    assert trends_response.status_code == 200
    trends = trends_response.json()["data"]
    assert trends["score_trend"]
    assert len(trends["insights"]) <= 3

    round_response = client.get(f"/api/v1/analytics/rounds/{round_id}")
    assert round_response.status_code == 200
    assert round_response.json()["data"]["shot_values"]
    first_value = round_response.json()["data"]["shot_values"][0]
    assert {"expected_before", "expected_after", "shot_cost"} <= set(first_value)

    compare_response = client.get("/api/v1/analytics/compare?group_by=category")
    assert compare_response.status_code == 200
    assert compare_response.json()["data"]["group_by"] == "category"

    insights_response = client.get("/api/v1/insights")
    assert insights_response.status_code == 200
    insights = insights_response.json()["data"]
    assert insights

    dismiss_response = client.patch(
        f"/api/v1/insights/{insights[0]['id']}",
        json={"status": "dismissed"},
    )
    assert dismiss_response.status_code == 200
    assert dismiss_response.json()["data"]["status"] == "dismissed"


def test_insights_support_english_locale(client: TestClient) -> None:
    register(client)
    round_id = create_committed_round(client)
    client.post(f"/api/v1/rounds/{round_id}/recalculate")

    trends_response = client.get("/api/v1/analytics/trends?locale=en")

    assert trends_response.status_code == 200
    insights = trends_response.json()["data"]["insights"]
    assert insights
    assert any("Penalties" in insight["problem"] for insight in insights)


def test_insight_renderer_keeps_korean_default() -> None:
    payload = {
        "category": "penalty_impact",
        "root_cause": "penalty_strokes",
        "primary_evidence_metric": "penalty_strokes",
        "problem": "페널티가 스코어를 직접 밀어 올립니다.",
        "evidence": "저장된 라운드에서 페널티가 총 3타 기록됐습니다.",
        "impact": "페널티 1타는 회복 샷까지 이어져 실제 손실이 더 커질 수 있습니다.",
        "next_action": "위험 홀이 보이면 티샷 목표 폭과 세이프 클럽 기준을 먼저 정하세요.",
    }

    assert render_insight_payload(payload, locale="ko")["problem"] == payload["problem"]
    assert render_insight_payload(payload, locale="en")["problem"].startswith("Penalties")


def test_analysis_is_owner_scoped(client: TestClient) -> None:
    register(client, "a@example.com")
    round_id = create_committed_round(client)
    client.post(f"/api/v1/rounds/{round_id}/recalculate")
    client.post("/api/v1/auth/logout")

    register(client, "b@example.com")

    assert client.get(f"/api/v1/analytics/rounds/{round_id}").status_code == 404
    assert client.post(f"/api/v1/rounds/{round_id}/recalculate").status_code == 404
