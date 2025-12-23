"""
Logging configuration and request logging middleware.
"""
import logging
import sys
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings


def setup_logging():
    """Configure application logging."""
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {logging.getLevelName(log_level)}")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]

        # Start timer
        start_time = time.perf_counter()

        # Get logger
        logger = logging.getLogger("api.request")

        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - Started"
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        log_level = logging.INFO if response.status_code < 400 else logging.WARNING
        logger.log(
            log_level,
            f"[{request_id}] {request.method} {request.url.path} - "
            f"{response.status_code} ({duration_ms:.2f}ms)"
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


def setup_request_logging(app):
    """Add request logging middleware to the app."""
    app.add_middleware(RequestLoggingMiddleware)
