from collections.abc import Generator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import AnalysisJob, Hole, Round, Shot, SourceFile, UploadReview


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with SessionLocal() as session:
        yield session

    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session: Session, tmp_path: Path) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    settings = get_settings()
    settings.upload_storage_dir = str(tmp_path / "uploads")
    settings.upload_max_bytes = 100_000

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as test_client:
        yield test_client


def register(client: TestClient, email: str = "user@example.com") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "strong-password",
            "display_name": "Lala Golfer",
        },
    )
    assert response.status_code == 201


def sample_round_text() -> str:
    return "\n".join(
        [
            "2026-04-11 13:23",
            "베르힐 영종",
            "홍성걸 양명욱 임길수",
            "1P4",
            "D C C",
            "I7 C C",
            "IP B B",
            "P B B 12 OK",
            "2P5",
            "D C C OB",
            "UW B B",
            "56 B B 50",
            "P C C 8",
            "P C C 2 OK",
        ]
    )


def upload_round(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/uploads/round-file",
        files={"file": ("round.txt", sample_round_text().encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_upload_round_file_creates_review_and_job(client: TestClient, db_session: Session) -> None:
    register(client)

    data = upload_round(client)

    assert data["status"] == "needs_review"
    assert data["upload_review_id"] == data["job_id"]

    source_file = db_session.get(SourceFile, UUID(data["source_file_id"]))
    review = db_session.get(UploadReview, UUID(data["upload_review_id"]))
    assert source_file is not None
    assert source_file.status == "parsed"
    assert source_file.content_hash
    assert review is not None
    assert review.parsed_round["course_name"] == "베르힐 영종"

    job_response = client.get(f"/api/v1/jobs/{data['job_id']}")
    assert job_response.status_code == 200
    assert job_response.json()["data"]["status"] == "completed"


def test_upload_review_is_owner_scoped(client: TestClient) -> None:
    register(client, "a@example.com")
    data = upload_round(client)
    client.post("/api/v1/auth/logout")

    register(client, "b@example.com")
    response = client.get(f"/api/v1/uploads/{data['upload_review_id']}/review")

    assert response.status_code == 404


def test_update_review_and_commit_creates_private_round_rows(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    data = upload_round(client)

    patch_response = client.patch(
        f"/api/v1/uploads/{data['upload_review_id']}/review",
        json={
            "user_edits": {
                "course_name": "Edited CC",
                "play_date": "2026-04-12",
                "holes": [
                    {
                        "hole_number": 1,
                        "par": 4,
                        "score": 5,
                        "putts": 2,
                        "shots": [
                            {
                                "shot_number": 1,
                                "club": "D",
                                "club_normalized": "D",
                                "distance": 220,
                                "start_lie": "T",
                                "end_lie": "F",
                                "result_grade": "B",
                                "feel_grade": "C",
                                "penalty_type": "H",
                                "score_cost": 1,
                            }
                        ],
                    }
                ],
            }
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["user_edits"]["course_name"] == "Edited CC"
    assert patch_response.json()["data"]["parsed_round"]["course_name"] == "Edited CC"
    assert patch_response.json()["data"]["parsed_round"]["total_score"] == 5
    assert patch_response.json()["data"]["parsed_round"]["holes"][0]["penalties"] == 1

    commit_response = client.post(
        f"/api/v1/uploads/{data['upload_review_id']}/commit",
        json={"share_course": False, "share_exact_date": False},
    )

    assert commit_response.status_code == 200
    round_id = commit_response.json()["data"]["round_id"]
    analytics_job_id = commit_response.json()["data"]["analytics_job_id"]
    round_ = db_session.get(Round, UUID(round_id))
    analytics_job = db_session.get(AnalysisJob, UUID(analytics_job_id))
    assert round_ is not None
    assert analytics_job is not None
    assert analytics_job.round_id == round_.id
    assert analytics_job.status == "queued"
    assert round_.course_name == "Edited CC"
    assert round_.play_date.isoformat() == "2026-04-12"
    assert round_.visibility == "private"
    assert round_.computed_status == "pending"
    assert round_.hole_count == 1
    assert round_.total_score == 5

    holes = db_session.scalars(select(Hole).where(Hole.round_id == round_.id)).all()
    shots = db_session.scalars(select(Shot).where(Shot.round_id == round_.id)).all()
    assert len(holes) == 1
    assert len(shots) == 1
    assert any(shot.penalty_type == "H" and shot.penalty_strokes == 1 for shot in shots)

    review = db_session.get(UploadReview, UUID(data["upload_review_id"]))
    assert review is not None
    assert str(review.committed_round_id) == round_id
    assert review.status == "committed"


def test_update_review_raw_content_reparses_source_file(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    data = upload_round(client)

    review_response = client.get(f"/api/v1/uploads/{data['upload_review_id']}/review")
    assert review_response.status_code == 200
    raw_content = review_response.json()["data"]["raw_content"]
    assert "베르힐 영종" in raw_content

    edited_raw = raw_content.replace("베르힐 영종", "Edited Raw CC")
    patch_response = client.patch(
        f"/api/v1/uploads/{data['upload_review_id']}/review/raw",
        json={"raw_content": edited_raw},
    )

    assert patch_response.status_code == 200
    payload = patch_response.json()["data"]
    assert payload["parsed_round"]["course_name"] == "Edited Raw CC"
    assert payload["raw_content"] == edited_raw
    assert payload["user_edits"] == {}

    source_file = db_session.get(SourceFile, UUID(data["source_file_id"]))
    assert source_file is not None
    stored_raw = (Path(get_settings().upload_storage_dir) / source_file.storage_key).read_text()
    assert stored_raw == edited_raw


def test_upload_review_raw_content_falls_back_when_source_file_missing(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    data = upload_round(client)

    review = db_session.get(UploadReview, UUID(data["upload_review_id"]))
    assert review is not None
    source_file = db_session.get(SourceFile, UUID(data["source_file_id"]))
    assert source_file is not None

    raw_path = Path(get_settings().upload_storage_dir) / source_file.storage_key
    raw_path.unlink()

    response = client.get(f"/api/v1/uploads/{data['upload_review_id']}/review")
    assert response.status_code == 200
    raw_content = response.json()["data"]["raw_content"]
    assert raw_content is not None
    assert "베르힐 영종" in raw_content
    assert "1 P4" in raw_content


def test_upload_commit_forbids_visibility_field(client: TestClient) -> None:
    register(client)
    data = upload_round(client)

    response = client.post(
        f"/api/v1/uploads/{data['upload_review_id']}/commit",
        json={"visibility": "public", "share_course": True, "share_exact_date": True},
    )

    assert response.status_code == 422
