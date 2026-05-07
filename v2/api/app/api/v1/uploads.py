import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.upload import (
    JobResponse,
    UploadCommitRequest,
    UploadCommitResponse,
    UploadReviewRawUpdateRequest,
    UploadReviewResponse,
    UploadReviewUpdateRequest,
    UploadRoundFileResponse,
)
from app.services.uploads import (
    UploadError,
    UploadNotFoundError,
    UploadNotReadyError,
    commit_upload_review,
    create_round_file_upload,
    get_upload_job,
    get_upload_review,
    get_upload_review_raw_content,
    update_upload_review_edits,
    update_upload_review_raw_content,
)

router = APIRouter(tags=["uploads"])
logger = logging.getLogger("lalagolf.api.uploads")


@router.post(
    "/uploads/round-file",
    status_code=status.HTTP_201_CREATED,
)
async def upload_round_file(
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
) -> dict[str, UploadRoundFileResponse]:
    content = await file.read()
    try:
        review = create_round_file_upload(
            db,
            owner=current_user,
            filename=file.filename or "round.txt",
            content_type=file.content_type,
            content=content,
            settings=settings,
        )
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    logger.info(
        "upload parse completed",
        extra={
            "job_id": str(review.id),
            "source_file_id": str(review.source_file_id),
            "status": review.status,
        },
    )
    return {
        "data": UploadRoundFileResponse(
            source_file_id=review.source_file_id,
            upload_review_id=review.id,
            status=review.status,
            job_id=review.id,
        )
    }


@router.get("/uploads/{upload_review_id}/review")
def read_upload_review(
    upload_review_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> dict[str, UploadReviewResponse]:
    try:
        review = get_upload_review(db, owner=current_user, upload_review_id=upload_review_id)
    except UploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        ) from exc

    return {"data": _review_response(review, settings=settings)}


@router.patch("/uploads/{upload_review_id}/review")
def update_upload_review(
    upload_review_id: UUID,
    payload: UploadReviewUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> dict[str, UploadReviewResponse]:
    try:
        review = update_upload_review_edits(
            db,
            owner=current_user,
            upload_review_id=upload_review_id,
            user_edits=payload.user_edits,
        )
    except UploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        ) from exc

    return {"data": _review_response(review, settings=settings)}


@router.patch("/uploads/{upload_review_id}/review/raw")
def update_upload_review_raw(
    upload_review_id: UUID,
    payload: UploadReviewRawUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> dict[str, UploadReviewResponse]:
    try:
        review = update_upload_review_raw_content(
            db,
            owner=current_user,
            upload_review_id=upload_review_id,
            raw_content=payload.raw_content,
            settings=settings,
        )
    except UploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        ) from exc
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"data": _review_response(review, settings=settings)}


@router.post("/uploads/{upload_review_id}/commit")
def commit_upload(
    upload_review_id: UUID,
    payload: UploadCommitRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, UploadCommitResponse]:
    try:
        round_ = commit_upload_review(
            db,
            owner=current_user,
            upload_review_id=upload_review_id,
            visibility=payload.visibility,
            share_course=payload.share_course,
            share_exact_date=payload.share_exact_date,
        )
    except UploadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        ) from exc
    except UploadNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload not ready",
        ) from exc
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    logger.info(
        "upload commit completed",
        extra={
            "job_id": str(round_.id),
            "upload_review_id": str(upload_review_id),
            "round_id": str(round_.id),
            "computed_status": round_.computed_status,
        },
    )
    return {
        "data": UploadCommitResponse(
            round_id=round_.id,
            computed_status=round_.computed_status,
            analytics_job_id=round_.id,
        )
    }


@router.get("/jobs/{job_id}")
def read_job(
    job_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, JobResponse]:
    try:
        job = get_upload_job(db, owner=current_user, job_id=job_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc

    return {"data": JobResponse(**job)}


def _review_response(review, *, settings: AppSettings) -> UploadReviewResponse:
    return UploadReviewResponse(
        id=review.id,
        status=review.status,
        parsed_round=review.parsed_round,
        warnings=review.warnings,
        user_edits=review.user_edits,
        committed_round_id=review.committed_round_id,
        raw_content=get_upload_review_raw_content(review, settings=settings),
    )
