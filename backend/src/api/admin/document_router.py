"""
Document management API router.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.redis import RedisClient
from src.api.deps import CurrentUser
from src.api.admin.document_schemas import (
    DocumentResponse,
    DocumentProgress,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentGraphDetails,
    EntityInfo,
    RelationshipInfo,
    ChunkInfo,
    DocumentStatus,
    ProcessingStage,
)
from src.models.document import Document, DocumentStatus as DocumentProcessingStatus
from src.models.chatbot_service import ChatbotService
from src.services.document.storage import get_document_storage
from src.services.document.document_remover import remove_document_data
from src.workers.document_tasks import process_document

router = APIRouter()

# Maximum file size: 100MB
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


async def validate_pdf_file(file: UploadFile) -> None:
    """Validate uploaded PDF file."""
    # Check content type
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        # Also check by extension
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed",
            )

    # Check file size
    # Read file to get size (FastAPI doesn't provide size directly)
    contents = await file.read()
    file_size = len(contents)

    # Reset file pointer for later use
    await file.seek(0)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    # Check PDF magic bytes
    if not contents.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file format",
        )


async def get_chatbot_or_404(
    db: AsyncSession,
    chatbot_id: str,
    admin_id: str,
) -> ChatbotService:
    """Helper to get chatbot with ownership check."""
    result = await db.execute(
        select(ChatbotService).where(
            ChatbotService.id == chatbot_id,
            ChatbotService.admin_id == admin_id,
        )
    )
    chatbot = result.scalar_one_or_none()
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )
    return chatbot


@router.post(
    "/{chatbot_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    chatbot_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(..., description="PDF file to upload"),
) -> DocumentUploadResponse:
    """
    Upload a PDF document for processing.

    Args:
        chatbot_id: Chatbot ID
        current_user: Authenticated admin user
        db: Database session
        file: PDF file to upload

    Returns:
        Upload response with document ID

    Raises:
        HTTPException: If chatbot not found or file invalid
    """
    # Verify chatbot ownership
    await get_chatbot_or_404(db, chatbot_id, current_user.id)

    # Validate PDF file
    await validate_pdf_file(file)

    # Generate document ID
    document_id = str(uuid.uuid4())

    # Save file to storage
    storage = get_document_storage()
    try:
        file_path, file_size = await storage.save_file(
            chatbot_id=chatbot_id,
            document_id=document_id,
            file=file,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Create document record
    document = Document(
        id=document_id,
        chatbot_id=chatbot_id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        status=DocumentProcessingStatus.PENDING,
    )
    db.add(document)
    await db.commit()

    # Initialize progress in Redis
    await RedisClient.set_document_progress(
        document_id=document_id,
        progress=0,
        stage="uploading",
    )

    # Trigger Celery task for processing
    process_document.delay(document_id, chatbot_id)

    return DocumentUploadResponse(
        id=document_id,
        filename=file.filename or "unknown.pdf",
        status=DocumentStatus.PENDING,
        message="Document uploaded successfully. Processing started.",
    )


@router.get("/{chatbot_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    chatbot_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[DocumentStatus] = Query(
        default=None, alias="status", description="Filter by status"
    ),
) -> DocumentListResponse:
    """
    List documents for a chatbot.

    Args:
        chatbot_id: Chatbot ID
        current_user: Authenticated admin user
        db: Database session
        status_filter: Optional status filter

    Returns:
        Document list
    """
    # Verify chatbot ownership
    await get_chatbot_or_404(db, chatbot_id, current_user.id)

    # Build query
    query = select(Document).where(Document.chatbot_id == chatbot_id)

    if status_filter:
        # Map API status to model status
        status_map = {
            DocumentStatus.PENDING: DocumentProcessingStatus.PENDING,
            DocumentStatus.PROCESSING: DocumentProcessingStatus.PROCESSING,
            DocumentStatus.COMPLETED: DocumentProcessingStatus.COMPLETED,
            DocumentStatus.FAILED: DocumentProcessingStatus.FAILED,
        }
        if status_filter in status_map:
            query = query.where(Document.status == status_map[status_filter])

    query = query.order_by(Document.created_at.desc())

    result = await db.execute(query)
    documents = list(result.scalars().all())

    items = [
        DocumentResponse(
            id=doc.id,
            chatbot_id=doc.chatbot_id,
            filename=doc.filename,
            file_size=doc.file_size,
            status=DocumentStatus(doc.status.value),
            chunk_count=doc.chunk_count or 0,
            entity_count=doc.entity_count or 0,
            error_message=doc.error_message,
            created_at=doc.created_at,
            processed_at=doc.processed_at,
        )
        for doc in documents
    ]

    return DocumentListResponse(items=items, total=len(items))


@router.get(
    "/{chatbot_id}/documents/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    chatbot_id: str,
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Get document details.

    Args:
        chatbot_id: Chatbot ID
        document_id: Document ID
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Document details

    Raises:
        HTTPException: If document not found
    """
    # Verify chatbot ownership
    await get_chatbot_or_404(db, chatbot_id, current_user.id)

    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.chatbot_id == chatbot_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentResponse(
        id=document.id,
        chatbot_id=document.chatbot_id,
        filename=document.filename,
        file_size=document.file_size,
        status=DocumentStatus(document.status.value),
        chunk_count=document.chunk_count or 0,
        entity_count=document.entity_count or 0,
        error_message=document.error_message,
        created_at=document.created_at,
        processed_at=document.processed_at,
    )


@router.get(
    "/{chatbot_id}/documents/{document_id}/progress",
    response_model=DocumentProgress,
)
async def get_document_progress(
    chatbot_id: str,
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DocumentProgress:
    """
    Get document processing progress from Redis.

    Args:
        chatbot_id: Chatbot ID
        document_id: Document ID
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Document processing progress

    Raises:
        HTTPException: If document not found
    """
    # Verify chatbot ownership
    await get_chatbot_or_404(db, chatbot_id, current_user.id)

    # Verify document exists
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.chatbot_id == chatbot_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Get progress from Redis
    progress_data = await RedisClient.get_document_progress(document_id)

    if progress_data:
        stage_str = progress_data.get("stage", "pending")
        try:
            stage = ProcessingStage(stage_str)
        except ValueError:
            stage = ProcessingStage.PROCESSING

        # Clamp progress to valid range (0-100)
        raw_progress = int(progress_data.get("progress", 0))
        clamped_progress = max(0, min(100, raw_progress))

        return DocumentProgress(
            document_id=document_id,
            progress=clamped_progress,
            stage=stage,
            message=progress_data.get("message"),
            error=progress_data.get("error"),
        )

    # Fallback to database status
    stage_map = {
        DocumentProcessingStatus.PENDING: ProcessingStage.UPLOADING,
        DocumentProcessingStatus.PROCESSING: ProcessingStage.PROCESSING,
        DocumentProcessingStatus.COMPLETED: ProcessingStage.COMPLETED,
        DocumentProcessingStatus.FAILED: ProcessingStage.FAILED,
    }

    return DocumentProgress(
        document_id=document_id,
        progress=100 if document.status == DocumentProcessingStatus.COMPLETED else 0,
        stage=stage_map.get(document.status, ProcessingStage.UPLOADING),
        error=document.error_message,
    )


@router.delete(
    "/{chatbot_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    chatbot_id: str,
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a document.

    Args:
        chatbot_id: Chatbot ID
        document_id: Document ID
        current_user: Authenticated admin user
        db: Database session

    Raises:
        HTTPException: If document not found
    """
    # Verify chatbot ownership
    await get_chatbot_or_404(db, chatbot_id, current_user.id)

    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.chatbot_id == chatbot_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete file from storage
    storage = get_document_storage()
    await storage.delete_file(chatbot_id, document_id)

    # Remove vectors and graph data
    await remove_document_data(document_id, chatbot_id)

    # Delete from database
    await db.delete(document)
    await db.commit()

    # Clean up Redis progress
    await RedisClient.delete_document_progress(document_id)


@router.get(
    "/{chatbot_id}/documents/{document_id}/graph-details",
    response_model=DocumentGraphDetails,
)
async def get_document_graph_details(
    chatbot_id: str,
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DocumentGraphDetails:
    """
    Get GraphRAG details for a document (entities, relationships, chunks).

    Args:
        chatbot_id: Chatbot ID
        document_id: Document ID
        current_user: Authenticated admin user
        db: Database session

    Returns:
        GraphRAG details including entities, relationships, and chunks

    Raises:
        HTTPException: If document not found
    """
    from src.core.neo4j import Neo4jClient

    # Verify chatbot ownership
    await get_chatbot_or_404(db, chatbot_id, current_user.id)

    # Get document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.chatbot_id == chatbot_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    entities: list[EntityInfo] = []
    relationships: list[RelationshipInfo] = []
    chunks: list[ChunkInfo] = []

    # Get entities from Neo4j
    try:
        entity_query = """
        MATCH (e {document_id: $document_id, chatbot_id: $chatbot_id})
        RETURN e.name as name, labels(e)[0] as type, e.description as description
        ORDER BY e.name
        LIMIT 100
        """
        entity_results = await Neo4jClient.execute_query(
            entity_query,
            {"document_id": document_id, "chatbot_id": chatbot_id},
        )
        entities = [
            EntityInfo(
                name=r["name"],
                type=r["type"] or "Concept",
                description=r.get("description"),
            )
            for r in entity_results
            if r.get("name")
        ]
    except Exception as e:
        print(f"Error fetching entities: {e}")

    # Get relationships from Neo4j
    try:
        rel_query = """
        MATCH (s {document_id: $document_id, chatbot_id: $chatbot_id})-[r]->(t {chatbot_id: $chatbot_id})
        RETURN s.name as source, t.name as target, type(r) as rel_type
        ORDER BY s.name, t.name
        LIMIT 100
        """
        rel_results = await Neo4jClient.execute_query(
            rel_query,
            {"document_id": document_id, "chatbot_id": chatbot_id},
        )
        relationships = [
            RelationshipInfo(
                source=r["source"],
                target=r["target"],
                type=r["rel_type"],
            )
            for r in rel_results
            if r.get("source") and r.get("target")
        ]
    except Exception as e:
        print(f"Error fetching relationships: {e}")

    # Get chunks from Qdrant
    try:
        from src.core.qdrant import QdrantManager
        from qdrant_client.http import models as qdrant_models

        client = QdrantManager.get_client()
        collection_name = "document_chunks"

        # Check if collection exists
        collections = client.get_collections().collections
        collection_exists = any(c.name == collection_name for c in collections)

        if collection_exists:
            # Scroll with filter for document_id and chatbot_id
            scroll_result = client.scroll(
                collection_name=collection_name,
                scroll_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="document_id",
                            match=qdrant_models.MatchValue(value=document_id),
                        ),
                        qdrant_models.FieldCondition(
                            key="chatbot_id",
                            match=qdrant_models.MatchValue(value=chatbot_id),
                        ),
                    ]
                ),
                limit=100,
                with_payload=True,
                with_vectors=False,
            )

            points = scroll_result[0] if scroll_result else []

            chunks = [
                ChunkInfo(
                    id=str(point.id),
                    text=point.payload.get("text", "")[:500],  # Truncate for display
                    page=point.payload.get("page_number"),
                    position=point.payload.get("chunk_index", idx),
                )
                for idx, point in enumerate(points)
            ]
            # Sort by position
            chunks.sort(key=lambda x: x.position)
    except Exception as e:
        print(f"Error fetching chunks: {e}")

    return DocumentGraphDetails(
        document_id=document_id,
        filename=document.filename,
        entities=entities,
        relationships=relationships,
        chunks=chunks,
        entity_count=document.entity_count or len(entities),
        relationship_count=len(relationships),
        chunk_count=document.chunk_count or len(chunks),
    )
