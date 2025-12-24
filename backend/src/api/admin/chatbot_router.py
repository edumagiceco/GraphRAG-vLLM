"""
Admin chatbot management API router.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.model_manager import ModelManager
from src.api.deps import CurrentUser
from src.api.admin.schemas import (
    CreateChatbotRequest,
    UpdateChatbotRequest,
    ChatbotStatusUpdate,
    ChatbotResponse,
    ChatbotDetailResponse,
    ChatbotListResponse,
    PersonaConfig,
)
from src.services.chatbot_service import ChatbotServiceManager
from src.models.chatbot_service import ChatbotStatus, ChatbotService

router = APIRouter()


async def get_effective_llm_model(chatbot: ChatbotService) -> str:
    """Get the effective LLM model for a chatbot (chatbot-specific or system default)."""
    if chatbot.llm_model:
        return chatbot.llm_model
    return await ModelManager.get_default_llm_model()


@router.post("", response_model=ChatbotDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_chatbot(
    request: CreateChatbotRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChatbotDetailResponse:
    """
    Create a new chatbot service.

    Args:
        request: Chatbot creation request
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Created chatbot details

    Raises:
        HTTPException: If access_url already exists
    """
    try:
        chatbot = await ChatbotServiceManager.create(
            db=db,
            admin_id=current_user.id,
            name=request.name,
            access_url=request.access_url,
            persona=request.persona.model_dump(),
            description=request.description,
            llm_model=request.llm_model,
        )

        effective_model = await get_effective_llm_model(chatbot)

        return ChatbotDetailResponse(
            id=chatbot.id,
            name=chatbot.name,
            description=chatbot.description,
            status=chatbot.status,
            access_url=chatbot.access_url,
            document_count=0,
            llm_model=chatbot.llm_model,
            created_at=chatbot.created_at,
            updated_at=chatbot.updated_at,
            persona=PersonaConfig(**chatbot.persona),
            active_version=chatbot.active_version,
            effective_llm_model=effective_model,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get("", response_model=ChatbotListResponse)
async def list_chatbots(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: ChatbotStatus | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
) -> ChatbotListResponse:
    """
    List chatbots for the current admin user.

    Args:
        current_user: Authenticated admin user
        db: Database session
        page: Page number
        page_size: Items per page
        status_filter: Optional status filter

    Returns:
        Paginated chatbot list
    """
    chatbots, total = await ChatbotServiceManager.list_by_admin(
        db=db,
        admin_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status_filter,
    )

    items = []
    for chatbot in chatbots:
        doc_count = await ChatbotServiceManager.get_document_count(db, chatbot.id)
        items.append(
            ChatbotResponse(
                id=chatbot.id,
                name=chatbot.name,
                description=chatbot.description,
                status=chatbot.status,
                access_url=chatbot.access_url,
                document_count=doc_count,
                llm_model=chatbot.llm_model,
                created_at=chatbot.created_at,
                updated_at=chatbot.updated_at,
            )
        )

    return ChatbotListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{chatbot_id}", response_model=ChatbotDetailResponse)
async def get_chatbot(
    chatbot_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChatbotDetailResponse:
    """
    Get chatbot details by ID.

    Args:
        chatbot_id: Chatbot ID
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Chatbot details

    Raises:
        HTTPException: If chatbot not found
    """
    chatbot = await ChatbotServiceManager.get_by_id(
        db=db,
        chatbot_id=chatbot_id,
        admin_id=current_user.id,
    )

    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )

    doc_count = await ChatbotServiceManager.get_document_count(db, chatbot.id)
    effective_model = await get_effective_llm_model(chatbot)

    return ChatbotDetailResponse(
        id=chatbot.id,
        name=chatbot.name,
        description=chatbot.description,
        status=chatbot.status,
        access_url=chatbot.access_url,
        document_count=doc_count,
        llm_model=chatbot.llm_model,
        created_at=chatbot.created_at,
        updated_at=chatbot.updated_at,
        persona=PersonaConfig(**chatbot.persona),
        active_version=chatbot.active_version,
        effective_llm_model=effective_model,
    )


@router.patch("/{chatbot_id}", response_model=ChatbotDetailResponse)
async def update_chatbot(
    chatbot_id: str,
    request: UpdateChatbotRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChatbotDetailResponse:
    """
    Update chatbot details.

    Args:
        chatbot_id: Chatbot ID
        request: Update request
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Updated chatbot details

    Raises:
        HTTPException: If chatbot not found
    """
    chatbot = await ChatbotServiceManager.update(
        db=db,
        chatbot_id=chatbot_id,
        admin_id=current_user.id,
        name=request.name,
        description=request.description,
        persona=request.persona.model_dump() if request.persona else None,
        llm_model=request.llm_model,
    )

    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )

    doc_count = await ChatbotServiceManager.get_document_count(db, chatbot.id)
    effective_model = await get_effective_llm_model(chatbot)

    return ChatbotDetailResponse(
        id=chatbot.id,
        name=chatbot.name,
        description=chatbot.description,
        status=chatbot.status,
        access_url=chatbot.access_url,
        document_count=doc_count,
        llm_model=chatbot.llm_model,
        created_at=chatbot.created_at,
        updated_at=chatbot.updated_at,
        persona=PersonaConfig(**chatbot.persona),
        active_version=chatbot.active_version,
        effective_llm_model=effective_model,
    )


@router.patch("/{chatbot_id}/status", response_model=ChatbotDetailResponse)
async def update_chatbot_status(
    chatbot_id: str,
    request: ChatbotStatusUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChatbotDetailResponse:
    """
    Update chatbot status (activate/deactivate).

    Args:
        chatbot_id: Chatbot ID
        request: Status update request
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Updated chatbot details

    Raises:
        HTTPException: If chatbot not found
    """
    chatbot = await ChatbotServiceManager.update_status(
        db=db,
        chatbot_id=chatbot_id,
        admin_id=current_user.id,
        status=request.status,
    )

    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )

    doc_count = await ChatbotServiceManager.get_document_count(db, chatbot.id)
    effective_model = await get_effective_llm_model(chatbot)

    return ChatbotDetailResponse(
        id=chatbot.id,
        name=chatbot.name,
        description=chatbot.description,
        status=chatbot.status,
        access_url=chatbot.access_url,
        document_count=doc_count,
        llm_model=chatbot.llm_model,
        created_at=chatbot.created_at,
        updated_at=chatbot.updated_at,
        persona=PersonaConfig(**chatbot.persona),
        active_version=chatbot.active_version,
        effective_llm_model=effective_model,
    )


@router.delete("/{chatbot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chatbot(
    chatbot_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a chatbot service.

    Args:
        chatbot_id: Chatbot ID
        current_user: Authenticated admin user
        db: Database session

    Raises:
        HTTPException: If chatbot not found
    """
    deleted = await ChatbotServiceManager.delete(
        db=db,
        chatbot_id=chatbot_id,
        admin_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )
