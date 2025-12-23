"""
Admin version management API router.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps import CurrentUser
from src.services.chatbot_service import ChatbotServiceManager
from src.services.version_service import VersionService
from src.models.index_version import VersionStatus


router = APIRouter()


# Pydantic schemas
class VersionResponse(BaseModel):
    """Version response schema."""

    id: str
    chatbot_id: str
    version: int
    status: str
    created_at: datetime
    activated_at: Optional[datetime] = None


class VersionListResponse(BaseModel):
    """Version list response schema."""

    items: list[VersionResponse]
    total: int
    active_version: Optional[int] = None


class ActivateVersionResponse(BaseModel):
    """Activate version response schema."""

    message: str
    version: VersionResponse


@router.get("/{chatbot_id}/versions", response_model=VersionListResponse)
async def list_versions(
    chatbot_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> VersionListResponse:
    """
    List all versions for a chatbot.

    Args:
        chatbot_id: Chatbot ID
        current_user: Authenticated admin user
        db: Database session

    Returns:
        List of versions

    Raises:
        HTTPException: If chatbot not found
    """
    # Verify chatbot exists and belongs to user
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

    versions = await VersionService.get_versions(db, chatbot_id)

    return VersionListResponse(
        items=[
            VersionResponse(
                id=v.id,
                chatbot_id=v.chatbot_id,
                version=v.version,
                status=v.status.value,
                created_at=v.created_at,
                activated_at=v.activated_at,
            )
            for v in versions
        ],
        total=len(versions),
        active_version=chatbot.active_version,
    )


@router.get("/{chatbot_id}/versions/{version}", response_model=VersionResponse)
async def get_version(
    chatbot_id: str,
    version: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> VersionResponse:
    """
    Get a specific version.

    Args:
        chatbot_id: Chatbot ID
        version: Version number
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Version details

    Raises:
        HTTPException: If chatbot or version not found
    """
    # Verify chatbot exists and belongs to user
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

    version_obj = await VersionService.get_version(db, chatbot_id, version)

    if not version_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    return VersionResponse(
        id=version_obj.id,
        chatbot_id=version_obj.chatbot_id,
        version=version_obj.version,
        status=version_obj.status.value,
        created_at=version_obj.created_at,
        activated_at=version_obj.activated_at,
    )


@router.post(
    "/{chatbot_id}/versions/{version}/activate",
    response_model=ActivateVersionResponse,
)
async def activate_version(
    chatbot_id: str,
    version: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ActivateVersionResponse:
    """
    Activate a specific version.

    Args:
        chatbot_id: Chatbot ID
        version: Version number to activate
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Confirmation with activated version

    Raises:
        HTTPException: If chatbot or version not found, or version cannot be activated
    """
    # Verify chatbot exists and belongs to user
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

    # Check version exists
    version_obj = await VersionService.get_version(db, chatbot_id, version)

    if not version_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    # Check if version can be activated
    if version_obj.status not in (VersionStatus.READY, VersionStatus.ACTIVE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot activate version with status '{version_obj.status.value}'. "
            f"Version must be 'ready' or already 'active'.",
        )

    # Activate the version
    activated = await VersionService.activate_version(db, chatbot_id, version)

    if not activated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate version",
        )

    return ActivateVersionResponse(
        message=f"Version {version} activated successfully",
        version=VersionResponse(
            id=activated.id,
            chatbot_id=activated.chatbot_id,
            version=activated.version,
            status=activated.status.value,
            created_at=activated.created_at,
            activated_at=activated.activated_at,
        ),
    )


@router.delete("/{chatbot_id}/versions/{version}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    chatbot_id: str,
    version: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a version (cannot delete active version).

    Args:
        chatbot_id: Chatbot ID
        version: Version number to delete
        current_user: Authenticated admin user
        db: Database session

    Raises:
        HTTPException: If chatbot or version not found, or version is active
    """
    # Verify chatbot exists and belongs to user
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

    # Check version exists
    version_obj = await VersionService.get_version(db, chatbot_id, version)

    if not version_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    # Check if version is active
    if version_obj.status == VersionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active version. Activate a different version first.",
        )

    # Delete the version
    deleted = await VersionService.delete_version(db, chatbot_id, version)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete version",
        )
