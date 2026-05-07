import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import account_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router
from app.api.v1.practice import router as practice_router
from app.api.v1.rounds import analytics_router
from app.api.v1.rounds import router as rounds_router
from app.api.v1.shares import router as shares_router
from app.api.v1.uploads import router as uploads_router
from app.core.config import get_settings
from app.core.logging import request_logging_middleware


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    app = FastAPI(title="LalaGolf v2 API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(account_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(practice_router, prefix="/api/v1")
    app.include_router(rounds_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(shares_router, prefix="/api/v1")
    app.include_router(uploads_router, prefix="/api/v1")

    @app.middleware("http")
    async def add_request_logging(request: Request, call_next):
        return await request_logging_middleware(request, call_next, settings)

    @app.get("/health", tags=["health"])
    def root_health() -> dict[str, str]:
        return {"status": "ok", "service": "api"}

    return app


app = create_app()
