"""
Statistics service for chatbot analytics.
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.stats import ChatbotStats
from src.models.conversation import ConversationSession, Message, MessageRole
from src.models.chatbot_service import ChatbotService

logger = logging.getLogger(__name__)


class StatsService:
    """Service for managing chatbot statistics."""

    @staticmethod
    async def get_or_create_daily_stats(
        db: AsyncSession,
        chatbot_id: str,
        stats_date: date,
    ) -> ChatbotStats:
        """
        Get or create daily stats record for a chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            stats_date: Date for stats

        Returns:
            ChatbotStats record
        """
        # Try to find existing
        result = await db.execute(
            select(ChatbotStats).where(
                and_(
                    ChatbotStats.chatbot_id == chatbot_id,
                    ChatbotStats.date == stats_date,
                )
            )
        )
        stats = result.scalar_one_or_none()

        if stats:
            return stats

        # Create new
        stats = ChatbotStats(
            id=str(uuid4()),
            chatbot_id=chatbot_id,
            date=stats_date,
            session_count=0,
            message_count=0,
            avg_response_time_ms=None,
        )
        db.add(stats)
        await db.commit()
        await db.refresh(stats)

        return stats

    @staticmethod
    async def increment_session_count(
        db: AsyncSession,
        chatbot_id: str,
        stats_date: Optional[date] = None,
    ) -> ChatbotStats:
        """
        Increment session count for a chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            stats_date: Date for stats (defaults to today)

        Returns:
            Updated ChatbotStats
        """
        stats_date = stats_date or date.today()
        stats = await StatsService.get_or_create_daily_stats(db, chatbot_id, stats_date)
        stats.session_count += 1
        await db.commit()
        await db.refresh(stats)
        return stats

    @staticmethod
    async def increment_message_count(
        db: AsyncSession,
        chatbot_id: str,
        count: int = 1,
        stats_date: Optional[date] = None,
    ) -> ChatbotStats:
        """
        Increment message count for a chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            count: Number of messages to add
            stats_date: Date for stats (defaults to today)

        Returns:
            Updated ChatbotStats
        """
        stats_date = stats_date or date.today()
        stats = await StatsService.get_or_create_daily_stats(db, chatbot_id, stats_date)
        stats.message_count += count
        await db.commit()
        await db.refresh(stats)
        return stats

    @staticmethod
    async def get_stats_range(
        db: AsyncSession,
        chatbot_id: str,
        start_date: date,
        end_date: date,
    ) -> list[ChatbotStats]:
        """
        Get stats for a date range.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of ChatbotStats
        """
        result = await db.execute(
            select(ChatbotStats)
            .where(
                and_(
                    ChatbotStats.chatbot_id == chatbot_id,
                    ChatbotStats.date >= start_date,
                    ChatbotStats.date <= end_date,
                )
            )
            .order_by(ChatbotStats.date)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_summary_stats(
        db: AsyncSession,
        chatbot_id: str,
        days: int = 30,
    ) -> dict:
        """
        Get summary statistics for a chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            days: Number of days to include

        Returns:
            Summary statistics dict
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Get stats for the period
        stats_list = await StatsService.get_stats_range(
            db, chatbot_id, start_date, end_date
        )

        # Calculate totals
        total_sessions = sum(s.session_count for s in stats_list)
        total_messages = sum(s.message_count for s in stats_list)

        # Calculate average response time (excluding nulls)
        response_times = [s.avg_response_time_ms for s in stats_list if s.avg_response_time_ms]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else None
        )

        # Calculate token totals
        total_input_tokens = sum(s.total_input_tokens or 0 for s in stats_list)
        total_output_tokens = sum(s.total_output_tokens or 0 for s in stats_list)

        # Calculate retrieval totals
        total_retrieval_count = sum(s.total_retrieval_count or 0 for s in stats_list)
        retrieval_times = [s.avg_retrieval_time_ms for s in stats_list if s.avg_retrieval_time_ms]
        avg_retrieval_time = (
            sum(retrieval_times) / len(retrieval_times) if retrieval_times else None
        )

        # Get daily breakdown
        daily_stats = [
            {
                "date": s.date.isoformat(),
                "sessions": s.session_count,
                "messages": s.message_count,
                "avg_response_time_ms": s.avg_response_time_ms,
                "input_tokens": s.total_input_tokens or 0,
                "output_tokens": s.total_output_tokens or 0,
                "retrieval_count": s.total_retrieval_count or 0,
            }
            for s in stats_list
        ]

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_response_time_ms": avg_response_time,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_retrieval_count": total_retrieval_count,
            "avg_retrieval_time_ms": avg_retrieval_time,
            "daily_stats": daily_stats,
        }

    @staticmethod
    async def get_performance_stats(
        db: AsyncSession,
        chatbot_id: str,
        days: int = 7,
    ) -> dict:
        """
        Get detailed performance statistics including percentiles.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            days: Number of days to include

        Returns:
            Performance statistics dict with percentiles
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get all response times for percentile calculation
        response_times_result = await db.execute(
            select(Message.response_time_ms)
            .join(ConversationSession, Message.session_id == ConversationSession.id)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot_id,
                    Message.created_at >= start_date,
                    Message.created_at <= end_date,
                    Message.role == MessageRole.ASSISTANT,
                    Message.response_time_ms.isnot(None),
                )
            )
            .order_by(Message.response_time_ms)
        )
        response_times = [row[0] for row in response_times_result.fetchall()]

        # Calculate percentiles
        def percentile(data: list, p: float) -> Optional[float]:
            if not data:
                return None
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f]) if f != c else data[f]

        p50 = percentile(response_times, 50)
        p95 = percentile(response_times, 95)
        p99 = percentile(response_times, 99)
        avg_response_time = sum(response_times) / len(response_times) if response_times else None

        # Get token aggregates
        token_result = await db.execute(
            select(
                func.sum(Message.input_tokens),
                func.sum(Message.output_tokens),
                func.count(Message.id),
            )
            .join(ConversationSession, Message.session_id == ConversationSession.id)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot_id,
                    Message.created_at >= start_date,
                    Message.created_at <= end_date,
                    Message.role == MessageRole.ASSISTANT,
                )
            )
        )
        token_row = token_result.one()
        total_input_tokens = token_row[0] or 0
        total_output_tokens = token_row[1] or 0
        message_count = token_row[2] or 0

        avg_tokens_per_response = (
            (total_input_tokens + total_output_tokens) / message_count
            if message_count > 0 else None
        )

        # Get retrieval aggregates
        retrieval_result = await db.execute(
            select(
                func.avg(Message.retrieval_count),
                func.avg(Message.retrieval_time_ms),
            )
            .join(ConversationSession, Message.session_id == ConversationSession.id)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot_id,
                    Message.created_at >= start_date,
                    Message.created_at <= end_date,
                    Message.role == MessageRole.ASSISTANT,
                )
            )
        )
        retrieval_row = retrieval_result.one()
        avg_retrieval_count = float(retrieval_row[0]) if retrieval_row[0] else None
        avg_retrieval_time = float(retrieval_row[1]) if retrieval_row[1] else None

        # Get daily response time trend
        daily_trend_result = await db.execute(
            select(
                func.date(Message.created_at).label("date"),
                func.avg(Message.response_time_ms).label("avg_ms"),
            )
            .join(ConversationSession, Message.session_id == ConversationSession.id)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot_id,
                    Message.created_at >= start_date,
                    Message.created_at <= end_date,
                    Message.role == MessageRole.ASSISTANT,
                    Message.response_time_ms.isnot(None),
                )
            )
            .group_by(func.date(Message.created_at))
            .order_by(func.date(Message.created_at))
        )
        response_time_trend = [
            {"date": str(row.date), "avg_ms": round(row.avg_ms, 0) if row.avg_ms else 0}
            for row in daily_trend_result.fetchall()
        ]

        return {
            "chatbot_id": chatbot_id,
            "period_days": days,
            "metrics": {
                "avg_response_time_ms": round(avg_response_time, 0) if avg_response_time else None,
                "p50_response_time_ms": round(p50, 0) if p50 else None,
                "p95_response_time_ms": round(p95, 0) if p95 else None,
                "p99_response_time_ms": round(p99, 0) if p99 else None,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "avg_tokens_per_response": round(avg_tokens_per_response, 0) if avg_tokens_per_response else None,
                "avg_retrieval_count": round(avg_retrieval_count, 1) if avg_retrieval_count else None,
                "avg_retrieval_time_ms": round(avg_retrieval_time, 0) if avg_retrieval_time else None,
            },
            "response_time_trend": response_time_trend,
        }

    @staticmethod
    async def calculate_daily_stats(
        db: AsyncSession,
        chatbot_id: str,
        stats_date: date,
    ) -> ChatbotStats:
        """
        Calculate and update daily stats from conversation data.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            stats_date: Date to calculate stats for

        Returns:
            Updated ChatbotStats
        """
        # Calculate date boundaries
        start_of_day = datetime.combine(stats_date, datetime.min.time())
        end_of_day = datetime.combine(stats_date, datetime.max.time())

        # Count sessions
        session_result = await db.execute(
            select(func.count())
            .select_from(ConversationSession)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot_id,
                    ConversationSession.created_at >= start_of_day,
                    ConversationSession.created_at <= end_of_day,
                )
            )
        )
        session_count = session_result.scalar() or 0

        # Count messages for this chatbot on this day
        message_result = await db.execute(
            select(func.count())
            .select_from(Message)
            .join(ConversationSession, Message.session_id == ConversationSession.id)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot_id,
                    Message.created_at >= start_of_day,
                    Message.created_at <= end_of_day,
                )
            )
        )
        message_count = message_result.scalar() or 0

        # Calculate average response time from assistant messages
        response_time_result = await db.execute(
            select(func.avg(Message.response_time_ms))
            .join(ConversationSession, Message.session_id == ConversationSession.id)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot_id,
                    Message.created_at >= start_of_day,
                    Message.created_at <= end_of_day,
                    Message.role == MessageRole.ASSISTANT,
                    Message.response_time_ms.isnot(None),
                )
            )
        )
        avg_response_time = response_time_result.scalar()

        # Calculate token totals
        token_result = await db.execute(
            select(
                func.sum(Message.input_tokens),
                func.sum(Message.output_tokens),
            )
            .join(ConversationSession, Message.session_id == ConversationSession.id)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot_id,
                    Message.created_at >= start_of_day,
                    Message.created_at <= end_of_day,
                    Message.role == MessageRole.ASSISTANT,
                )
            )
        )
        token_row = token_result.one()
        total_input_tokens = token_row[0] or 0
        total_output_tokens = token_row[1] or 0

        # Calculate retrieval metrics
        retrieval_result = await db.execute(
            select(
                func.sum(Message.retrieval_count),
                func.avg(Message.retrieval_time_ms),
            )
            .join(ConversationSession, Message.session_id == ConversationSession.id)
            .where(
                and_(
                    ConversationSession.chatbot_id == chatbot_id,
                    Message.created_at >= start_of_day,
                    Message.created_at <= end_of_day,
                    Message.role == MessageRole.ASSISTANT,
                )
            )
        )
        retrieval_row = retrieval_result.one()
        total_retrieval_count = retrieval_row[0] or 0
        avg_retrieval_time = retrieval_row[1]

        # Get or create stats record
        stats = await StatsService.get_or_create_daily_stats(db, chatbot_id, stats_date)
        stats.session_count = session_count
        stats.message_count = message_count
        stats.avg_response_time_ms = int(avg_response_time) if avg_response_time else None
        stats.total_input_tokens = total_input_tokens
        stats.total_output_tokens = total_output_tokens
        stats.total_retrieval_count = total_retrieval_count
        stats.avg_retrieval_time_ms = int(avg_retrieval_time) if avg_retrieval_time else None

        await db.commit()
        await db.refresh(stats)

        logger.info(
            f"Calculated stats for {chatbot_id} on {stats_date}: "
            f"{session_count} sessions, {message_count} messages, "
            f"avg_response={avg_response_time}ms, tokens={total_input_tokens}+{total_output_tokens}"
        )

        return stats

    @staticmethod
    async def recalculate_all_stats(
        db: AsyncSession,
        chatbot_id: str,
        days: int = 30,
    ) -> list[ChatbotStats]:
        """
        Recalculate stats for a chatbot for the last N days.

        Args:
            db: Database session
            chatbot_id: Chatbot ID
            days: Number of days to recalculate

        Returns:
            List of updated ChatbotStats
        """
        results = []
        today = date.today()

        for i in range(days):
            stats_date = today - timedelta(days=i)
            stats = await StatsService.calculate_daily_stats(db, chatbot_id, stats_date)
            results.append(stats)

        return results

    @staticmethod
    async def get_all_chatbot_ids(db: AsyncSession) -> list[str]:
        """
        Get all chatbot IDs.

        Args:
            db: Database session

        Returns:
            List of chatbot IDs
        """
        result = await db.execute(select(ChatbotService.id))
        return [row[0] for row in result.fetchall()]
