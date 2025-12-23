"""
Chatbot service for CRUD operations.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.chatbot_service import ChatbotService, ChatbotStatus
from src.models.document import Document

logger = logging.getLogger(__name__)


class ChatbotServiceManager:
    """Service for managing chatbot CRUD operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        admin_id: str,
        name: str,
        access_url: str,
        persona: dict,
        description: Optional[str] = None,
    ) -> ChatbotService:
        """
        Create a new chatbot service.

        Args:
            db: Database session
            admin_id: Admin user ID
            name: Chatbot name
            access_url: Unique URL slug
            persona: Persona configuration dict
            description: Optional description

        Returns:
            Created chatbot service

        Raises:
            ValueError: If access_url already exists
        """
        # Check if access_url already exists
        existing = await db.execute(
            select(ChatbotService).where(ChatbotService.access_url == access_url)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Access URL '{access_url}' already exists")

        chatbot = ChatbotService(
            id=str(uuid.uuid4()),
            admin_id=admin_id,
            name=name,
            description=description,
            persona=persona,
            access_url=access_url,
            status=ChatbotStatus.INACTIVE,
            active_version=1,
        )

        db.add(chatbot)
        await db.commit()
        await db.refresh(chatbot)

        return chatbot

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        chatbot_id: str,
        admin_id: Optional[str] = None,
    ) -> Optional[ChatbotService]:
        """
        Get a chatbot by ID.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            admin_id: Optional admin ID to filter by owner

        Returns:
            Chatbot service or None
        """
        query = select(ChatbotService).where(ChatbotService.id == chatbot_id)
        if admin_id:
            query = query.where(ChatbotService.admin_id == admin_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_access_url(
        db: AsyncSession,
        access_url: str,
    ) -> Optional[ChatbotService]:
        """
        Get a chatbot by access URL.

        Args:
            db: Database session
            access_url: Public access URL slug

        Returns:
            Chatbot service or None
        """
        result = await db.execute(
            select(ChatbotService).where(ChatbotService.access_url == access_url)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_admin(
        db: AsyncSession,
        admin_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ChatbotStatus] = None,
    ) -> tuple[list[ChatbotService], int]:
        """
        List chatbots for an admin user.

        Args:
            db: Database session
            admin_id: Admin user ID
            page: Page number (1-indexed)
            page_size: Items per page
            status: Optional status filter

        Returns:
            Tuple of (chatbot list, total count)
        """
        # Base query
        query = select(ChatbotService).where(ChatbotService.admin_id == admin_id)

        if status:
            query = query.where(ChatbotService.status == status)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(ChatbotService.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        chatbots = list(result.scalars().all())

        return chatbots, total

    @staticmethod
    async def update(
        db: AsyncSession,
        chatbot_id: str,
        admin_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        persona: Optional[dict] = None,
    ) -> Optional[ChatbotService]:
        """
        Update a chatbot service.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            admin_id: Admin user ID (for ownership check)
            name: New name
            description: New description
            persona: New persona config

        Returns:
            Updated chatbot or None if not found
        """
        chatbot = await ChatbotServiceManager.get_by_id(db, chatbot_id, admin_id)
        if not chatbot:
            return None

        if name is not None:
            chatbot.name = name
        if description is not None:
            chatbot.description = description
        if persona is not None:
            chatbot.persona = persona

        await db.commit()
        await db.refresh(chatbot)

        return chatbot

    @staticmethod
    async def update_status(
        db: AsyncSession,
        chatbot_id: str,
        admin_id: str,
        status: ChatbotStatus,
    ) -> Optional[ChatbotService]:
        """
        Update chatbot status.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            admin_id: Admin user ID (for ownership check)
            status: New status

        Returns:
            Updated chatbot or None if not found
        """
        chatbot = await ChatbotServiceManager.get_by_id(db, chatbot_id, admin_id)
        if not chatbot:
            return None

        chatbot.status = status
        await db.commit()
        await db.refresh(chatbot)

        return chatbot

    @staticmethod
    async def delete(
        db: AsyncSession,
        chatbot_id: str,
        admin_id: str,
        cleanup_external: bool = True,
    ) -> bool:
        """
        Delete a chatbot service.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            admin_id: Admin user ID (for ownership check)
            cleanup_external: Whether to cleanup Neo4j/Qdrant data

        Returns:
            True if deleted, False if not found
        """
        chatbot = await ChatbotServiceManager.get_by_id(db, chatbot_id, admin_id)
        if not chatbot:
            return False

        # Cleanup external data stores (Neo4j, Qdrant) before deleting from DB
        if cleanup_external:
            try:
                from src.services.cleanup_service import cleanup_chatbot_data

                cleanup_result = await cleanup_chatbot_data(chatbot_id)
                logger.info(f"Cleanup result for {chatbot_id}: {cleanup_result}")
            except Exception as e:
                # Log error but continue with deletion
                logger.error(f"Failed to cleanup external data for {chatbot_id}: {e}")

        await db.delete(chatbot)
        await db.commit()

        return True

    @staticmethod
    async def get_document_count(
        db: AsyncSession,
        chatbot_id: str,
    ) -> int:
        """
        Get document count for a chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID

        Returns:
            Number of documents
        """
        result = await db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.chatbot_id == chatbot_id)
        )
        return result.scalar() or 0
