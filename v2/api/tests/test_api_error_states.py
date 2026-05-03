from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SourceFile, UploadReview
from tests.test_uploads_api import register


def test_private_api_errors_are_consistent_without_auth(client: TestClient) -> None:
    upload_response = client.post(
        "/api/v1/uploads/round-file",
        files={"file": ("round.txt", b"1P4\nP B B OK", "text/plain")},
    )
    assert upload_response.status_code == 401
    assert upload_response.json()["detail"] == "Not authenticated"

    assert client.get("/api/v1/rounds").status_code == 401
    assert client.get("/api/v1/analytics/summary").status_code == 401
    assert client.post("/api/v1/chat/threads", json={"title": "Blocked"}).status_code == 401


def test_upload_rejects_oversized_file(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/api/v1/uploads/round-file",
        files={"file": ("too-large.txt", b"x" * 100_001, "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is too large"


def test_upload_rejects_invalid_encoding_and_records_failed_source(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)

    response = client.post(
        "/api/v1/uploads/round-file",
        files={"file": ("bad.txt", b"\xff\xfe\xfa", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file must be UTF-8 text"

    source_file = db_session.scalars(select(SourceFile)).one()
    review = db_session.scalars(select(UploadReview)).one()
    assert source_file.status == "failed"
    assert source_file.parse_error == "Uploaded file must be UTF-8 text"
    assert review.status == "failed"
    assert review.warnings[0]["code"] == "invalid_encoding"


def test_commit_not_ready_upload_returns_conflict(client: TestClient) -> None:
    register(client)

    upload_response = client.post(
        "/api/v1/uploads/round-file",
        files={
            "file": (
                "empty-round.txt",
                b"2026-04-11\nNo Holes CC",
                "text/plain",
            )
        },
    )
    assert upload_response.status_code == 201
    upload_review_id = upload_response.json()["data"]["upload_review_id"]

    response = client.post(
        f"/api/v1/uploads/{upload_review_id}/commit",
        json={"visibility": "private", "share_course": False, "share_exact_date": False},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Upload not ready"


def test_unknown_job_returns_not_found(client: TestClient) -> None:
    register(client)

    response = client.get(f"/api/v1/jobs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"
