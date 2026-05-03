from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.share import (
    ShareCreateRequest,
    ShareCreateResponse,
    SharedRoundResponse,
    ShareResponse,
    ShareUpdateRequest,
)
from app.services.shares import (
    ShareNotFoundError,
    create_share,
    get_shared_round,
    list_shares,
    share_create_response,
    share_response,
    update_share,
)

router = APIRouter(tags=["shares"])


@router.post("/shares", status_code=status.HTTP_201_CREATED)
def create_round_share(
    payload: ShareCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, ShareCreateResponse]:
    try:
        share, token = create_share(
            db,
            owner=current_user,
            round_id=payload.round_id,
            title=payload.title,
            expires_at=payload.expires_at,
        )
    except ShareNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc
    return {"data": ShareCreateResponse(**share_create_response(share, token))}


@router.get("/shares")
def read_shares(db: DbSession, current_user: CurrentUser) -> dict[str, list[ShareResponse]]:
    shares = list_shares(db, owner=current_user)
    return {"data": [ShareResponse(**share_response(share)) for share in shares]}


@router.patch("/shares/{share_id}")
def patch_share(
    share_id: UUID,
    payload: ShareUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, ShareResponse]:
    try:
        share = update_share(
            db,
            owner=current_user,
            share_id=share_id,
            title=payload.title,
            expires_at=payload.expires_at,
            revoked=payload.revoked,
        )
    except ShareNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        ) from exc
    return {"data": ShareResponse(**share_response(share))}


@router.get("/shared/{token}")
def read_shared_round(token: str, db: DbSession) -> dict[str, SharedRoundResponse]:
    try:
        payload = get_shared_round(db, token=token)
    except ShareNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        ) from exc
    return {"data": SharedRoundResponse(**payload)}
