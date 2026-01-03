"""
IndexVersion SQLAlchemy model.
"""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.chatbot_service import ChatbotService


class VersionStatus(str, Enum):
    """Index version status."""
    BUILDING = "building"
    READY = "ready"
    ACTIVE = "active"
    ARCHIVED = "archived"


class IndexVersion(Base):
    """Index version for a chatbot's knowledge base."""

    __tablename__ = "index_versions"
    __table_args__ = (
        UniqueConstraint("chatbot_id", "version", name="uq_chatbot_version"),
    )

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Foreign key
    chatbot_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("chatbot_services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Fields
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    status: Mapped[VersionStatus] = mapped_column(
        SQLEnum(
            VersionStatus,
            name="version_status",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj]
        ),
        nullable=False,
        default=VersionStatus.BUILDING,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Relationships
    chatbot: Mapped["ChatbotService"] = relationship(
        "ChatbotService",
        back_populates="versions",
    )

    def __repr__(self) -> str:
        return f"<IndexVersion v{self.version} ({self.status.value})>"

    @property
    def is_active(self) -> bool:
        """Check if version is currently active."""
        return self.status == VersionStatus.ACTIVE

    @property
    def is_ready(self) -> bool:
        """Check if version is ready to be activated."""
        return self.status == VersionStatus.READY

    def activate(self) -> None:
        """Mark version as active."""
        self.status = VersionStatus.ACTIVE
        self.activated_at = datetime.utcnow()

    def archive(self) -> None:
        """Archive the version."""
        self.status = VersionStatus.ARCHIVED
