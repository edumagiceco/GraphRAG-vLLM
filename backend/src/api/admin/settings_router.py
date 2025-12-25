"""
Settings API router for model configuration.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.core.database import get_db
from src.core.config import settings
from src.core.model_manager import ModelManager
from src.models.admin_user import AdminUser
from src.api.admin.settings_schemas import (
    SystemSettingsResponse,
    AvailableModelsResponse,
    ModelInfo,
    UpdateDefaultLLMRequest,
    UpdateEmbeddingModelRequest,
    UpdateTimezoneRequest,
    ConnectionTestResponse,
    ReprocessDocumentsRequest,
    ReprocessDocumentsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/models",
    response_model=SystemSettingsResponse,
    summary="Get current model settings",
)
async def get_model_settings(
    current_admin: AdminUser = Depends(get_current_user),
) -> SystemSettingsResponse:
    """Get the current system model settings."""
    embedding_dimension = await ModelManager.get_embedding_dimension()
    timezone = await ModelManager.get_timezone()

    return SystemSettingsResponse(
        llm_backend=settings.llm_backend,
        default_llm_model=settings.vllm_model,
        embedding_model=settings.vllm_embedding_model,
        embedding_dimension=embedding_dimension,
        vllm_base_url=settings.vllm_base_url,
        vllm_embedding_url=settings.vllm_embedding_base_url,
        timezone=timezone,
    )


@router.get(
    "/models/available",
    response_model=AvailableModelsResponse,
    summary="List available models from vLLM servers",
)
async def list_available_models(
    current_admin: AdminUser = Depends(get_current_user),
) -> AvailableModelsResponse:
    """List all available models from the vLLM servers."""
    import httpx

    models = []
    chat_models = []
    embedding_models = []

    # Get LLM models from vLLM server
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.vllm_base_url}/models",
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                for m in data.get("data", []):
                    model_info = ModelInfo(
                        name=m.get("id", "unknown"),
                        size=0,
                        size_formatted="-",
                        modified_at="-",
                        family=None,
                        parameter_size=None,
                        quantization_level=None,
                    )
                    models.append(model_info)
                    chat_models.append(model_info)
    except Exception as e:
        logger.warning(f"Failed to get LLM models from vLLM: {e}")

    # Get embedding models from vLLM embedding server
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.vllm_embedding_base_url}/models",
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                for m in data.get("data", []):
                    model_info = ModelInfo(
                        name=m.get("id", "unknown"),
                        size=0,
                        size_formatted="-",
                        modified_at="-",
                        family=None,
                        parameter_size=None,
                        quantization_level=None,
                    )
                    models.append(model_info)
                    embedding_models.append(model_info)
    except Exception as e:
        logger.warning(f"Failed to get embedding models from vLLM: {e}")

    return AvailableModelsResponse(
        models=models,
        chat_models=chat_models,
        embedding_models=embedding_models,
        total=len(models),
    )


@router.get(
    "/models/test-connection",
    response_model=ConnectionTestResponse,
    summary="Test vLLM connection",
)
async def test_vllm_connection(
    current_admin: AdminUser = Depends(get_current_user),
) -> ConnectionTestResponse:
    """Test connection to the vLLM servers."""
    import httpx

    llm_connected = False
    embedding_connected = False
    llm_model = None
    embedding_model = None
    errors = []

    # Test LLM server
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.vllm_base_url}/models",
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                if models:
                    llm_connected = True
                    llm_model = models[0].get("id", "unknown")
    except Exception as e:
        errors.append(f"LLM server: {str(e)}")

    # Test embedding server
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.vllm_embedding_base_url}/models",
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                if models:
                    embedding_connected = True
                    embedding_model = models[0].get("id", "unknown")
    except Exception as e:
        errors.append(f"Embedding server: {str(e)}")

    return ConnectionTestResponse(
        connected=llm_connected and embedding_connected,
        llm_connected=llm_connected,
        embedding_connected=embedding_connected,
        llm_model=llm_model,
        embedding_model=embedding_model,
        vllm_base_url=settings.vllm_base_url,
        vllm_embedding_url=settings.vllm_embedding_base_url,
        error="; ".join(errors) if errors else None,
    )


@router.put(
    "/timezone",
    response_model=SystemSettingsResponse,
    summary="Update system timezone",
)
async def update_timezone(
    request: UpdateTimezoneRequest,
    current_admin: AdminUser = Depends(get_current_user),
) -> SystemSettingsResponse:
    """Update the system timezone setting."""
    # Validate timezone format (GMT+N or GMT-N)
    import re
    if not re.match(r'^GMT[+-]\d{1,2}(:\d{2})?$', request.timezone):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timezone format: {request.timezone}. Use format like 'GMT+0', 'GMT+9', 'GMT-5'",
        )

    await ModelManager.set_timezone(request.timezone)

    logger.info(f"Timezone updated to {request.timezone} by {current_admin.email}")

    return await get_model_settings(current_admin)


@router.post(
    "/documents/reprocess",
    response_model=ReprocessDocumentsResponse,
    summary="Reprocess all documents",
)
async def reprocess_documents(
    request: ReprocessDocumentsRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_user),
) -> ReprocessDocumentsResponse:
    """
    Queue all documents for reprocessing.
    Useful after changing the embedding model.
    """
    from sqlalchemy import select, update
    from src.models.document import Document, DocumentStatus

    # Build query
    query = select(Document)
    if request.chatbot_id:
        query = query.where(Document.chatbot_id == request.chatbot_id)

    if not request.force:
        # Only reprocess completed documents
        query = query.where(Document.status == DocumentStatus.COMPLETED)

    result = await db.execute(query)
    documents = result.scalars().all()

    if not documents:
        return ReprocessDocumentsResponse(
            task_id="",
            document_count=0,
            message="No documents to reprocess",
        )

    # Update status to pending
    doc_ids = [doc.id for doc in documents]
    await db.execute(
        update(Document)
        .where(Document.id.in_(doc_ids))
        .values(status=DocumentStatus.PENDING)
    )
    await db.commit()

    # Queue processing tasks
    from src.workers.document_tasks import process_document

    task_ids = []
    for doc in documents:
        task = process_document.delay(doc.id, doc.chatbot_id)
        task_ids.append(task.id)

    logger.info(
        f"Queued {len(documents)} documents for reprocessing by {current_admin.email}"
    )

    return ReprocessDocumentsResponse(
        task_id=task_ids[0] if task_ids else "",
        document_count=len(documents),
        message=f"Queued {len(documents)} documents for reprocessing",
    )
