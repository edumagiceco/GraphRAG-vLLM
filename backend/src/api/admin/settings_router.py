"""
Settings API router for model configuration.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.core.database import get_db
from src.core.model_manager import ModelManager
from src.models.admin_user import AdminUser
from src.api.admin.settings_schemas import (
    SystemSettingsResponse,
    AvailableModelsResponse,
    ModelInfo,
    UpdateDefaultLLMRequest,
    UpdateEmbeddingModelRequest,
    UpdateOllamaUrlRequest,
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
    default_llm = await ModelManager.get_default_llm_model()
    embedding_model = await ModelManager.get_embedding_model()
    embedding_dimension = await ModelManager.get_embedding_dimension()
    ollama_url = await ModelManager.get_ollama_base_url()
    timezone = await ModelManager.get_timezone()

    return SystemSettingsResponse(
        default_llm_model=default_llm,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
        ollama_base_url=ollama_url,
        timezone=timezone,
    )


@router.get(
    "/models/available",
    response_model=AvailableModelsResponse,
    summary="List available models from Ollama",
)
async def list_available_models(
    current_admin: AdminUser = Depends(get_current_user),
) -> AvailableModelsResponse:
    """List all available models from the Ollama server."""
    models = await ModelManager.list_available_models()

    # Convert to response format
    model_infos = [
        ModelInfo(
            name=m.name,
            size=m.size,
            size_formatted=m.size_formatted,
            modified_at=m.modified_at,
            family=m.family,
            parameter_size=m.parameter_size,
            quantization_level=m.quantization_level,
        )
        for m in models
    ]

    # Classify into chat and embedding models
    chat_models, embedding_models = ModelManager.classify_models(models)

    chat_model_infos = [
        ModelInfo(
            name=m.name,
            size=m.size,
            size_formatted=m.size_formatted,
            modified_at=m.modified_at,
            family=m.family,
            parameter_size=m.parameter_size,
            quantization_level=m.quantization_level,
        )
        for m in chat_models
    ]

    embedding_model_infos = [
        ModelInfo(
            name=m.name,
            size=m.size,
            size_formatted=m.size_formatted,
            modified_at=m.modified_at,
            family=m.family,
            parameter_size=m.parameter_size,
            quantization_level=m.quantization_level,
        )
        for m in embedding_models
    ]

    return AvailableModelsResponse(
        models=model_infos,
        chat_models=chat_model_infos,
        embedding_models=embedding_model_infos,
        total=len(models),
    )


@router.put(
    "/models/default-llm",
    response_model=SystemSettingsResponse,
    summary="Update default LLM model",
)
async def update_default_llm_model(
    request: UpdateDefaultLLMRequest,
    current_admin: AdminUser = Depends(get_current_user),
) -> SystemSettingsResponse:
    """Update the default LLM model for chat completion."""
    # Verify model exists
    models = await ModelManager.list_available_models()
    model_names = [m.name for m in models]

    if request.model not in model_names:
        # Check if it's a partial match (without tag)
        base_name = request.model.split(":")[0]
        matching = [m for m in model_names if m.startswith(base_name)]
        if not matching:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{request.model}' not found in Ollama. "
                       f"Available models: {', '.join(model_names[:5])}...",
            )

    await ModelManager.set_default_llm_model(request.model)

    # Reset LLM instance to use new model
    ModelManager.reset_llm_instance()

    logger.info(f"Default LLM model updated to {request.model} by {current_admin.email}")

    return await get_model_settings(current_admin)


@router.put(
    "/models/embedding",
    response_model=SystemSettingsResponse,
    summary="Update embedding model",
)
async def update_embedding_model(
    request: UpdateEmbeddingModelRequest,
    current_admin: AdminUser = Depends(get_current_user),
) -> SystemSettingsResponse:
    """
    Update the embedding model.

    WARNING: Changing the embedding model will make existing vectors incompatible.
    You should reprocess all documents after changing this setting.
    """
    # Verify model exists
    models = await ModelManager.list_available_models()
    model_names = [m.name for m in models]

    if request.model not in model_names:
        base_name = request.model.split(":")[0]
        matching = [m for m in model_names if m.startswith(base_name)]
        if not matching:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{request.model}' not found in Ollama.",
            )

    await ModelManager.set_embedding_model(request.model)

    # Reset embedding instance to use new model
    ModelManager.reset_embedding_instance()

    logger.warning(
        f"Embedding model updated to {request.model} by {current_admin.email}. "
        "Existing vectors may be incompatible!"
    )

    return await get_model_settings(current_admin)


@router.get(
    "/models/test-connection",
    response_model=ConnectionTestResponse,
    summary="Test Ollama connection",
)
async def test_ollama_connection(
    current_admin: AdminUser = Depends(get_current_user),
) -> ConnectionTestResponse:
    """Test connection to the Ollama server."""
    ollama_url = await ModelManager.get_ollama_base_url()
    connected, version, error = await ModelManager.test_connection()

    return ConnectionTestResponse(
        connected=connected,
        ollama_version=version,
        ollama_base_url=ollama_url,
        error=error,
    )


@router.put(
    "/models/ollama-url",
    response_model=SystemSettingsResponse,
    summary="Update Ollama base URL",
)
async def update_ollama_url(
    request: UpdateOllamaUrlRequest,
    current_admin: AdminUser = Depends(get_current_user),
) -> SystemSettingsResponse:
    """Update the Ollama server base URL."""
    await ModelManager.set_ollama_base_url(request.url)

    logger.info(f"Ollama URL updated to {request.url} by {current_admin.email}")

    return await get_model_settings(current_admin)


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
