from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AnalysisJob, Round
from tests.test_rounds_api import create_committed_round
from tests.test_uploads_api import register


def test_analysis_inline_fallback_completes_job_without_worker(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_settings()
    previous = settings.analysis_inline_fallback
    settings.analysis_inline_fallback = True
    try:
        register(client, "inline@example.com")
        round_id = create_committed_round(client)

        recalc = client.post(f"/api/v1/rounds/{round_id}/recalculate")
        assert recalc.status_code == 200
        body = recalc.json()["data"]
        assert body["analytics_job_status"] == "succeeded"

        job = db_session.get(AnalysisJob, UUID(body["analytics_job_id"]))
        assert job is not None
        assert job.status == "succeeded"

        round_ = db_session.get(Round, UUID(round_id))
        assert round_ is not None
        assert round_.computed_status == "ready"
        assert round_.total_score is not None
    finally:
        settings.analysis_inline_fallback = previous


def test_analysis_inline_fallback_disabled_keeps_job_queued(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_settings()
    assert settings.analysis_inline_fallback is False

    register(client, "queued@example.com")
    round_id = create_committed_round(client)

    recalc = client.post(f"/api/v1/rounds/{round_id}/recalculate")
    assert recalc.status_code == 200
    body = recalc.json()["data"]
    assert body["analytics_job_status"] == "queued"

    job = db_session.get(AnalysisJob, UUID(body["analytics_job_id"]))
    assert job is not None
    assert job.status == "queued"
    assert job.rq_job_id is None
