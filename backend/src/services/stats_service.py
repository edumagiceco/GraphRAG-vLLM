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
from src.models.conversation import ConversationSession, Message
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

        # Get daily breakdown
        daily_stats = [
            {
                "date": s.date.isoformat(),
                "sessions": s.session_count,
                "messages": s.message_count,
                "avg_response_time_ms": s.avg_response_time_ms,
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
            "daily_stats": daily_stats,
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

        # Get or create stats record
        stats = await StatsService.get_or_create_daily_stats(db, chatbot_id, stats_date)
        stats.session_count = session_count
        stats.message_count = message_count

        await db.commit()
        await db.refresh(stats)

        logger.info(
            f"Calculated stats for {chatbot_id} on {stats_date}: "
            f"{session_count} sessions, {message_count} messages"
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
