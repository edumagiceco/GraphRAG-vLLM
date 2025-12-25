"""
Settings API schemas for model configuration.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """Information about a model."""

    name: str = Field(..., description="Model name")
    size: int = Field(default=0, description="Model size in bytes")
    size_formatted: str = Field(default="-", description="Human-readable size")
    modified_at: str = Field(default="-", description="Last modified timestamp")
    family: Optional[str] = Field(None, description="Model family")
    parameter_size: Optional[str] = Field(None, description="Parameter size")
    quantization_level: Optional[str] = Field(None, description="Quantization level")


class SystemSettingsResponse(BaseModel):
    """Response schema for system settings."""

    llm_backend: str = Field(..., description="LLM backend type ('vllm' or 'ollama')")
    default_llm_model: str = Field(..., description="Default LLM model for chat")
    embedding_model: str = Field(..., description="Embedding model for vector generation")
    embedding_dimension: int = Field(..., description="Embedding vector dimension")
    vllm_base_url: str = Field(..., description="vLLM server base URL")
    vllm_embedding_url: str = Field(..., description="vLLM embedding server URL")
    timezone: str = Field(..., description="System timezone (e.g., 'GMT+9', 'GMT-5')")


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
    llm_connected: bool = Field(default=False, description="LLM server connection status")
    embedding_connected: bool = Field(default=False, description="Embedding server connection status")
    llm_model: Optional[str] = Field(None, description="Connected LLM model name")
    embedding_model: Optional[str] = Field(None, description="Connected embedding model name")
    vllm_base_url: str = Field(..., description="vLLM server URL")
    vllm_embedding_url: str = Field(..., description="vLLM embedding server URL")
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


class UpdateTimezoneRequest(BaseModel):
    """Request schema for updating system timezone."""

    timezone: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Timezone in GMT offset format (e.g., 'GMT+0', 'GMT+9', 'GMT-5')",
    )
