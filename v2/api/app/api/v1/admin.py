from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentAdmin, DbSession
from app.models import SourceFile, UploadReview

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
