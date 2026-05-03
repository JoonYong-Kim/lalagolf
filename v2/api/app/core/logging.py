import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.core.config import Settings

logger = logging.getLogger("lalagolf.api")


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
    settings: Settings,
) -> Response:
    request_id = request.headers.get(settings.request_id_header) or uuid.uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()
    response: Response | None = None

    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        status_code = response.status_code if response is not None else 500
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": elapsed_ms,
            },
        )
        if response is not None:
            response.headers[settings.request_id_header] = request_id
