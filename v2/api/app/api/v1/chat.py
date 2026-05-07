from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatMessagePairResponse,
    ChatMessageResponse,
    ChatThreadCreateRequest,
    ChatThreadDetailResponse,
    ChatThreadResponse,
)
from app.services.chat import (
    ChatNotFoundError,
    add_message,
    chat_status,
    create_thread,
    get_thread,
    list_threads,
    message_response,
    thread_response,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/status")
def read_chat_status(settings: AppSettings) -> dict[str, dict]:
    return {"data": chat_status(settings)}


@router.post("/threads", status_code=status.HTTP_201_CREATED)
def create_chat_thread(
    payload: ChatThreadCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, ChatThreadResponse]:
    thread = create_thread(db, owner=current_user, title=payload.title)
    return {"data": ChatThreadResponse(**thread_response(thread))}


@router.get("/threads")
def read_chat_threads(
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, list[ChatThreadResponse]]:
    threads = list_threads(db, owner=current_user)
    return {"data": [ChatThreadResponse(**thread_response(thread)) for thread in threads]}


@router.get("/threads/{thread_id}")
def read_chat_thread(
    thread_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, ChatThreadDetailResponse]:
    try:
        thread, messages = get_thread(db, owner=current_user, thread_id=thread_id)
    except ChatNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        ) from exc
    return {
        "data": ChatThreadDetailResponse(
            **thread_response(thread),
            messages=[ChatMessageResponse(**message_response(message)) for message in messages],
        )
    }


@router.post("/threads/{thread_id}/messages", status_code=status.HTTP_201_CREATED)
def create_chat_message(
    thread_id: UUID,
    payload: ChatMessageCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> dict[str, ChatMessagePairResponse]:
    try:
        user_message, assistant_message = add_message(
            db,
            owner=current_user,
            thread_id=thread_id,
            content=payload.content,
            settings=settings,
        )
    except ChatNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        ) from exc

    return {
        "data": ChatMessagePairResponse(
            user_message=ChatMessageResponse(**message_response(user_message)),
            assistant_message=ChatMessageResponse(**message_response(assistant_message)),
        )
    }
