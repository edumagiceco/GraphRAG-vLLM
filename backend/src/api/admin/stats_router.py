"""
Admin statistics API router.
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps import CurrentUser
from src.services.chatbot_service import ChatbotServiceManager
from src.services.stats_service import StatsService


router = APIRouter()


# Pydantic schemas for stats responses
class DailyStats(BaseModel):
    """Daily statistics."""

    date: str
    sessions: int
    messages: int
    avg_response_time_ms: Optional[int] = None


class StatsSummary(BaseModel):
    """Statistics summary response."""

    period_days: int
    start_date: str
    end_date: str
    total_sessions: int
    total_messages: int
    avg_response_time_ms: Optional[float] = None
    daily_stats: list[DailyStats]


class StatsResponse(BaseModel):
    """Full stats response."""

    chatbot_id: str
    chatbot_name: str
    stats: StatsSummary


@router.get("/{chatbot_id}/stats", response_model=StatsResponse)
async def get_chatbot_stats(
    chatbot_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to include"),
) -> StatsResponse:
    """
    Get statistics for a chatbot.

    Args:
        chatbot_id: Chatbot ID
        current_user: Authenticated admin user
        db: Database session
        days: Number of days to include in stats

    Returns:
        Statistics summary

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

    # Get summary stats
    summary = await StatsService.get_summary_stats(db, chatbot_id, days)

    return StatsResponse(
        chatbot_id=chatbot_id,
        chatbot_name=chatbot.name,
        stats=StatsSummary(
            period_days=summary["period_days"],
            start_date=summary["start_date"],
            end_date=summary["end_date"],
            total_sessions=summary["total_sessions"],
            total_messages=summary["total_messages"],
            avg_response_time_ms=summary["avg_response_time_ms"],
            daily_stats=[
                DailyStats(
                    date=d["date"],
                    sessions=d["sessions"],
                    messages=d["messages"],
                    avg_response_time_ms=d["avg_response_time_ms"],
                )
                for d in summary["daily_stats"]
            ],
        ),
    )


@router.post("/{chatbot_id}/stats/recalculate", status_code=status.HTTP_202_ACCEPTED)
async def recalculate_stats(
    chatbot_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to recalculate"),
) -> dict:
    """
    Trigger recalculation of statistics for a chatbot.

    Args:
        chatbot_id: Chatbot ID
        current_user: Authenticated admin user
        db: Database session
        days: Number of days to recalculate

    Returns:
        Confirmation message

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

    # Recalculate stats
    results = await StatsService.recalculate_all_stats(db, chatbot_id, days)

    return {
        "message": f"Recalculated stats for {len(results)} days",
        "chatbot_id": chatbot_id,
        "days_processed": len(results),
    }
