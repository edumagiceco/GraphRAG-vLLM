"""
Settings API schemas for model configuration.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """Information about an Ollama model."""

    name: str = Field(..., description="Model name (e.g., 'llama2:7b')")
    size: int = Field(..., description="Model size in bytes")
    size_formatted: str = Field(..., description="Human-readable size (e.g., '4.1 GB')")
    modified_at: str = Field(..., description="Last modified timestamp")
    family: Optional[str] = Field(None, description="Model family (e.g., 'llama')")
    parameter_size: Optional[str] = Field(None, description="Parameter size (e.g., '7B')")
    quantization_level: Optional[str] = Field(None, description="Quantization level (e.g., 'Q4_0')")


class SystemSettingsResponse(BaseModel):
    """Response schema for system settings."""

    default_llm_model: str = Field(..., description="Default LLM model for chat")
    embedding_model: str = Field(..., description="Embedding model for vector generation")
    embedding_dimension: int = Field(..., description="Embedding vector dimension")
    ollama_base_url: str = Field(..., description="Ollama server base URL")


class AvailableModelsResponse(BaseModel):
    """Response schema for available models."""

    models: list[ModelInfo] = Field(..., description="All available models")
    chat_models: list[ModelInfo] = Field(..., description="Models suitable for chat")
    embedding_models: list[ModelInfo] = Field(..., description="Models suitable for embedding")
    total: int = Field(..., description="Total number of models")


class UpdateDefaultLLMRequest(BaseModel):
    """Request schema for updating default LLM model."""

    model: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Model name to set as default",
    )


class UpdateEmbeddingModelRequest(BaseModel):
    """Request schema for updating embedding model."""

    model: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Embedding model name",
    )


class ConnectionTestResponse(BaseModel):
    """Response schema for connection test."""

    connected: bool = Field(..., description="Whether connection is successful")
    ollama_version: Optional[str] = Field(None, description="Ollama server version")
    ollama_base_url: str = Field(..., description="Ollama server URL tested")
    error: Optional[str] = Field(None, description="Error message if connection failed")


class ReprocessDocumentsRequest(BaseModel):
    """Request schema for reprocessing documents."""

    chatbot_id: Optional[str] = Field(
        None,
        description="Specific chatbot ID to reprocess. If null, reprocess all."
    )
    force: bool = Field(
        default=False,
        description="Force reprocess even if already completed"
    )


class ReprocessDocumentsResponse(BaseModel):
    """Response schema for reprocess request."""

    task_id: str = Field(..., description="Celery task ID for tracking")
    document_count: int = Field(..., description="Number of documents queued for reprocessing")
    message: str = Field(..., description="Status message")


class UpdateOllamaUrlRequest(BaseModel):
    """Request schema for updating Ollama base URL."""

    url: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Ollama server base URL (e.g., 'http://localhost:11434')",
    )
