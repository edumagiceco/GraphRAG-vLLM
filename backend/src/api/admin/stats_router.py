"""
Admin statistics API router.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps import CurrentUser
from src.services.chatbot_service import ChatbotServiceManager
from src.services.stats_service import StatsService
from src.models.conversation import ConversationSession, Message, MessageRole


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


# =============================================================================
# Conversation Detail Schemas
# =============================================================================

class MessageDetail(BaseModel):
    """Message detail for conversation view."""
    id: str
    role: str
    content: str
    sources: Optional[list] = None
    response_time_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    retrieval_count: Optional[int] = None
    created_at: datetime


class SessionSummary(BaseModel):
    """Session summary for conversation list."""
    id: str
    message_count: int
    first_message: Optional[str] = None
    created_at: datetime
    last_message_at: Optional[datetime] = None
    total_response_time_ms: Optional[int] = None
    total_input_tokens: Optional[int] = None
    total_output_tokens: Optional[int] = None


class ConversationsResponse(BaseModel):
    """Response for conversations list."""
    chatbot_id: str
    chatbot_name: str
    date: str
    sessions: list[SessionSummary]
    total_sessions: int
    total_messages: int


class SessionDetailResponse(BaseModel):
    """Response for session detail."""
    session_id: str
    chatbot_id: str
    chatbot_name: str
    message_count: int
    created_at: datetime
    messages: list[MessageDetail]


# =============================================================================
# Conversation Detail Endpoints
# =============================================================================

@router.get("/{chatbot_id}/conversations", response_model=ConversationsResponse)
async def get_conversations_by_date(
    chatbot_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    date_str: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    search: Optional[str] = Query(None, description="Search query to filter conversations"),
) -> ConversationsResponse:
    """
    Get all conversation sessions for a chatbot on a specific date.

    Args:
        chatbot_id: Chatbot ID
        current_user: Authenticated admin user
        db: Database session
        date_str: Target date in YYYY-MM-DD format
        search: Optional search query to filter by message content

    Returns:
        List of conversation sessions with summaries
    """
    # Verify chatbot exists
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

    # Parse date
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD",
        )

    # Date boundaries
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date, datetime.max.time())

    # Query sessions for the date
    query = (
        select(ConversationSession)
        .where(
            and_(
                ConversationSession.chatbot_id == chatbot_id,
                ConversationSession.created_at >= day_start,
                ConversationSession.created_at <= day_end,
            )
        )
        .order_by(ConversationSession.created_at.desc())
    )

    result = await db.execute(query)
    sessions = result.scalars().all()

    # Build session summaries
    session_summaries = []
    total_messages = 0

    for session in sessions:
        # Get messages for this session
        msg_query = (
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.created_at.asc())
        )
        msg_result = await db.execute(msg_query)
        messages = msg_result.scalars().all()

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            has_match = any(search_lower in msg.content.lower() for msg in messages)
            if not has_match:
                continue

        # Get first user message
        first_user_msg = next(
            (m for m in messages if m.role == MessageRole.USER),
            None
        )
        first_message = first_user_msg.content[:100] if first_user_msg else None

        # Get last message time
        last_msg = messages[-1] if messages else None
        last_message_at = last_msg.created_at if last_msg else None

        # Calculate totals from assistant messages
        assistant_messages = [m for m in messages if m.role == MessageRole.ASSISTANT]
        total_response_time = sum(m.response_time_ms or 0 for m in assistant_messages)
        total_input = sum(m.input_tokens or 0 for m in assistant_messages)
        total_output = sum(m.output_tokens or 0 for m in assistant_messages)

        session_summaries.append(SessionSummary(
            id=session.id,
            message_count=len(messages),
            first_message=first_message,
            created_at=session.created_at,
            last_message_at=last_message_at,
            total_response_time_ms=total_response_time if total_response_time > 0 else None,
            total_input_tokens=total_input if total_input > 0 else None,
            total_output_tokens=total_output if total_output > 0 else None,
        ))
        total_messages += len(messages)

    return ConversationsResponse(
        chatbot_id=chatbot_id,
        chatbot_name=chatbot.name,
        date=date_str,
        sessions=session_summaries,
        total_sessions=len(session_summaries),
        total_messages=total_messages,
    )


@router.get("/{chatbot_id}/conversations/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    chatbot_id: str,
    session_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SessionDetailResponse:
    """
    Get detailed messages for a specific conversation session.

    Args:
        chatbot_id: Chatbot ID
        session_id: Session ID
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Session detail with all messages
    """
    # Verify chatbot exists
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

    # Get session
    session_result = await db.execute(
        select(ConversationSession).where(
            and_(
                ConversationSession.id == session_id,
                ConversationSession.chatbot_id == chatbot_id,
            )
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Get messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return SessionDetailResponse(
        session_id=session_id,
        chatbot_id=chatbot_id,
        chatbot_name=chatbot.name,
        message_count=len(messages),
        created_at=session.created_at,
        messages=[
            MessageDetail(
                id=msg.id,
                role=msg.role.value,
                content=msg.content,
                sources=msg.sources,
                response_time_ms=msg.response_time_ms,
                input_tokens=msg.input_tokens,
                output_tokens=msg.output_tokens,
                retrieval_count=msg.retrieval_count,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )
