"""
ChatbotService SQLAlchemy model.
"""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.admin_user import AdminUser
    from src.models.document import Document
    from src.models.conversation import ConversationSession
    from src.models.index_version import IndexVersion
    from src.models.stats import ChatbotStats


class ChatbotStatus(str, Enum):
    """Chatbot service status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROCESSING = "processing"


class ChatbotService(Base):
    """Chatbot service instance."""

    __tablename__ = "chatbot_services"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Foreign key
    admin_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Fields
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    persona: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default={"tone": "professional", "language": "ko"},
    )
    status: Mapped[ChatbotStatus] = mapped_column(
        SQLEnum(ChatbotStatus, name="chatbot_status", create_type=False),
        nullable=False,
        default=ChatbotStatus.PROCESSING,
        index=True,
    )
    access_url: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    active_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    llm_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="LLM model override for this chatbot. If null, uses system default.",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    admin: Mapped["AdminUser"] = relationship(
        "AdminUser",
        back_populates="chatbots",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="chatbot",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["ConversationSession"]] = relationship(
        "ConversationSession",
        back_populates="chatbot",
        cascade="all, delete-orphan",
    )
    versions: Mapped[list["IndexVersion"]] = relationship(
        "IndexVersion",
        back_populates="chatbot",
        cascade="all, delete-orphan",
    )
    stats: Mapped[list["ChatbotStats"]] = relationship(
        "ChatbotStats",
        back_populates="chatbot",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ChatbotService {self.name} ({self.access_url})>"

    @property
    def is_active(self) -> bool:
        """Check if chatbot is active."""
        return self.status == ChatbotStatus.ACTIVE
