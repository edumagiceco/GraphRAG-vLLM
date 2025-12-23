"""
ChatbotStats SQLAlchemy model.
"""
from datetime import date
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Date, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.chatbot_service import ChatbotService


class ChatbotStats(Base):
    """Daily aggregated statistics for a chatbot."""

    __tablename__ = "chatbot_stats"
    __table_args__ = (
        UniqueConstraint("chatbot_id", "date", name="uq_chatbot_date"),
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
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    session_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    message_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    avg_response_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationships
    chatbot: Mapped["ChatbotService"] = relationship(
        "ChatbotService",
        back_populates="stats",
    )

    def __repr__(self) -> str:
        return f"<ChatbotStats {self.date}: {self.session_count} sessions, {self.message_count} messages>"

    def increment_sessions(self, count: int = 1) -> None:
        """Increment session count."""
        self.session_count += count

    def increment_messages(self, count: int = 1) -> None:
        """Increment message count."""
        self.message_count += count
