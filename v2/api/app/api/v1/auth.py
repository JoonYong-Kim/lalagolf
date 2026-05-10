import json
import secrets
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.auth import (
    ClubBagSchema,
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.club_bags import get_club_bag, set_club_bag
from app.services.auth import (
    DuplicateEmailError,
    InvalidCredentialsError,
    OAuthEmailNotVerifiedError,
    authenticate_user,
    create_session,
    create_user,
    get_or_create_google_user,
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


def google_oauth_configured(settings: AppSettings) -> bool:
    return bool(settings.google_oauth_client_id and settings.google_oauth_client_secret)


def require_google_oauth(settings: AppSettings) -> None:
    if not google_oauth_configured(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )


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


@router.get("/google/status")
def google_status(settings: AppSettings) -> dict[str, dict[str, bool]]:
    return {"data": {"configured": google_oauth_configured(settings)}}


@router.get("/google/start")
def start_google_login(settings: AppSettings) -> RedirectResponse:
    require_google_oauth(settings)
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")
    response.set_cookie(
        key=settings.google_oauth_state_cookie_name,
        value=state,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=10 * 60,
        path="/api/v1/auth/google",
    )
    return response


@router.get("/google/callback")
def google_callback(
    code: str,
    state: str,
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> RedirectResponse:
    require_google_oauth(settings)
    expected_state = request.cookies.get(settings.google_oauth_state_cookie_name)
    if not expected_state or not secrets.compare_digest(expected_state, state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    google_user = fetch_google_userinfo(code=code, settings=settings)
    try:
        user = get_or_create_google_user(
            db,
            email=google_user["email"],
            display_name=google_user.get("name") or google_user["email"].split("@", 1)[0],
            avatar_url=google_user.get("picture"),
            email_verified=google_user.get("email_verified") is True,
        )
    except OAuthEmailNotVerifiedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google email is not verified",
        ) from exc

    token, _session = create_session(
        db,
        user=user,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    response = RedirectResponse(f"{settings.web_base_url.rstrip('/')}/upload")
    set_session_cookie(response, token=token, settings=settings)
    response.delete_cookie(settings.google_oauth_state_cookie_name, path="/api/v1/auth/google")
    return response


def fetch_google_userinfo(*, code: str, settings: AppSettings) -> dict[str, Any]:
    token_payload = {
        "code": code,
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "grant_type": "authorization_code",
    }
    token_response = post_form("https://oauth2.googleapis.com/token", token_payload)
    id_token = token_response.get("id_token")
    if not isinstance(id_token, str):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Google token missing")

    info = get_json(f"https://oauth2.googleapis.com/tokeninfo?{urlencode({'id_token': id_token})}")
    if info.get("aud") != settings.google_oauth_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Google token")
    email = info.get("email")
    if not isinstance(email, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google email missing")
    return info


def post_form(url: str, payload: dict[str, str | None]) -> dict[str, Any]:
    body = urlencode({key: value for key, value in payload.items() if value is not None}).encode()
    request = UrlRequest(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    return read_json(request)


def get_json(url: str) -> dict[str, Any]:
    return read_json(UrlRequest(url, method="GET"))


def read_json(request: UrlRequest) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google OAuth failed",
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Google OAuth failed")
    return payload


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


@account_router.get("/me/club-bag")
def read_club_bag(
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, ClubBagSchema]:
    return {"data": ClubBagSchema(**get_club_bag(db, owner=current_user))}


@account_router.put("/me/club-bag")
def write_club_bag(
    payload: ClubBagSchema,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, ClubBagSchema]:
    bag = set_club_bag(db, owner=current_user, bag=payload.model_dump())
    return {"data": ClubBagSchema(**bag)}


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
