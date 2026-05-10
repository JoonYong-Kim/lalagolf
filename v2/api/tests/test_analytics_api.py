from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisJob,
    AnalysisSnapshot,
    ExpectedScoreTable,
    Insight,
    Round,
    RoundMetric,
    ShotValue,
)
from app.services.analysis_jobs import run_analysis_job_in_session
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
    run_analysis_job_in_session(
        db_session,
        UUID(first_response.json()["data"]["analytics_job_id"]),
    )
    run_analysis_job_in_session(
        db_session,
        UUID(second_response.json()["data"]["analytics_job_id"]),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["data"]["computed_status"] == "pending"

    round_ = db_session.get(Round, UUID(round_id))
    assert round_ is not None
    assert round_.computed_status == "ready"

    metrics = db_session.scalars(select(RoundMetric).where(RoundMetric.round_id == round_.id)).all()
    shot_values = db_session.scalars(select(ShotValue).where(ShotValue.round_id == round_.id)).all()
    expected_tables = db_session.scalars(
        select(ExpectedScoreTable).where(ExpectedScoreTable.user_id == round_.user_id)
    ).all()
    insights = db_session.scalars(select(Insight).where(Insight.user_id == round_.user_id)).all()
    snapshots = db_session.scalars(
        select(AnalysisSnapshot)
        .where(
            AnalysisSnapshot.user_id == round_.user_id,
            AnalysisSnapshot.scope_type == "analytics_trends",
            AnalysisSnapshot.scope_key == "all",
        )
        .order_by(AnalysisSnapshot.created_at.asc())
    ).all()

    assert {metric.metric_key for metric in metrics} >= {"total_score", "putts_total"}
    assert len(shot_values) > 0
    assert len(expected_tables) == 1
    assert expected_tables[0].scope_type == "round_baseline"
    assert expected_tables[0].scope_key == f"round:{round_.id}:prior_recent:10"
    assert {value.expected_source_scope for value in shot_values} == {expected_tables[0].scope_key}
    assert len([insight for insight in insights if insight.status == "active"]) <= 3
    assert len({insight.dedupe_key for insight in insights}) == len(insights)
    assert len(snapshots) == 1
    assert snapshots[-1].payload["kpis"]["round_count"] == 1
    assert snapshots[-1].payload["category_summary"]


def test_round_recalculation_uses_prior_recent_round_baseline(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    first_round_id = create_committed_round(client)
    second_round_id = create_committed_round(client)

    first_response = client.post(f"/api/v1/rounds/{first_round_id}/recalculate")
    second_response = client.post(f"/api/v1/rounds/{second_round_id}/recalculate")
    run_analysis_job_in_session(
        db_session,
        UUID(first_response.json()["data"]["analytics_job_id"]),
    )
    run_analysis_job_in_session(
        db_session,
        UUID(second_response.json()["data"]["analytics_job_id"]),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_round = db_session.get(Round, UUID(first_round_id))
    second_round = db_session.get(Round, UUID(second_round_id))
    assert first_round is not None
    assert second_round is not None

    first_table = db_session.scalar(
        select(ExpectedScoreTable).where(
            ExpectedScoreTable.user_id == first_round.user_id,
            ExpectedScoreTable.scope_type == "round_baseline",
            ExpectedScoreTable.scope_key == f"round:{first_round.id}:prior_recent:10",
        )
    )
    second_table = db_session.scalar(
        select(ExpectedScoreTable).where(
            ExpectedScoreTable.user_id == second_round.user_id,
            ExpectedScoreTable.scope_type == "round_baseline",
            ExpectedScoreTable.scope_key == f"round:{second_round.id}:prior_recent:10",
        )
    )
    second_shot_values = db_session.scalars(
        select(ShotValue).where(ShotValue.round_id == second_round.id)
    ).all()

    assert first_table is not None
    assert second_table is not None
    assert first_table.sample_count == 0
    assert second_table.sample_count > 0
    assert {value.expected_source_scope for value in second_shot_values} == {
        second_table.scope_key
    }


def test_recalculate_reuses_pending_analysis_job(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    round_id = create_committed_round(client)

    first_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")
    second_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["data"]["analytics_job_id"] == second_response.json()["data"][
        "analytics_job_id"
    ]

    jobs = db_session.scalars(select(AnalysisJob)).all()
    assert len(jobs) == 1
    assert len([job for job in jobs if job.kind == "round_recalculation"]) == 1


def test_round_latest_analysis_job_endpoint(client: TestClient) -> None:
    register(client)
    round_id = create_committed_round(client)
    recalculate_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")
    job_id = recalculate_response.json()["data"]["analytics_job_id"]

    latest_response = client.get(f"/api/v1/rounds/{round_id}/analysis-job")

    assert latest_response.status_code == 200
    assert latest_response.json()["data"]["id"] == job_id
    assert latest_response.json()["data"]["status"] == "queued"


def test_failed_analysis_job_can_be_retried(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    round_id = create_committed_round(client)
    recalculate_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")
    failed_job_id = UUID(recalculate_response.json()["data"]["analytics_job_id"])
    failed_job = db_session.get(AnalysisJob, failed_job_id)
    assert failed_job is not None
    failed_job.status = "failed"
    failed_job.error_message = "boom"
    db_session.commit()

    retry_response = client.post(f"/api/v1/analysis-jobs/{failed_job_id}/retry")

    assert retry_response.status_code == 200
    retried = retry_response.json()["data"]
    assert retried["id"] != str(failed_job_id)
    assert retried["round_id"] == round_id
    assert retried["status"] == "queued"


def test_analysis_endpoints_and_insight_dismissal(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    round_id = create_committed_round(client)
    recalculate_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")
    job_id = recalculate_response.json()["data"]["analytics_job_id"]
    job_response = client.get(f"/api/v1/analysis-jobs/{job_id}")
    assert job_response.status_code == 200
    assert job_response.json()["data"]["status"] == "queued"
    run_analysis_job_in_session(
        db_session,
        UUID(job_id),
    )
    completed_job_response = client.get(f"/api/v1/analysis-jobs/{job_id}")
    assert completed_job_response.status_code == 200
    assert completed_job_response.json()["data"]["status"] == "succeeded"

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


def test_trends_endpoint_prefers_latest_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    round_id = create_committed_round(client)
    recalculate_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")
    run_analysis_job_in_session(
        db_session,
        UUID(recalculate_response.json()["data"]["analytics_job_id"]),
    )

    round_ = db_session.get(Round, UUID(round_id))
    assert round_ is not None
    snapshot = db_session.scalar(
        select(AnalysisSnapshot)
        .where(
            AnalysisSnapshot.user_id == round_.user_id,
            AnalysisSnapshot.scope_type == "analytics_trends",
            AnalysisSnapshot.scope_key == "all",
        )
        .order_by(AnalysisSnapshot.created_at.desc())
    )
    assert snapshot is not None
    snapshot.payload = {
        **snapshot.payload,
        "kpis": {**snapshot.payload["kpis"], "round_count": 999},
    }
    db_session.commit()

    trends_response = client.get("/api/v1/analytics/trends")

    assert trends_response.status_code == 200
    assert trends_response.json()["data"]["kpis"]["round_count"] == 999


def test_insights_support_english_locale(client: TestClient, db_session: Session) -> None:
    register(client)
    round_id = create_committed_round(client)
    recalculate_response = client.post(f"/api/v1/rounds/{round_id}/recalculate")
    run_analysis_job_in_session(
        db_session,
        UUID(recalculate_response.json()["data"]["analytics_job_id"]),
    )

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
    assert client.get(f"/api/v1/rounds/{round_id}/analysis-job").status_code == 404
