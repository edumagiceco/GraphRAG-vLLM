"""
Celery tasks for document processing pipeline.
"""
import asyncio
from datetime import datetime

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.core.celery_app import OllamaRateLimitedTask
from src.models.document import Document, DocumentStatus as DocumentProcessingStatus

logger = get_task_logger(__name__)


def get_sync_redis():
    """Get sync Redis client for Celery tasks."""
    import redis
    return redis.from_url(settings.redis_url)


def set_progress(document_id: str, progress: int, stage: str, error: str = None):
    """Set document processing progress in Redis."""
    redis_client = get_sync_redis()
    key = f"doc_progress:{document_id}"
    data = {"progress": str(progress), "stage": stage}
    if error:
        data["error"] = error
    redis_client.hset(key, mapping=data)
    redis_client.expire(key, 86400)  # 24 hours
    # Publish progress update
    redis_client.publish(
        f"progress:{document_id}",
        f"{progress}:{stage}:{error or ''}"
    )


def get_db_session():
    """Create sync database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    # Convert async URL to sync
    sync_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    return Session(engine)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str, chatbot_id: str) -> dict:
    """
    Process a PDF document through the full GraphRAG pipeline.

    Stages:
    1. Parsing (10%) - Extract text from PDF
    2. Chunking (30%) - Split into semantic chunks
    3. Embedding (50%) - Generate vector embeddings
    4. Extracting (70%) - Extract entities from chunks
    5. Graphing (90%) - Build knowledge graph
    6. Completed (100%) - Finalize

    Args:
        document_id: UUID of the document to process
        chatbot_id: UUID of the chatbot service

    Returns:
        Processing result dict
    """
    db = get_db_session()

    try:
        # Get document from database
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Update status to parsing (first processing stage)
        document.status = DocumentProcessingStatus.PARSING
        db.commit()

        # Stage 1: Parsing (10%)
        logger.info(f"[{document_id}] Starting PDF parsing...")
        set_progress(document_id, 10, "parsing")

        from src.services.document.parser import extract_text_from_pdf
        text = extract_text_from_pdf(document.file_path)

        if not text or not text.strip():
            raise ValueError("No text content extracted from PDF")

        logger.info(f"[{document_id}] Extracted {len(text)} characters")

        # Stage 2: Chunking (30%)
        logger.info(f"[{document_id}] Chunking text...")
        set_progress(document_id, 30, "chunking")

        from src.services.document.chunker import chunk_document
        chunks = chunk_document(text, document_id, document.filename)

        logger.info(f"[{document_id}] Created {len(chunks)} chunks")

        if not chunks:
            raise ValueError("No chunks created from document")

        # Stage 3: Embedding (50%)
        logger.info(f"[{document_id}] Generating embeddings...")
        set_progress(document_id, 50, "embedding")

        from src.services.document.embedder import get_document_embedder
        embedder = get_document_embedder()
        point_ids = embedder.embed_and_store(chunks, chatbot_id)

        logger.info(f"[{document_id}] Stored {len(point_ids)} vectors in Qdrant")

        # Stage 4: Entity Extraction (70%)
        logger.info(f"[{document_id}] Extracting entities...")
        set_progress(document_id, 70, "extracting")

        from src.services.graph.entity_extractor import extract_entities
        # Extract entities from full text (LLM rate limited)
        entities = extract_entities(text[:10000], use_llm=True)  # Limit text for LLM

        logger.info(f"[{document_id}] Extracted {len(entities)} entities")

        # Stage 5: Relationship Extraction & Graph Building (90%)
        logger.info(f"[{document_id}] Building knowledge graph...")
        set_progress(document_id, 90, "graphing")

        if entities:
            from src.services.graph.relation_extractor import extract_relationships
            relationships = extract_relationships(text[:10000], entities, use_llm=True)

            logger.info(f"[{document_id}] Extracted {len(relationships)} relationships")

            # Build graph in Neo4j
            from src.services.graph.graph_builder import GraphBuilder
            builder = GraphBuilder()

            # Run async operations in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    builder.add_entities(entities, chatbot_id, document_id)
                )
                loop.run_until_complete(
                    builder.add_relationships(relationships, chatbot_id, document_id)
                )
            finally:
                loop.close()

        # Stage 6: Completed (100%)
        logger.info(f"[{document_id}] Document processing completed!")
        set_progress(document_id, 100, "completed")

        # Update document record
        document.status = DocumentProcessingStatus.COMPLETED
        document.chunk_count = len(chunks)
        document.entity_count = len(entities) if entities else 0
        document.processed_at = datetime.utcnow()
        db.commit()

        return {
            "document_id": document_id,
            "status": "completed",
            "chunk_count": len(chunks),
            "entity_count": len(entities) if entities else 0,
        }

    except Exception as exc:
        logger.error(f"[{document_id}] Document processing failed: {exc}")
        set_progress(document_id, -1, "failed", str(exc))

        # Update document status
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentProcessingStatus.FAILED
                document.error_message = str(exc)[:500]
                db.commit()
        except Exception:
            pass

        raise self.retry(exc=exc)

    finally:
        db.close()


@shared_task(base=OllamaRateLimitedTask, bind=True, max_retries=2)
def extract_entities_task(self, text: str, document_id: str) -> list:
    """
    Extract entities from text using LLM.
    Uses rate limiting to prevent overloading Ollama.

    Args:
        text: Text to extract entities from
        document_id: Document ID for context

    Returns:
        List of extracted entities
    """
    logger.info(f"[{document_id}] Extracting entities with LLM...")

    try:
        from src.services.graph.entity_extractor import extract_entities
        entities = extract_entities(text, use_llm=True)
        return entities
    except Exception as exc:
        logger.error(f"[{document_id}] Entity extraction failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True)
def cleanup_document_task(self, document_id: str, chatbot_id: str) -> dict:
    """
    Clean up vectors and graph nodes for a deleted document.

    Args:
        document_id: UUID of the document
        chatbot_id: UUID of the chatbot service

    Returns:
        Cleanup result dict
    """
    logger.info(f"Cleaning up document {document_id}...")

    deleted_vectors = 0
    deleted_nodes = 0

    try:
        # Delete vectors from Qdrant
        from src.services.document.embedder import get_document_embedder
        embedder = get_document_embedder()
        deleted_vectors = embedder.delete_by_document(document_id)
        logger.info(f"Deleted {deleted_vectors} vectors from Qdrant")

        # Delete nodes from Neo4j
        from src.services.graph.graph_builder import GraphBuilder
        builder = GraphBuilder()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            deleted_nodes = loop.run_until_complete(
                builder.delete_by_document(document_id)
            )
        finally:
            loop.close()

        logger.info(f"Deleted {deleted_nodes} nodes from Neo4j")

    except Exception as exc:
        logger.error(f"Cleanup failed for document {document_id}: {exc}")
        # Don't raise - cleanup failures shouldn't block

    return {
        "document_id": document_id,
        "status": "cleaned",
        "deleted_vectors": deleted_vectors,
        "deleted_nodes": deleted_nodes,
    }


@shared_task(bind=True)
def cleanup_chatbot_task(self, chatbot_id: str) -> dict:
    """
    Clean up all vectors and graph nodes for a deleted chatbot.

    Args:
        chatbot_id: UUID of the chatbot

    Returns:
        Cleanup result dict
    """
    logger.info(f"Cleaning up chatbot {chatbot_id}...")

    deleted_vectors = 0
    deleted_nodes = 0

    try:
        # Delete vectors from Qdrant
        from src.services.document.embedder import get_document_embedder
        embedder = get_document_embedder()
        deleted_vectors = embedder.delete_by_chatbot(chatbot_id)
        logger.info(f"Deleted {deleted_vectors} vectors from Qdrant")

        # Delete nodes from Neo4j
        from src.services.graph.graph_builder import GraphBuilder
        builder = GraphBuilder()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            deleted_nodes = loop.run_until_complete(
                builder.delete_by_chatbot(chatbot_id)
            )
        finally:
            loop.close()

        logger.info(f"Deleted {deleted_nodes} nodes from Neo4j")

    except Exception as exc:
        logger.error(f"Cleanup failed for chatbot {chatbot_id}: {exc}")

    return {
        "chatbot_id": chatbot_id,
        "status": "cleaned",
        "deleted_vectors": deleted_vectors,
        "deleted_nodes": deleted_nodes,
    }
