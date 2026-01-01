"""
Chat API tests.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from src.models import ChatbotService, ConversationSession


class TestChatbotInfo:
    """Tests for chatbot info endpoint."""

    @pytest.mark.asyncio
    async def test_get_chatbot_info(self, client: AsyncClient, chatbot: ChatbotService):
        """Test getting chatbot public info."""
        response = await client.get(f"/api/v1/chat/{chatbot.access_url}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == chatbot.name
        assert "greeting" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_chatbot(self, client: AsyncClient):
        """Test getting non-existent chatbot."""
        response = await client.get("/api/v1/chat/nonexistent-bot")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_inactive_chatbot(
        self, client: AsyncClient, inactive_chatbot: ChatbotService
    ):
        """Test getting inactive chatbot returns 404."""
        response = await client.get(f"/api/v1/chat/{inactive_chatbot.access_url}")

        assert response.status_code == 404


class TestSessionManagement:
    """Tests for session management."""

    @pytest.mark.asyncio
    async def test_create_session(self, client: AsyncClient, chatbot: ChatbotService):
        """Test creating a new chat session."""
        with patch("src.services.stats_service.StatsService.increment_session_count", new_callable=AsyncMock):
            response = await client.post(f"/api/v1/chat/{chatbot.access_url}/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["chatbot_id"] == chatbot.id
        assert data["message_count"] == 0

    @pytest.mark.asyncio
    async def test_create_session_with_initial_message(
        self, client: AsyncClient, chatbot: ChatbotService, mock_llm, mock_qdrant
    ):
        """Test creating session with initial message."""
        with patch("src.services.stats_service.StatsService.increment_session_count", new_callable=AsyncMock), \
             patch("src.services.stats_service.StatsService.increment_message_count", new_callable=AsyncMock), \
             patch("src.services.retrieval.retrieve_context", new_callable=AsyncMock) as mock_retrieve:

            mock_retrieve.return_value = {
                "context": "Test context",
                "citations": [],
                "vector_count": 1,
                "graph_count": 0,
            }

            response = await client.post(
                f"/api/v1/chat/{chatbot.access_url}/sessions",
                json={"initial_message": "Hello, I have a question"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["message_count"] == 2  # User + Assistant
        assert data["initial_response"] is not None
        assert data["initial_response"]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_session(
        self, client: AsyncClient, chatbot: ChatbotService, chat_session: ConversationSession
    ):
        """Test getting session details."""
        response = await client.get(
            f"/api/v1/chat/{chatbot.access_url}/sessions/{chat_session.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == chat_session.id
        assert "messages" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(
        self, client: AsyncClient, chatbot: ChatbotService
    ):
        """Test getting non-existent session."""
        response = await client.get(
            f"/api/v1/chat/{chatbot.access_url}/sessions/nonexistent-session-id"
        )

        assert response.status_code == 404


class TestMessageSending:
    """Tests for message sending."""

    @pytest.mark.asyncio
    async def test_send_message_non_streaming(
        self,
        client: AsyncClient,
        chatbot: ChatbotService,
        chat_session: ConversationSession,
        mock_llm,
        mock_qdrant,
    ):
        """Test sending message with non-streaming response."""
        with patch("src.services.stats_service.StatsService.increment_message_count", new_callable=AsyncMock), \
             patch("src.services.retrieval.retrieve_context", new_callable=AsyncMock) as mock_retrieve:

            mock_retrieve.return_value = {
                "context": "Test context from documents",
                "citations": [{"filename": "test.pdf", "page_num": 1}],
                "vector_count": 1,
                "graph_count": 0,
            }

            response = await client.post(
                f"/api/v1/chat/{chatbot.access_url}/sessions/{chat_session.id}/messages",
                json={"content": "What is the company policy?", "stream": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["role"] == "assistant"
        assert "content" in data

    @pytest.mark.asyncio
    async def test_send_message_empty_content(
        self,
        client: AsyncClient,
        chatbot: ChatbotService,
        chat_session: ConversationSession,
    ):
        """Test sending message with empty content."""
        response = await client.post(
            f"/api/v1/chat/{chatbot.access_url}/sessions/{chat_session.id}/messages",
            json={"content": "", "stream": False},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_send_message_to_nonexistent_session(
        self, client: AsyncClient, chatbot: ChatbotService
    ):
        """Test sending message to non-existent session."""
        response = await client.post(
            f"/api/v1/chat/{chatbot.access_url}/sessions/nonexistent-id/messages",
            json={"content": "Hello", "stream": False},
        )

        assert response.status_code == 404


class TestStopGeneration:
    """Tests for stop generation endpoint."""

    @pytest.mark.asyncio
    async def test_stop_generation(
        self,
        client: AsyncClient,
        chatbot: ChatbotService,
        chat_session: ConversationSession,
    ):
        """Test stopping response generation."""
        with patch("src.core.redis.RedisClient.set_cancel_token", new_callable=AsyncMock) as mock_cancel:
            response = await client.post(
                f"/api/v1/chat/{chatbot.access_url}/sessions/{chat_session.id}/stop"
            )

        assert response.status_code == 204
        mock_cancel.assert_called_once_with(chat_session.id, expire_seconds=60)

    @pytest.mark.asyncio
    async def test_stop_generation_nonexistent_session(
        self, client: AsyncClient, chatbot: ChatbotService
    ):
        """Test stopping generation for non-existent session."""
        response = await client.post(
            f"/api/v1/chat/{chatbot.access_url}/sessions/nonexistent-id/stop"
        )

        assert response.status_code == 404
