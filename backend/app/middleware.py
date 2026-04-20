import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        with structlog.contextvars.bound_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        ):
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response
