"""
Pytest configuration and fixtures for GraphRAG backend tests.
"""
import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

from src.core.database import Base, get_db
from src.models import (
    AdminUser,
    ChatbotService,
    ChatbotStatus,
    Document,
    ConversationSession,
    Message,
    MessageRole,
)


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine with SQLite in-memory."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


# =============================================================================
# Application Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def app(test_engine, db_session) -> FastAPI:
    """Create test FastAPI application."""
    from src.main import app as main_app

    # Override database dependency
    async def override_get_db():
        yield db_session

    main_app.dependency_overrides[get_db] = override_get_db

    yield main_app

    main_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Model Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> AdminUser:
    """Create test admin user."""
    from src.core.security import get_password_hash

    user = AdminUser(
        id=str(uuid4()),
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def superuser(db_session: AsyncSession) -> AdminUser:
    """Create test superuser."""
    from src.core.security import get_password_hash

    user = AdminUser(
        id=str(uuid4()),
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def chatbot(db_session: AsyncSession) -> ChatbotService:
    """Create test chatbot."""
    bot = ChatbotService(
        id=str(uuid4()),
        name="Test Chatbot",
        access_url="test-chatbot",
        status=ChatbotStatus.ACTIVE,
        persona={
            "name": "Test Bot",
            "greeting": "Hello! How can I help you?",
            "system_prompt": "You are a helpful assistant.",
        },
    )
    db_session.add(bot)
    await db_session.commit()
    await db_session.refresh(bot)
    return bot


@pytest_asyncio.fixture
async def inactive_chatbot(db_session: AsyncSession) -> ChatbotService:
    """Create inactive test chatbot."""
    bot = ChatbotService(
        id=str(uuid4()),
        name="Inactive Chatbot",
        access_url="inactive-chatbot",
        status=ChatbotStatus.INACTIVE,
        persona={},
    )
    db_session.add(bot)
    await db_session.commit()
    await db_session.refresh(bot)
    return bot


@pytest_asyncio.fixture
async def chat_session(db_session: AsyncSession, chatbot: ChatbotService) -> ConversationSession:
    """Create test chat session."""
    session = ConversationSession(
        id=str(uuid4()),
        chatbot_id=chatbot.id,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, admin_user: AdminUser) -> dict:
    """Get authentication headers for test user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def superuser_headers(client: AsyncClient, superuser: AdminUser) -> dict:
    """Get authentication headers for superuser."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("src.core.redis.RedisClient") as mock:
        mock.get_client = AsyncMock(return_value=None)
        mock.is_cancelled = AsyncMock(return_value=False)
        mock.set_cancel_token = AsyncMock()
        mock.clear_cancel_token = AsyncMock()
        mock.exists = AsyncMock(return_value=False)
        yield mock


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client."""
    mock_client = MagicMock()
    mock_client.search = MagicMock(return_value=[])
    mock_client.get_collections = MagicMock(return_value=MagicMock(collections=[]))

    with patch("src.services.retrieval.vector_search.QdrantClient", return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_llm():
    """Mock LLM generator."""
    with patch("src.services.chat_service.get_answer_generator") as mock:
        generator = AsyncMock()
        generator.generate = AsyncMock(return_value="This is a test response.")
        generator.generate_stream = AsyncMock()
        mock.return_value = generator
        yield generator


@pytest.fixture
def mock_embedding():
    """Mock embedding model."""
    with patch("src.core.embeddings.get_embedding_model") as mock:
        model = AsyncMock()
        model.embed_query = AsyncMock(return_value=[0.1] * 1024)
        model.embed_texts = AsyncMock(return_value=[[0.1] * 1024])
        mock.return_value = model
        yield model
