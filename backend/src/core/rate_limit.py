"""
API rate limiting using Redis.
"""
import logging
import time
from typing import Optional

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.redis import RedisClient
from src.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


class RateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        prefix: str = "rate_limit",
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.prefix = prefix

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try to get user ID from auth header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Use hashed token as identifier for authenticated users
            token = auth_header[7:]
            return f"user:{hash(token) % 10000000}"

        # Fall back to IP address for unauthenticated requests
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    async def is_allowed(self, request: Request) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed.

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        client_id = self._get_client_id(request)
        current_time = int(time.time())

        try:
            redis = await RedisClient.get_client()
            if not redis:
                # If Redis is unavailable, allow the request
                logger.warning("Redis unavailable for rate limiting")
                return True, None

            # Check minute limit
            minute_key = f"{self.prefix}:{client_id}:minute:{current_time // 60}"
            minute_count = await redis.incr(minute_key)

            if minute_count == 1:
                await redis.expire(minute_key, 60)

            if minute_count > self.requests_per_minute:
                retry_after = 60 - (current_time % 60)
                return False, retry_after

            # Check hour limit
            hour_key = f"{self.prefix}:{client_id}:hour:{current_time // 3600}"
            hour_count = await redis.incr(hour_key)

            if hour_count == 1:
                await redis.expire(hour_key, 3600)

            if hour_count > self.requests_per_hour:
                retry_after = 3600 - (current_time % 3600)
                return False, retry_after

            return True, None

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow request if rate limiting fails
            return True, None

    async def get_remaining(self, request: Request) -> dict:
        """Get remaining requests for client."""
        client_id = self._get_client_id(request)
        current_time = int(time.time())

        try:
            redis = await RedisClient.get_client()
            if not redis:
                return {
                    "minute_remaining": self.requests_per_minute,
                    "hour_remaining": self.requests_per_hour,
                }

            minute_key = f"{self.prefix}:{client_id}:minute:{current_time // 60}"
            hour_key = f"{self.prefix}:{client_id}:hour:{current_time // 3600}"

            minute_count = int(await redis.get(minute_key) or 0)
            hour_count = int(await redis.get(hour_key) or 0)

            return {
                "minute_remaining": max(0, self.requests_per_minute - minute_count),
                "hour_remaining": max(0, self.requests_per_hour - hour_count),
                "minute_limit": self.requests_per_minute,
                "hour_limit": self.requests_per_hour,
            }

        except Exception as e:
            logger.error(f"Failed to get remaining: {e}")
            return {
                "minute_remaining": self.requests_per_minute,
                "hour_remaining": self.requests_per_hour,
            }


# Default rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            requests_per_minute=getattr(settings, 'rate_limit_per_minute', 60),
            requests_per_hour=getattr(settings, 'rate_limit_per_hour', 1000),
        )
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""

    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Skip rate limiting for health check endpoints
        if request.url.path.endswith("/health"):
            return await call_next(request)

        rate_limiter = get_rate_limiter()
        is_allowed, retry_after = await rate_limiter.is_allowed(request)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {request.url.path} - "
                f"retry after {retry_after}s"
            )
            raise RateLimitExceeded(retry_after=retry_after or 60)

        response = await call_next(request)

        # Add rate limit headers
        remaining = await rate_limiter.get_remaining(request)
        response.headers["X-RateLimit-Limit-Minute"] = str(remaining.get("minute_limit", 60))
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining.get("minute_remaining", 60))

        return response


def setup_rate_limiting(app, enabled: bool = True):
    """Setup rate limiting middleware."""
    if enabled:
        app.add_middleware(RateLimitMiddleware)
        logger.info("Rate limiting middleware enabled")
    else:
        logger.info("Rate limiting middleware disabled")
