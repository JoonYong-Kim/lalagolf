from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.social import (
    CompareCandidateResponse,
    FollowCreateRequest,
    FollowResponse,
    FollowStatusUpdateRequest,
    PublicRoundCardResponse,
    PublicRoundDetailResponse,
    RoundCommentCreateRequest,
    RoundCommentResponse,
    RoundLikeResponse,
)
from app.services.social import (
    SocialAccessError,
    SocialNotFoundError,
    add_comment,
    add_like,
    create_follow,
    delete_comment,
    delete_follow,
    follow_payload,
    get_public_round_detail,
    list_comparison_candidates,
    list_follows,
    list_public_rounds,
    list_round_comments,
    load_viewable_round,
    remove_like,
    update_follow,
)

router = APIRouter(tags=["social"])


@router.get("/rounds/public")
def read_public_rounds(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    course: str | None = None,
    handle: str | None = None,
    keyword: str | None = None,
    year: int | None = Query(default=None, ge=1900, le=2200),
) -> dict[str, object]:
    payload = list_public_rounds(
        db,
        limit=limit,
        offset=offset,
        course=course,
        handle=handle,
        keyword=keyword,
        year=year,
    )
    return {
        "data": [PublicRoundCardResponse(**item) for item in payload["items"]],
        "meta": {k: payload[k] for k in ("total", "limit", "offset")},
    }


@router.get("/rounds/public/{round_id}")
def read_public_round(
    round_id: UUID,
    db: DbSession,
    locale: str = Query(default="ko", pattern="^(ko|en)$"),
) -> dict[str, PublicRoundDetailResponse]:
    try:
        payload = get_public_round_detail(db, round_id=round_id, locale=locale)
    except SocialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc
    return {"data": PublicRoundDetailResponse(**payload)}


@router.get("/rounds/{round_id}/comparison-candidates")
def read_comparison_candidates(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, list[CompareCandidateResponse]]:
    try:
        candidates = list_comparison_candidates(db, viewer=current_user, round_id=round_id)
    except SocialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc
    return {"data": [CompareCandidateResponse(**item) for item in candidates]}


@router.post("/follows", status_code=status.HTTP_201_CREATED)
def create_follow_request(
    payload: FollowCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, FollowResponse]:
    try:
        follow = create_follow(db, viewer=current_user, following_id=payload.following_id)
    except SocialAccessError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SocialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from exc
    return {"data": FollowResponse(**follow_payload(db, follow))}


@router.get("/follows")
def read_follows(
    db: DbSession,
    current_user: CurrentUser,
    scope: str = Query(default="all", pattern="^(all|incoming|outgoing)$"),
) -> dict[str, list[FollowResponse]]:
    follows = list_follows(db, viewer=current_user, scope=scope)
    return {"data": [FollowResponse(**follow) for follow in follows]}


@router.patch("/follows/{follower_id}/{following_id}")
def patch_follow(
    follower_id: UUID,
    following_id: UUID,
    payload: FollowStatusUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, FollowResponse]:
    try:
        follow = update_follow(
            db,
            viewer=current_user,
            follower_id=follower_id,
            following_id=following_id,
            status=payload.status,
        )
    except SocialAccessError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SocialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow not found",
        ) from exc
    return {"data": FollowResponse(**follow_payload(db, follow))}


@router.delete("/follows/{follower_id}/{following_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_follow(
    follower_id: UUID,
    following_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    try:
        delete_follow(db, viewer=current_user, follower_id=follower_id, following_id=following_id)
    except SocialAccessError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SocialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow not found",
        ) from exc


@router.post("/rounds/{round_id}/likes")
def like_round(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundLikeResponse]:
    try:
        payload = add_like(db, viewer=current_user, round_id=round_id)
    except SocialAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SocialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc
    return {"data": RoundLikeResponse(**payload)}


@router.delete("/rounds/{round_id}/likes")
def unlike_round(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundLikeResponse]:
    try:
        payload = remove_like(db, viewer=current_user, round_id=round_id)
    except SocialAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SocialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc
    return {"data": RoundLikeResponse(**payload)}


@router.get("/rounds/{round_id}/comments")
def read_round_comments(
    round_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, list[RoundCommentResponse]]:
    try:
        round_ = load_viewable_round(db, viewer=current_user, round_id=round_id)
        comments = list_round_comments(db, viewer=current_user, round_=round_)
    except SocialAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SocialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc
    return {"data": [RoundCommentResponse(**comment) for comment in comments]}


@router.post("/rounds/{round_id}/comments", status_code=status.HTTP_201_CREATED)
def create_round_comment(
    round_id: UUID,
    payload: RoundCommentCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundCommentResponse]:
    try:
        comment = add_comment(
            db,
            viewer=current_user,
            round_id=round_id,
            body=payload.body,
            parent_comment_id=payload.parent_comment_id,
        )
    except SocialAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SocialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found",
        ) from exc
    return {"data": RoundCommentResponse(**comment)}


@router.delete("/rounds/{round_id}/comments/{comment_id}")
def remove_round_comment(
    round_id: UUID,
    comment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, RoundCommentResponse]:
    try:
        comment = delete_comment(db, viewer=current_user, comment_id=comment_id)
    except SocialAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SocialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        ) from exc
    if comment["round_id"] != round_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    return {"data": RoundCommentResponse(**comment)}
