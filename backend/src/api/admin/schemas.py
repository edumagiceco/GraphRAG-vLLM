"""
Admin API schemas for chatbot management.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.models.chatbot_service import ChatbotStatus


class PersonaConfig(BaseModel):
    """Chatbot persona configuration."""

    name: str = Field(..., min_length=1, max_length=50, description="Persona name")
    description: str = Field(
        ..., min_length=1, max_length=500, description="Persona description"
    )
    greeting: str = Field(
        default="안녕하세요! 무엇을 도와드릴까요?",
        max_length=500,
        description="Initial greeting message",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Custom system prompt for LLM",
    )


class CreateChatbotRequest(BaseModel):
    """Request schema for creating a chatbot."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Chatbot service name",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Chatbot description",
    )
    persona: PersonaConfig = Field(..., description="Chatbot persona configuration")
    access_url: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
        description="Unique URL slug for public access (lowercase alphanumeric and hyphens)",
    )
    llm_model: Optional[str] = Field(
        default=None,
        max_length=100,
        description="LLM model override for this chatbot. If null, uses system default.",
    )

    @field_validator("access_url")
    @classmethod
    def validate_access_url(cls, v: str) -> str:
        """Validate access URL format."""
        if "--" in v:
            raise ValueError("Access URL cannot contain consecutive hyphens")
        reserved = ["admin", "api", "login", "logout", "auth", "chat", "static"]
        if v.lower() in reserved:
            raise ValueError(f"Access URL '{v}' is reserved")
        return v.lower()


class UpdateChatbotRequest(BaseModel):
    """Request schema for updating a chatbot."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Chatbot service name",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Chatbot description",
    )
    persona: Optional[PersonaConfig] = Field(
        default=None, description="Chatbot persona configuration"
    )
    llm_model: Optional[str] = Field(
        default=None,
        max_length=100,
        description="LLM model override for this chatbot. Set to empty string to use system default.",
    )


class ChatbotStatusUpdate(BaseModel):
    """Request schema for updating chatbot status."""

    status: ChatbotStatus = Field(..., description="New chatbot status")


class ChatbotResponse(BaseModel):
    """Response schema for chatbot."""

    id: str = Field(..., description="Chatbot ID")
    name: str = Field(..., description="Chatbot name")
    description: Optional[str] = Field(None, description="Chatbot description")
    status: ChatbotStatus = Field(..., description="Current status")
    access_url: str = Field(..., description="Public access URL slug")
    document_count: int = Field(default=0, description="Number of documents")
    llm_model: Optional[str] = Field(None, description="LLM model override (null = use default)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class ChatbotDetailResponse(ChatbotResponse):
    """Detailed chatbot response with persona."""

    persona: PersonaConfig = Field(..., description="Persona configuration")
    active_version: int = Field(default=1, description="Active index version")
    effective_llm_model: str = Field(
        ..., description="Actual LLM model used (chatbot-specific or system default)"
    )

    model_config = {"from_attributes": True}


class ChatbotListResponse(BaseModel):
    """Response schema for chatbot list."""

    items: list[ChatbotResponse] = Field(..., description="List of chatbots")
    total: int = Field(..., description="Total count")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Items per page")
