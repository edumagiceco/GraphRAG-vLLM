"""
Document SQLAlchemy model.
"""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import String, Text, Integer, BigInteger, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.chatbot_service import ChatbotService


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    EXTRACTING = "extracting"
    GRAPHING = "graphing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """Uploaded PDF document."""

    __tablename__ = "documents"

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
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus, name="document_status", create_type=False),
        nullable=False,
        default=DocumentStatus.PENDING,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    page_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    processing_progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    chunk_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    entity_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    chatbot: Mapped["ChatbotService"] = relationship(
        "ChatbotService",
        back_populates="documents",
    )

    def __repr__(self) -> str:
        return f"<Document {self.filename} ({self.status.value})>"

    @property
    def is_completed(self) -> bool:
        """Check if document processing is completed."""
        return self.status == DocumentStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if document processing failed."""
        return self.status == DocumentStatus.FAILED

    @property
    def is_processing(self) -> bool:
        """Check if document is currently being processed."""
        return self.status not in [DocumentStatus.COMPLETED, DocumentStatus.FAILED, DocumentStatus.PENDING]
