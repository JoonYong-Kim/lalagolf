from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models import AnalysisJob, Round, User
from app.models.constants import COMPUTED_STATUS_FAILED, COMPUTED_STATUS_PENDING
from app.services.analytics import recalculate_round_metrics

ANALYSIS_JOB_KIND_ROUND_RECALCULATION = "round_recalculation"


class AnalysisJobNotFoundError(Exception):
    pass


def enqueue_round_analysis_job(
    db: Session,
    *,
    owner: User,
    round_: Round,
    settings: Settings,
) -> AnalysisJob:
    round_.computed_status = COMPUTED_STATUS_PENDING
    existing_job = db.scalars(
        select(AnalysisJob)
        .where(
            AnalysisJob.user_id == owner.id,
            AnalysisJob.round_id == round_.id,
            AnalysisJob.kind == ANALYSIS_JOB_KIND_ROUND_RECALCULATION,
            AnalysisJob.status.in_(("queued", "running")),
        )
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    ).first()
    if existing_job is not None:
        if existing_job.status == "queued" and existing_job.rq_job_id is None:
            rq_job_id = _try_enqueue_rq_job(existing_job.id, settings=settings)
            if rq_job_id is not None:
                existing_job.rq_job_id = rq_job_id
        db.commit()
        db.refresh(existing_job)
        return existing_job

    job = AnalysisJob(
        user_id=owner.id,
        round_id=round_.id,
        kind=ANALYSIS_JOB_KIND_ROUND_RECALCULATION,
        status="queued",
        payload={"round_id": str(round_.id)},
    )
    db.add(job)
    db.flush()

    rq_job_id = _try_enqueue_rq_job(job.id, settings=settings)
    if rq_job_id is not None:
        job.rq_job_id = rq_job_id
    db.commit()
    db.refresh(job)
    return job


def get_analysis_job(db: Session, *, owner: User, job_id: uuid.UUID) -> AnalysisJob:
    job = db.scalars(
        select(AnalysisJob).where(AnalysisJob.id == job_id, AnalysisJob.user_id == owner.id)
    ).first()
    if job is None:
        raise AnalysisJobNotFoundError
    return job


def get_latest_round_analysis_job(
    db: Session,
    *,
    owner: User,
    round_id: uuid.UUID,
) -> AnalysisJob:
    job = db.scalars(
        select(AnalysisJob)
        .where(
            AnalysisJob.user_id == owner.id,
            AnalysisJob.round_id == round_id,
            AnalysisJob.kind == ANALYSIS_JOB_KIND_ROUND_RECALCULATION,
        )
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    ).first()
    if job is None:
        raise AnalysisJobNotFoundError
    return job


def retry_analysis_job(
    db: Session,
    *,
    owner: User,
    job_id: uuid.UUID,
    settings: Settings,
) -> AnalysisJob:
    job = get_analysis_job(db, owner=owner, job_id=job_id)
    if job.status in {"queued", "running", "succeeded"}:
        return job

    round_ = db.get(Round, job.round_id)
    if round_ is None or round_.user_id != owner.id or round_.deleted_at is not None:
        raise AnalysisJobNotFoundError
    return enqueue_round_analysis_job(db, owner=owner, round_=round_, settings=settings)


def run_analysis_job(job_id: str) -> dict[str, Any]:
    job_uuid = uuid.UUID(job_id)
    with SessionLocal() as db:
        return run_analysis_job_in_session(db, job_uuid)


def run_analysis_job_in_session(db: Session, job_id: uuid.UUID) -> dict[str, Any]:
    job = db.get(AnalysisJob, job_id)
    if job is None:
        raise AnalysisJobNotFoundError

    job.status = "running"
    job.attempts += 1
    job.started_at = datetime.now(UTC)
    job.error_message = None
    db.commit()

    owner = db.get(User, job.user_id)
    round_ = db.get(Round, job.round_id)
    if owner is None or round_ is None:
        job.status = "failed"
        job.error_message = "Analysis job owner or round no longer exists"
        job.finished_at = datetime.now(UTC)
        db.commit()
        return {"job_id": str(job.id), "status": job.status}

    round_id = round_.id
    try:
        result = recalculate_round_metrics(db, owner=owner, round_id=round_id)
    except Exception as exc:
        db.rollback()
        failed_job = db.get(AnalysisJob, job_id)
        failed_round = db.get(Round, round_id)
        if failed_job is not None:
            failed_job.status = "failed"
            failed_job.error_message = str(exc)
            failed_job.finished_at = datetime.now(UTC)
        if failed_round is not None:
            failed_round.computed_status = COMPUTED_STATUS_FAILED
        db.commit()
        raise

    completed_job = db.get(AnalysisJob, job_id)
    if completed_job is not None:
        completed_job.status = "succeeded"
        completed_job.error_message = None
        completed_job.finished_at = datetime.now(UTC)
        completed_job.payload = {
            **(completed_job.payload or {}),
            "result": _json_safe_payload(result),
        }
    db.commit()
    return {"job_id": str(job_id), "status": "succeeded", **result}


def _try_enqueue_rq_job(job_id: uuid.UUID, *, settings: Settings) -> str | None:
    if not settings.analysis_enqueue_enabled:
        return None
    try:
        from rq import Queue
    except ImportError:
        return None

    redis = Redis.from_url(settings.redis_url)
    queue = Queue(settings.analysis_queue_name, connection=redis)
    try:
        rq_job = queue.enqueue(
            "app.services.analysis_jobs.run_analysis_job",
            str(job_id),
            job_id=str(job_id),
        )
    except Exception:
        return None
    return rq_job.id


def _json_safe_payload(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe_payload(item) for item in value]
    return value


def enqueue_pending_analysis_jobs_once(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    count = 0
    with SessionLocal() as db:
        jobs = db.scalars(
            select(AnalysisJob)
            .where(AnalysisJob.status == "queued", AnalysisJob.rq_job_id.is_(None))
            .order_by(AnalysisJob.created_at.asc())
            .limit(100)
        ).all()
        for job in jobs:
            rq_job_id = _try_enqueue_rq_job(job.id, settings=settings)
            if rq_job_id is not None:
                job.rq_job_id = rq_job_id
                count += 1
        db.commit()
    return count
