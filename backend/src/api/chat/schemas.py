"""
Chat API schemas.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Message content",
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream the response",
    )


class MessageResponse(BaseModel):
    """Response for a single message."""

    id: str = Field(..., description="Message ID")
    session_id: str = Field(..., description="Session ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    sources: Optional[list[dict]] = Field(None, description="Source citations")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    """Response for a chat session."""

    id: str = Field(..., description="Session ID")
    chatbot_id: str = Field(..., description="Chatbot ID")
    started_at: datetime = Field(..., description="Session start time")
    message_count: int = Field(default=0, description="Number of messages")

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    """Detailed session response with messages."""

    messages: list[MessageResponse] = Field(
        default_factory=list,
        description="Session messages",
    )


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    # Optional initial message
    initial_message: Optional[str] = Field(
        None,
        max_length=4000,
        description="Optional initial message to send",
    )


class ChatbotPublicInfo(BaseModel):
    """Public information about a chatbot."""

    name: str = Field(..., description="Chatbot name")
    persona_name: str = Field(..., description="Persona name")
    greeting: str = Field(..., description="Greeting message")


class StreamChunk(BaseModel):
    """A chunk of streamed response."""

    type: str = Field(..., description="Chunk type: 'content', 'sources', 'done', 'error'")
    content: Optional[str] = Field(None, description="Text content for content chunks")
    sources: Optional[list[dict]] = Field(None, description="Sources for sources chunk")
    error: Optional[str] = Field(None, description="Error message for error chunk")
    message_id: Optional[str] = Field(None, description="Message ID for done chunk")
