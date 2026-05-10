from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AppSettings, CurrentAdmin, DbSession
from app.models import AnalysisJob, Round, SourceFile, UploadReview, User
from app.services.analysis_jobs import enqueue_round_analysis_job

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/uploads/errors")
def list_upload_errors(
    db: DbSession,
    _admin: CurrentAdmin,
    limit: int = 50,
) -> dict[str, list[dict[str, object]]]:
    reviews = db.scalars(
        select(UploadReview)
        .options(selectinload(UploadReview.source_file))
        .where(UploadReview.status == "failed")
        .order_by(UploadReview.created_at.desc())
        .limit(min(max(limit, 1), 100))
    ).all()

    return {
        "data": [
            {
                "id": review.id,
                "source_file_id": review.source_file_id,
                "filename": _source_filename(review.source_file),
                "status": review.status,
                "warnings": review.warnings,
                "created_at": review.created_at,
            }
            for review in reviews
        ]
    }


def _source_filename(source_file: SourceFile | None) -> str | None:
    if source_file is None:
        return None
    return source_file.filename


@router.get("/analysis/jobs")
def list_failed_analysis_jobs(
    db: DbSession,
    _admin: CurrentAdmin,
    limit: int = 50,
) -> dict[str, list[dict[str, object]]]:
    rows = db.execute(
        select(AnalysisJob, Round, User)
        .join(Round, Round.id == AnalysisJob.round_id)
        .join(User, User.id == AnalysisJob.user_id)
        .where(AnalysisJob.status == "failed")
        .order_by(AnalysisJob.created_at.desc())
        .limit(min(max(limit, 1), 100))
    ).all()

    return {
        "data": [
            _analysis_job_payload(job=job, round_=round_, user=user)
            for job, round_, user in rows
        ]
    }


@router.post("/analysis/jobs/{job_id}/retry")
def retry_failed_analysis_job(
    job_id: UUID,
    db: DbSession,
    _admin: CurrentAdmin,
    settings: AppSettings,
) -> dict[str, dict[str, object]]:
    row = db.execute(
        select(AnalysisJob, Round, User)
        .join(Round, Round.id == AnalysisJob.round_id)
        .join(User, User.id == AnalysisJob.user_id)
        .where(AnalysisJob.id == job_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job, round_, user = row
    retried_job = job
    if job.status == "failed":
        retried_job = enqueue_round_analysis_job(db, owner=user, round_=round_, settings=settings)

    return {
        "data": _analysis_job_payload(job=retried_job, round_=round_, user=user),
    }


def _analysis_job_payload(
    *,
    job: AnalysisJob,
    round_: Round,
    user: User,
) -> dict[str, object]:
    return {
        "id": job.id,
        "user_id": job.user_id,
        "user_email": user.email,
        "round_id": job.round_id,
        "course_name": round_.course_name,
        "play_date": round_.play_date,
        "kind": job.kind,
        "status": job.status,
        "rq_job_id": job.rq_job_id,
        "attempts": job.attempts,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }
