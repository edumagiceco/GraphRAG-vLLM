"""
Document API schemas.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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


class ProcessingStage(str, Enum):
    """Document processing stages."""

    UPLOADING = "uploading"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    EXTRACTING = "extracting"
    GRAPHING = "graphing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentResponse(BaseModel):
    """Response schema for document."""

    id: str = Field(..., description="Document ID")
    chatbot_id: str = Field(..., description="Parent chatbot ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    status: DocumentStatus = Field(..., description="Processing status")
    chunk_count: int = Field(default=0, description="Number of chunks")
    entity_count: int = Field(default=0, description="Number of extracted entities")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Upload timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")

    model_config = {"from_attributes": True}


class DocumentProgress(BaseModel):
    """Document processing progress."""

    document_id: str = Field(..., description="Document ID")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    stage: ProcessingStage = Field(..., description="Current processing stage")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")


class DocumentListResponse(BaseModel):
    """Response schema for document list."""

    items: list[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total count")


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload."""

    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    status: DocumentStatus = Field(..., description="Initial status")
    message: str = Field(..., description="Upload status message")


class EntityInfo(BaseModel):
    """Entity information from knowledge graph."""

    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type (Concept, Definition, Process)")
    description: Optional[str] = Field(None, description="Entity description")


class RelationshipInfo(BaseModel):
    """Relationship information from knowledge graph."""

    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    type: str = Field(..., description="Relationship type")


class ChunkInfo(BaseModel):
    """Chunk information from vector store."""

    id: str = Field(..., description="Chunk ID")
    text: str = Field(..., description="Chunk text content")
    page: Optional[int] = Field(None, description="Source page number")
    position: int = Field(..., description="Position in document")


class DocumentGraphDetails(BaseModel):
    """GraphRAG details for a document."""

    document_id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    entities: list[EntityInfo] = Field(default_factory=list, description="Extracted entities")
    relationships: list[RelationshipInfo] = Field(default_factory=list, description="Extracted relationships")
    chunks: list[ChunkInfo] = Field(default_factory=list, description="Document chunks")
    entity_count: int = Field(default=0, description="Total entity count")
    relationship_count: int = Field(default=0, description="Total relationship count")
    chunk_count: int = Field(default=0, description="Total chunk count")
