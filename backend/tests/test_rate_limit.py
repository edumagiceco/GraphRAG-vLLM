"""
Integration tests for rate limiting middleware.
"""
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.rate_limit import (
    RateLimiter,
    RateLimitMiddleware,
    RateLimitExceeded,
    setup_rate_limiting,
    get_rate_limiter,
)


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter instance for testing."""
        return RateLimiter(
            requests_per_minute=5,
            requests_per_hour=100,
            prefix="test_rate_limit",
        )

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        return request

    def test_get_client_id_from_ip(self, rate_limiter, mock_request):
        """Test client ID extraction from IP address."""
        client_id = rate_limiter._get_client_id(mock_request)
        assert client_id == "ip:127.0.0.1"

    def test_get_client_id_from_forwarded_for(self, rate_limiter, mock_request):
        """Test client ID extraction from X-Forwarded-For header."""
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        client_id = rate_limiter._get_client_id(mock_request)
        assert client_id == "ip:192.168.1.1"

    def test_get_client_id_from_bearer_token(self, rate_limiter, mock_request):
        """Test client ID extraction from Bearer token."""
        mock_request.headers = {"Authorization": "Bearer test_token_123"}
        client_id = rate_limiter._get_client_id(mock_request)
        assert client_id.startswith("user:")

    @pytest.mark.asyncio
    async def test_is_allowed_when_redis_unavailable(self, rate_limiter, mock_request):
        """Test that requests are allowed when Redis is unavailable."""
        with patch("src.core.rate_limit.RedisClient.get_client", return_value=None):
            is_allowed, retry_after = await rate_limiter.is_allowed(mock_request)
            assert is_allowed is True
            assert retry_after is None

    @pytest.mark.asyncio
    async def test_is_allowed_within_limit(self, rate_limiter, mock_request):
        """Test that requests within limit are allowed."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True

        with patch(
            "src.core.rate_limit.RedisClient.get_client",
            return_value=mock_redis,
        ):
            is_allowed, retry_after = await rate_limiter.is_allowed(mock_request)
            assert is_allowed is True
            assert retry_after is None

    @pytest.mark.asyncio
    async def test_is_allowed_exceeds_minute_limit(self, rate_limiter, mock_request):
        """Test that requests exceeding minute limit are blocked."""
        mock_redis = AsyncMock()
        mock_redis.incr.return_value = 10  # Exceeds limit of 5

        with patch(
            "src.core.rate_limit.RedisClient.get_client",
            return_value=mock_redis,
        ):
            is_allowed, retry_after = await rate_limiter.is_allowed(mock_request)
            assert is_allowed is False
            assert retry_after is not None
            assert 0 < retry_after <= 60

    @pytest.mark.asyncio
    async def test_get_remaining(self, rate_limiter, mock_request):
        """Test getting remaining request counts."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = [b"3", b"50"]

        with patch(
            "src.core.rate_limit.RedisClient.get_client",
            return_value=mock_redis,
        ):
            remaining = await rate_limiter.get_remaining(mock_request)
            assert remaining["minute_remaining"] == 2  # 5 - 3
            assert remaining["hour_remaining"] == 50  # 100 - 50


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with rate limiting."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        setup_rate_limiting(app, enabled=True)
        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_excluded_paths_not_rate_limited(self, client):
        """Test that excluded paths are not rate limited."""
        # Health endpoint should be excluded
        response = client.get("/health")
        assert response.status_code == 200

    def test_rate_limit_headers_added(self, client):
        """Test that rate limit headers are added to responses."""
        with patch(
            "src.core.rate_limit.RedisClient.get_client",
            return_value=None,
        ):
            response = client.get("/test")
            assert response.status_code == 200
            # Headers should be present when Redis is unavailable (defaults)
            assert "X-RateLimit-Limit-Minute" in response.headers
            assert "X-RateLimit-Remaining-Minute" in response.headers


class TestSetupRateLimiting:
    """Tests for setup_rate_limiting function."""

    def test_setup_rate_limiting_enabled(self):
        """Test that middleware is added when enabled."""
        app = FastAPI()
        initial_middleware_count = len(app.user_middleware)

        setup_rate_limiting(app, enabled=True)

        assert len(app.user_middleware) == initial_middleware_count + 1

    def test_setup_rate_limiting_disabled(self):
        """Test that middleware is not added when disabled."""
        app = FastAPI()
        initial_middleware_count = len(app.user_middleware)

        setup_rate_limiting(app, enabled=False)

        assert len(app.user_middleware) == initial_middleware_count


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""

    def test_rate_limit_exceeded_exception(self):
        """Test RateLimitExceeded exception properties."""
        exc = RateLimitExceeded(retry_after=30)
        assert exc.status_code == 429
        assert "Rate limit exceeded" in exc.detail
        assert exc.headers["Retry-After"] == "30"

    def test_rate_limit_exceeded_default_retry_after(self):
        """Test RateLimitExceeded default retry_after."""
        exc = RateLimitExceeded()
        assert exc.headers["Retry-After"] == "60"


class TestIntegration:
    """Integration tests for rate limiting."""

    @pytest.fixture
    def app_with_rate_limit(self):
        """Create app with strict rate limit for testing."""
        app = FastAPI()

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"status": "ok"}

        @app.get("/api/v1/chat/message")
        async def chat_endpoint():
            return {"message": "Hello"}

        setup_rate_limiting(app, enabled=True)
        return app

    def test_rate_limiting_integration(self, app_with_rate_limit):
        """Test full rate limiting flow."""
        client = TestClient(app_with_rate_limit)

        # Mock Redis to simulate rate limiting
        mock_redis = AsyncMock()
        call_count = 0

        async def mock_incr(key):
            nonlocal call_count
            call_count += 1
            return call_count

        mock_redis.incr = mock_incr
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=b"1")

        with patch(
            "src.core.rate_limit.RedisClient.get_client",
            return_value=mock_redis,
        ):
            # First request should succeed
            response = client.get("/api/v1/test")
            assert response.status_code == 200
