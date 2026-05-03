from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.auth import LoginRequest, ProfileUpdateRequest, RegisterRequest, UserResponse
from app.services.auth import (
    DuplicateEmailError,
    InvalidCredentialsError,
    authenticate_user,
    create_session,
    create_user,
    revoke_session,
)

router = APIRouter(prefix="/auth", tags=["auth"])
account_router = APIRouter(tags=["auth"])


def set_session_cookie(response: Response, *, token: str, settings: AppSettings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_lifetime_days * 24 * 60 * 60,
        path="/",
    )


def user_payload(user: CurrentUser) -> dict[str, UserResponse]:
    return {"user": UserResponse.model_validate(user)}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: DbSession,
    settings: AppSettings,
) -> dict[str, dict[str, UserResponse]]:
    try:
        user = create_user(
            db,
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc

    token, _session = create_session(
        db,
        user=user,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_session_cookie(response, token=token, settings=settings)
    return {"data": user_payload(user)}


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
    settings: AppSettings,
) -> dict[str, dict[str, UserResponse]]:
    try:
        user = authenticate_user(db, email=payload.email, password=payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc

    token, _session = create_session(
        db,
        user=user,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_session_cookie(response, token=token, settings=settings)
    return {"data": user_payload(user)}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: DbSession,
    settings: AppSettings,
) -> dict[str, dict[str, bool]]:
    session_token = request.cookies.get(settings.session_cookie_name)
    if session_token:
        revoke_session(db, token=session_token, settings=settings)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"data": {"ok": True}}


@account_router.get("/me")
def me(current_user: CurrentUser) -> dict[str, dict[str, UserResponse]]:
    return {"data": user_payload(current_user)}


@account_router.patch("/me/profile")
def update_profile(
    payload: ProfileUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, dict[str, UserResponse]]:
    if payload.display_name is not None:
        current_user.display_name = payload.display_name.strip()

    if current_user.profile is None:
        from app.models import UserProfile

        current_user.profile = UserProfile()

    profile = current_user.profile
    for field in (
        "bio",
        "home_course",
        "handicap_target",
        "privacy_default",
        "share_course_by_default",
        "share_exact_date_by_default",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(profile, field, value)

    db.commit()
    db.refresh(current_user)
    return {"data": user_payload(current_user)}
