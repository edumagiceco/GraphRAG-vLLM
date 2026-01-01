"""
Authentication API tests.
"""
import pytest
from httpx import AsyncClient

from src.models import AdminUser


class TestLogin:
    """Tests for login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, admin_user: AdminUser):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, admin_user: AdminUser):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_invalid_email_format(self, client: AsyncClient):
        """Test login with invalid email format."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "invalid-email", "password": "password123"},
        )

        assert response.status_code == 422  # Validation error


class TestTokenValidation:
    """Tests for token validation."""

    @pytest.mark.asyncio
    async def test_access_protected_route_with_token(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test accessing protected route with valid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_access_protected_route_without_token(self, client: AsyncClient):
        """Test accessing protected route without token."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_with_invalid_token(self, client: AsyncClient):
        """Test accessing protected route with invalid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


class TestPasswordChange:
    """Tests for password change."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful password change."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
            },
        )

        assert response.status_code == 200

        # Verify can login with new password
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "newpassword456"},
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test password change with wrong current password."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456",
            },
        )

        assert response.status_code == 400


class TestUserInfo:
    """Tests for user info endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict):
        """Test getting current user info."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_superuser_flag(
        self, client: AsyncClient, superuser_headers: dict
    ):
        """Test superuser flag in user info."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=superuser_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_superuser"] is True
