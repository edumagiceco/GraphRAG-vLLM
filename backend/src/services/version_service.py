"""
Version service for managing index versions.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.index_version import IndexVersion, VersionStatus
from src.models.chatbot_service import ChatbotService

logger = logging.getLogger(__name__)


class VersionService:
    """Service for managing chatbot index versions."""

    @staticmethod
    async def get_versions(
        db: AsyncSession,
        chatbot_id: str,
    ) -> list[IndexVersion]:
        """
        Get all versions for a chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID

        Returns:
            List of IndexVersion objects
        """
        result = await db.execute(
            select(IndexVersion)
            .where(IndexVersion.chatbot_id == chatbot_id)
            .order_by(IndexVersion.version.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_version(
        db: AsyncSession,
        chatbot_id: str,
        version: int,
    ) -> Optional[IndexVersion]:
        """
        Get a specific version.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            version: Version number

        Returns:
            IndexVersion or None
        """
        result = await db.execute(
            select(IndexVersion).where(
                and_(
                    IndexVersion.chatbot_id == chatbot_id,
                    IndexVersion.version == version,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_version(
        db: AsyncSession,
        chatbot_id: str,
    ) -> Optional[IndexVersion]:
        """
        Get the active version for a chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID

        Returns:
            Active IndexVersion or None
        """
        result = await db.execute(
            select(IndexVersion).where(
                and_(
                    IndexVersion.chatbot_id == chatbot_id,
                    IndexVersion.status == VersionStatus.ACTIVE,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_next_version_number(
        db: AsyncSession,
        chatbot_id: str,
    ) -> int:
        """
        Get the next version number for a chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID

        Returns:
            Next version number
        """
        result = await db.execute(
            select(func.max(IndexVersion.version)).where(
                IndexVersion.chatbot_id == chatbot_id
            )
        )
        max_version = result.scalar()
        return (max_version or 0) + 1

    @staticmethod
    async def create_version(
        db: AsyncSession,
        chatbot_id: str,
        status: VersionStatus = VersionStatus.BUILDING,
    ) -> IndexVersion:
        """
        Create a new version for a chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            status: Initial status

        Returns:
            Created IndexVersion
        """
        version_number = await VersionService.get_next_version_number(db, chatbot_id)

        version = IndexVersion(
            id=str(uuid4()),
            chatbot_id=chatbot_id,
            version=version_number,
            status=status,
        )

        db.add(version)
        await db.commit()
        await db.refresh(version)

        logger.info(f"Created version {version_number} for chatbot {chatbot_id}")
        return version

    @staticmethod
    async def update_status(
        db: AsyncSession,
        chatbot_id: str,
        version: int,
        status: VersionStatus,
    ) -> Optional[IndexVersion]:
        """
        Update version status.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            version: Version number
            status: New status

        Returns:
            Updated IndexVersion or None
        """
        version_obj = await VersionService.get_version(db, chatbot_id, version)

        if not version_obj:
            return None

        version_obj.status = status

        if status == VersionStatus.ACTIVE:
            version_obj.activated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(version_obj)

        logger.info(
            f"Updated version {version} status to {status.value} "
            f"for chatbot {chatbot_id}"
        )
        return version_obj

    @staticmethod
    async def activate_version(
        db: AsyncSession,
        chatbot_id: str,
        version: int,
    ) -> Optional[IndexVersion]:
        """
        Activate a version, deactivating any other active version.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            version: Version number to activate

        Returns:
            Activated IndexVersion or None
        """
        # Get the version to activate
        version_obj = await VersionService.get_version(db, chatbot_id, version)

        if not version_obj:
            return None

        if version_obj.status not in (VersionStatus.READY, VersionStatus.ACTIVE):
            logger.warning(
                f"Cannot activate version {version} with status {version_obj.status}"
            )
            return None

        # Deactivate any currently active version
        current_active = await VersionService.get_active_version(db, chatbot_id)
        if current_active and current_active.version != version:
            current_active.status = VersionStatus.ARCHIVED
            logger.info(f"Archived version {current_active.version}")

        # Activate the new version
        version_obj.status = VersionStatus.ACTIVE
        version_obj.activated_at = datetime.utcnow()

        # Update chatbot's active_version
        chatbot_result = await db.execute(
            select(ChatbotService).where(ChatbotService.id == chatbot_id)
        )
        chatbot = chatbot_result.scalar_one_or_none()
        if chatbot:
            chatbot.active_version = version

        await db.commit()
        await db.refresh(version_obj)

        logger.info(f"Activated version {version} for chatbot {chatbot_id}")
        return version_obj

    @staticmethod
    async def mark_ready(
        db: AsyncSession,
        chatbot_id: str,
        version: int,
    ) -> Optional[IndexVersion]:
        """
        Mark a version as ready (finished building).

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            version: Version number

        Returns:
            Updated IndexVersion or None
        """
        return await VersionService.update_status(
            db, chatbot_id, version, VersionStatus.READY
        )

    @staticmethod
    async def delete_version(
        db: AsyncSession,
        chatbot_id: str,
        version: int,
    ) -> bool:
        """
        Delete a version (cannot delete active version).

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            version: Version number

        Returns:
            True if deleted, False otherwise
        """
        version_obj = await VersionService.get_version(db, chatbot_id, version)

        if not version_obj:
            return False

        if version_obj.status == VersionStatus.ACTIVE:
            logger.warning(f"Cannot delete active version {version}")
            return False

        await db.delete(version_obj)
        await db.commit()

        logger.info(f"Deleted version {version} for chatbot {chatbot_id}")
        return True

    @staticmethod
    async def get_or_create_initial_version(
        db: AsyncSession,
        chatbot_id: str,
    ) -> IndexVersion:
        """
        Get or create an initial version for a new chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID

        Returns:
            IndexVersion
        """
        versions = await VersionService.get_versions(db, chatbot_id)

        if versions:
            return versions[0]  # Return latest

        # Create version 1
        version = IndexVersion(
            id=str(uuid4()),
            chatbot_id=chatbot_id,
            version=1,
            status=VersionStatus.ACTIVE,
            activated_at=datetime.utcnow(),
        )

        db.add(version)
        await db.commit()
        await db.refresh(version)

        return version
