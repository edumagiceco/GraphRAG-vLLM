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
    input_tokens: int = 0
    output_tokens: int = 0
    retrieval_count: int = 0


class StatsSummary(BaseModel):
    """Statistics summary response."""

    period_days: int
    start_date: str
    end_date: str
    total_sessions: int
    total_messages: int
    avg_response_time_ms: Optional[float] = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_retrieval_count: int = 0
    avg_retrieval_time_ms: Optional[float] = None
    daily_stats: list[DailyStats]


class StatsResponse(BaseModel):
    """Full stats response."""

    chatbot_id: str
    chatbot_name: str
    stats: StatsSummary


class PerformanceMetrics(BaseModel):
    """Detailed performance metrics."""

    avg_response_time_ms: Optional[float] = None
    p50_response_time_ms: Optional[float] = None
    p95_response_time_ms: Optional[float] = None
    p99_response_time_ms: Optional[float] = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    avg_tokens_per_response: Optional[float] = None
    avg_retrieval_count: Optional[float] = None
    avg_retrieval_time_ms: Optional[float] = None


class ResponseTimeTrend(BaseModel):
    """Response time trend data point."""

    date: str
    avg_ms: float


class PerformanceStatsResponse(BaseModel):
    """Performance statistics response."""

    chatbot_id: str
    period_days: int
    metrics: PerformanceMetrics
    response_time_trend: list[ResponseTimeTrend]


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
            total_input_tokens=summary.get("total_input_tokens", 0),
            total_output_tokens=summary.get("total_output_tokens", 0),
            total_retrieval_count=summary.get("total_retrieval_count", 0),
            avg_retrieval_time_ms=summary.get("avg_retrieval_time_ms"),
            daily_stats=[
                DailyStats(
                    date=d["date"],
                    sessions=d["sessions"],
                    messages=d["messages"],
                    avg_response_time_ms=d["avg_response_time_ms"],
                    input_tokens=d.get("input_tokens", 0),
                    output_tokens=d.get("output_tokens", 0),
                    retrieval_count=d.get("retrieval_count", 0),
                )
                for d in summary["daily_stats"]
            ],
        ),
    )


@router.get("/{chatbot_id}/stats/performance", response_model=PerformanceStatsResponse)
async def get_performance_stats(
    chatbot_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
) -> PerformanceStatsResponse:
    """
    Get detailed performance statistics for a chatbot.

    Includes percentile response times (P50, P95, P99), token usage,
    and response time trends.

    Args:
        chatbot_id: Chatbot ID
        current_user: Authenticated admin user
        db: Database session
        days: Number of days to include in stats

    Returns:
        Performance statistics with percentiles

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

    # Get performance stats
    perf_stats = await StatsService.get_performance_stats(db, chatbot_id, days)

    return PerformanceStatsResponse(
        chatbot_id=chatbot_id,
        period_days=perf_stats["period_days"],
        metrics=PerformanceMetrics(
            avg_response_time_ms=perf_stats["metrics"]["avg_response_time_ms"],
            p50_response_time_ms=perf_stats["metrics"]["p50_response_time_ms"],
            p95_response_time_ms=perf_stats["metrics"]["p95_response_time_ms"],
            p99_response_time_ms=perf_stats["metrics"]["p99_response_time_ms"],
            total_input_tokens=perf_stats["metrics"]["total_input_tokens"],
            total_output_tokens=perf_stats["metrics"]["total_output_tokens"],
            avg_tokens_per_response=perf_stats["metrics"]["avg_tokens_per_response"],
            avg_retrieval_count=perf_stats["metrics"]["avg_retrieval_count"],
            avg_retrieval_time_ms=perf_stats["metrics"]["avg_retrieval_time_ms"],
        ),
        response_time_trend=[
            ResponseTimeTrend(date=t["date"], avg_ms=t["avg_ms"])
            for t in perf_stats["response_time_trend"]
        ],
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
