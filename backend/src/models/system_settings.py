"""
SystemSettings SQLAlchemy model.
Stores system-wide configuration settings.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class SystemSettings(Base):
    """System-wide settings storage."""

    __tablename__ = "system_settings"

    # Primary key - setting key
    key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    # Value stored as text (JSON serialized for complex types)
    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Description for documentation
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
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

    def __repr__(self) -> str:
        return f"<SystemSettings {self.key}={self.value[:50]}...>"


# Setting key constants
class SettingKeys:
    """Constants for system setting keys."""
    DEFAULT_LLM_MODEL = "default_llm_model"
    EMBEDDING_MODEL = "embedding_model"
    EMBEDDING_DIMENSION = "embedding_dimension"
    OLLAMA_BASE_URL = "ollama_base_url"
