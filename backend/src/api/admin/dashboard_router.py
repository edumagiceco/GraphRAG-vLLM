"""
Dashboard API router for system overview and statistics.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.config import settings
from src.api.deps import CurrentUser
from src.models.chatbot_service import ChatbotService, ChatbotStatus
from src.models.conversation import ConversationSession, Message, MessageRole
from src.models.document import Document
from src.models.stats import ChatbotStats


router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================

class ChatbotSummary(BaseModel):
    """Summary of a chatbot for dashboard."""
    id: str
    name: str
    status: str
    today_sessions: int = 0
    today_messages: int = 0
    total_documents: int = 0


class SystemStatus(BaseModel):
    """System component status."""
    database: str = "healthy"
    neo4j: str = "healthy"
    redis: str = "healthy"
    qdrant: str = "healthy"
    llm: str = "healthy"


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    total_chatbots: int = 0
    active_chatbots: int = 0
    today_sessions: int = 0
    today_messages: int = 0
    week_sessions: int = 0
    week_messages: int = 0
    avg_response_time_ms: Optional[float] = None
    total_tokens_today: int = 0


class DashboardResponse(BaseModel):
    """Full dashboard response."""
    stats: DashboardStats
    recent_chatbots: list[ChatbotSummary]
    system_status: SystemStatus


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard overview with statistics and system status.

    Provides:
    - Overall chatbot counts
    - Today's and this week's session/message counts
    - Average response time
    - Recent active chatbots
    - System component status
    """
    today = date.today()
    week_ago = today - timedelta(days=7)

    # Get chatbot counts
    total_chatbots_result = await db.execute(
        select(func.count()).select_from(ChatbotService)
    )
    total_chatbots = total_chatbots_result.scalar() or 0

    active_chatbots_result = await db.execute(
        select(func.count())
        .select_from(ChatbotService)
        .where(ChatbotService.status == ChatbotStatus.ACTIVE)
    )
    active_chatbots = active_chatbots_result.scalar() or 0

    # Get today's stats
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    today_sessions_result = await db.execute(
        select(func.count())
        .select_from(ConversationSession)
        .where(
            and_(
                ConversationSession.created_at >= today_start,
                ConversationSession.created_at <= today_end,
            )
        )
    )
    today_sessions = today_sessions_result.scalar() or 0

    today_messages_result = await db.execute(
        select(func.count())
        .select_from(Message)
        .where(
            and_(
                Message.created_at >= today_start,
                Message.created_at <= today_end,
            )
        )
    )
    today_messages = today_messages_result.scalar() or 0

    # Get this week's stats
    week_start = datetime.combine(week_ago, datetime.min.time())

    week_sessions_result = await db.execute(
        select(func.count())
        .select_from(ConversationSession)
        .where(ConversationSession.created_at >= week_start)
    )
    week_sessions = week_sessions_result.scalar() or 0

    week_messages_result = await db.execute(
        select(func.count())
        .select_from(Message)
        .where(Message.created_at >= week_start)
    )
    week_messages = week_messages_result.scalar() or 0

    # Get average response time (last 7 days)
    avg_response_result = await db.execute(
        select(func.avg(Message.response_time_ms))
        .where(
            and_(
                Message.created_at >= week_start,
                Message.role == MessageRole.ASSISTANT,
                Message.response_time_ms.isnot(None),
            )
        )
    )
    avg_response_time = avg_response_result.scalar()

    # Get today's token usage
    tokens_result = await db.execute(
        select(
            func.coalesce(func.sum(Message.input_tokens), 0),
            func.coalesce(func.sum(Message.output_tokens), 0),
        )
        .where(
            and_(
                Message.created_at >= today_start,
                Message.created_at <= today_end,
                Message.role == MessageRole.ASSISTANT,
            )
        )
    )
    tokens_row = tokens_result.one()
    total_tokens_today = (tokens_row[0] or 0) + (tokens_row[1] or 0)

    # Get recent chatbots with today's activity
    chatbots_result = await db.execute(
        select(ChatbotService)
        .order_by(ChatbotService.updated_at.desc())
        .limit(5)
    )
    chatbots = chatbots_result.scalars().all()

    recent_chatbots = []
    for chatbot in chatbots:
        # Get today's stats for this chatbot
        chatbot_sessions_result = await db.execute(
            select(func.count())
            .select_from(ConversationSession)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot.id,
                    ConversationSession.created_at >= today_start,
                    ConversationSession.created_at <= today_end,
                )
            )
        )
        chatbot_sessions = chatbot_sessions_result.scalar() or 0

        chatbot_messages_result = await db.execute(
            select(func.count())
            .select_from(Message)
            .join(ConversationSession, Message.session_id == ConversationSession.id)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot.id,
                    Message.created_at >= today_start,
                    Message.created_at <= today_end,
                )
            )
        )
        chatbot_messages = chatbot_messages_result.scalar() or 0

        # Get document count for this chatbot
        doc_count_result = await db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.chatbot_id == chatbot.id)
        )
        doc_count = doc_count_result.scalar() or 0

        recent_chatbots.append(ChatbotSummary(
            id=chatbot.id,
            name=chatbot.name,
            status=chatbot.status.value,
            today_sessions=chatbot_sessions,
            today_messages=chatbot_messages,
            total_documents=doc_count,
        ))

    # Check system status
    system_status = await check_system_status()

    return DashboardResponse(
        stats=DashboardStats(
            total_chatbots=total_chatbots,
            active_chatbots=active_chatbots,
            today_sessions=today_sessions,
            today_messages=today_messages,
            week_sessions=week_sessions,
            week_messages=week_messages,
            avg_response_time_ms=round(avg_response_time, 0) if avg_response_time else None,
            total_tokens_today=total_tokens_today,
        ),
        recent_chatbots=recent_chatbots,
        system_status=system_status,
    )


async def check_system_status() -> SystemStatus:
    """Check status of all system components."""
    from src.core.neo4j import Neo4jClient
    from src.core.redis import RedisClient

    status = SystemStatus()

    # Check Neo4j
    try:
        if Neo4jClient._driver:
            await Neo4jClient._driver.verify_connectivity()
            status.neo4j = "healthy"
        else:
            status.neo4j = "disconnected"
    except Exception:
        status.neo4j = "error"

    # Check Redis
    try:
        if RedisClient._client:
            await RedisClient._client.ping()
            status.redis = "healthy"
        else:
            status.redis = "disconnected"
    except Exception:
        status.redis = "error"

    # Check LLM (vLLM or Ollama)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            if settings.llm_backend == "vllm":
                # vLLM uses OpenAI-compatible API, check /models endpoint
                response = await client.get(f"{settings.vllm_base_url}/models")
            else:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
            status.llm = "healthy" if response.status_code == 200 else "error"
    except Exception:
        status.llm = "error"

    return status
