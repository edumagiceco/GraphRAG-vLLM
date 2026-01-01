"""
Chatbot management API tests.
"""
import pytest
from httpx import AsyncClient

from src.models import ChatbotService, ChatbotStatus


class TestChatbotList:
    """Tests for chatbot list endpoint."""

    @pytest.mark.asyncio
    async def test_list_chatbots_unauthorized(self, client: AsyncClient):
        """Test listing chatbots without authentication."""
        response = await client.get("/api/v1/chatbots")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_chatbots_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing chatbots when none exist."""
        response = await client.get(
            "/api/v1/chatbots",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_chatbots_with_data(
        self, client: AsyncClient, auth_headers: dict, chatbot: ChatbotService
    ):
        """Test listing chatbots with existing data."""
        response = await client.get(
            "/api/v1/chatbots",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(item["id"] == chatbot.id for item in data["items"])


class TestChatbotCreate:
    """Tests for chatbot creation."""

    @pytest.mark.asyncio
    async def test_create_chatbot(self, client: AsyncClient, auth_headers: dict):
        """Test creating a new chatbot."""
        response = await client.post(
            "/api/v1/chatbots",
            headers=auth_headers,
            json={
                "name": "New Test Bot",
                "access_url": "new-test-bot",
                "persona": {
                    "name": "Helper",
                    "greeting": "Hi there!",
                    "system_prompt": "You are helpful.",
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Test Bot"
        assert data["access_url"] == "new-test-bot"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_chatbot_duplicate_url(
        self, client: AsyncClient, auth_headers: dict, chatbot: ChatbotService
    ):
        """Test creating chatbot with duplicate access URL."""
        response = await client.post(
            "/api/v1/chatbots",
            headers=auth_headers,
            json={
                "name": "Duplicate Bot",
                "access_url": chatbot.access_url,  # Duplicate
                "persona": {},
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_chatbot_invalid_url(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating chatbot with invalid access URL."""
        response = await client.post(
            "/api/v1/chatbots",
            headers=auth_headers,
            json={
                "name": "Invalid URL Bot",
                "access_url": "Invalid URL With Spaces!",
                "persona": {},
            },
        )

        assert response.status_code == 422


class TestChatbotRead:
    """Tests for reading chatbot details."""

    @pytest.mark.asyncio
    async def test_get_chatbot(
        self, client: AsyncClient, auth_headers: dict, chatbot: ChatbotService
    ):
        """Test getting chatbot details."""
        response = await client.get(
            f"/api/v1/chatbots/{chatbot.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == chatbot.id
        assert data["name"] == chatbot.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_chatbot(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent chatbot."""
        response = await client.get(
            "/api/v1/chatbots/nonexistent-id",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestChatbotUpdate:
    """Tests for chatbot updates."""

    @pytest.mark.asyncio
    async def test_update_chatbot(
        self, client: AsyncClient, auth_headers: dict, chatbot: ChatbotService
    ):
        """Test updating chatbot."""
        response = await client.put(
            f"/api/v1/chatbots/{chatbot.id}",
            headers=auth_headers,
            json={
                "name": "Updated Name",
                "persona": {"greeting": "Updated greeting"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_chatbot_status(
        self, client: AsyncClient, auth_headers: dict, chatbot: ChatbotService
    ):
        """Test updating chatbot status."""
        response = await client.put(
            f"/api/v1/chatbots/{chatbot.id}",
            headers=auth_headers,
            json={"status": "inactive"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"


class TestChatbotDelete:
    """Tests for chatbot deletion."""

    @pytest.mark.asyncio
    async def test_delete_chatbot(
        self, client: AsyncClient, auth_headers: dict, chatbot: ChatbotService
    ):
        """Test deleting chatbot."""
        response = await client.delete(
            f"/api/v1/chatbots/{chatbot.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify deletion
        get_response = await client.get(
            f"/api/v1/chatbots/{chatbot.id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_chatbot(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting non-existent chatbot."""
        response = await client.delete(
            "/api/v1/chatbots/nonexistent-id",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestChatbotStats:
    """Tests for chatbot statistics."""

    @pytest.mark.asyncio
    async def test_get_chatbot_stats(
        self, client: AsyncClient, auth_headers: dict, chatbot: ChatbotService
    ):
        """Test getting chatbot statistics."""
        response = await client.get(
            f"/api/v1/chatbots/{chatbot.id}/stats",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data or "period_days" in data
