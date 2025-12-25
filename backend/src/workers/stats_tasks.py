"""
Celery tasks for statistics aggregation and maintenance.
"""
import logging
from datetime import date, datetime, timedelta

from celery import shared_task
from sqlalchemy import select, delete, func, and_

from src.core.config import settings
from src.models.stats import ChatbotStats
from src.models.conversation import ConversationSession, Message, MessageRole
from src.models.chatbot_service import ChatbotService

logger = logging.getLogger(__name__)


def get_sync_session():
    """Create a synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    # Convert async URL to sync
    sync_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    return Session(engine)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def aggregate_daily_stats(self) -> dict:
    """
    Aggregate daily statistics for all chatbots.

    This task runs periodically (every hour) to update daily stats.

    Returns:
        Dict with aggregation results
    """
    logger.info("Starting daily stats aggregation")

    session = get_sync_session()
    results = {
        "processed_chatbots": 0,
        "stats_updated": 0,
        "errors": [],
    }

    try:
        # Get all chatbot IDs
        chatbot_ids = session.execute(select(ChatbotService.id)).scalars().all()

        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())

        for chatbot_id in chatbot_ids:
            try:
                # Count today's sessions
                session_count = session.execute(
                    select(func.count())
                    .select_from(ConversationSession)
                    .where(
                        and_(
                            ConversationSession.chatbot_id == chatbot_id,
                            ConversationSession.created_at >= start_of_day,
                            ConversationSession.created_at <= end_of_day,
                        )
                    )
                ).scalar() or 0

                # Count today's messages (via join)
                message_count = session.execute(
                    select(func.count())
                    .select_from(Message)
                    .join(
                        ConversationSession,
                        Message.session_id == ConversationSession.id,
                    )
                    .where(
                        and_(
                            ConversationSession.chatbot_id == chatbot_id,
                            Message.created_at >= start_of_day,
                            Message.created_at <= end_of_day,
                        )
                    )
                ).scalar() or 0

                # Calculate average response time from assistant messages
                response_time_result = session.execute(
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
                ).scalar()

                # Calculate token totals
                token_result = session.execute(
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
                ).one()
                total_input_tokens = token_result[0] or 0
                total_output_tokens = token_result[1] or 0

                # Calculate retrieval metrics
                retrieval_result = session.execute(
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
                ).one()
                total_retrieval_count = retrieval_result[0] or 0
                avg_retrieval_time = retrieval_result[1]

                # Get or create stats record
                stats = session.execute(
                    select(ChatbotStats).where(
                        and_(
                            ChatbotStats.chatbot_id == chatbot_id,
                            ChatbotStats.date == today,
                        )
                    )
                ).scalar_one_or_none()

                if stats:
                    stats.session_count = session_count
                    stats.message_count = message_count
                    stats.avg_response_time_ms = int(response_time_result) if response_time_result else None
                    stats.total_input_tokens = total_input_tokens
                    stats.total_output_tokens = total_output_tokens
                    stats.total_retrieval_count = total_retrieval_count
                    stats.avg_retrieval_time_ms = int(avg_retrieval_time) if avg_retrieval_time else None
                else:
                    from uuid import uuid4

                    stats = ChatbotStats(
                        id=str(uuid4()),
                        chatbot_id=chatbot_id,
                        date=today,
                        session_count=session_count,
                        message_count=message_count,
                        avg_response_time_ms=int(response_time_result) if response_time_result else None,
                        total_input_tokens=total_input_tokens,
                        total_output_tokens=total_output_tokens,
                        total_retrieval_count=total_retrieval_count,
                        avg_retrieval_time_ms=int(avg_retrieval_time) if avg_retrieval_time else None,
                    )
                    session.add(stats)

                session.commit()
                results["stats_updated"] += 1

            except Exception as e:
                logger.error(f"Failed to aggregate stats for chatbot {chatbot_id}: {e}")
                results["errors"].append(f"{chatbot_id}: {str(e)}")
                session.rollback()

            results["processed_chatbots"] += 1

        logger.info(
            f"Stats aggregation complete: {results['processed_chatbots']} chatbots, "
            f"{results['stats_updated']} stats updated, {len(results['errors'])} errors"
        )

    except Exception as e:
        logger.error(f"Stats aggregation failed: {e}")
        results["errors"].append(str(e))
        raise self.retry(exc=e)

    finally:
        session.close()

    return results


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def cleanup_expired_sessions(self) -> dict:
    """
    Clean up expired conversation sessions.

    This task runs periodically (every 30 minutes) to remove expired sessions.

    Returns:
        Dict with cleanup results
    """
    logger.info("Starting expired session cleanup")

    session = get_sync_session()
    results = {
        "deleted_sessions": 0,
        "errors": [],
    }

    try:
        now = datetime.utcnow()

        # Find and delete expired sessions
        # Messages will be deleted by CASCADE
        result = session.execute(
            delete(ConversationSession).where(
                ConversationSession.expires_at < now
            )
        )
        results["deleted_sessions"] = result.rowcount

        session.commit()

        logger.info(f"Cleaned up {results['deleted_sessions']} expired sessions")

    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        results["errors"].append(str(e))
        session.rollback()
        raise self.retry(exc=e)

    finally:
        session.close()

    return results


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def recalculate_chatbot_stats(self, chatbot_id: str, days: int = 30) -> dict:
    """
    Recalculate statistics for a specific chatbot.

    Args:
        chatbot_id: Chatbot ID to recalculate stats for
        days: Number of days to recalculate

    Returns:
        Dict with recalculation results
    """
    from uuid import uuid4

    logger.info(f"Recalculating stats for chatbot {chatbot_id}, last {days} days")

    session = get_sync_session()
    results = {
        "chatbot_id": chatbot_id,
        "days_processed": 0,
        "stats_updated": 0,
        "errors": [],
    }

    try:
        today = date.today()

        for i in range(days):
            stats_date = today - timedelta(days=i)
            start_of_day = datetime.combine(stats_date, datetime.min.time())
            end_of_day = datetime.combine(stats_date, datetime.max.time())

            try:
                # Count sessions
                session_count = session.execute(
                    select(func.count())
                    .select_from(ConversationSession)
                    .where(
                        and_(
                            ConversationSession.chatbot_id == chatbot_id,
                            ConversationSession.created_at >= start_of_day,
                            ConversationSession.created_at <= end_of_day,
                        )
                    )
                ).scalar() or 0

                # Count messages
                message_count = session.execute(
                    select(func.count())
                    .select_from(Message)
                    .join(
                        ConversationSession,
                        Message.session_id == ConversationSession.id,
                    )
                    .where(
                        and_(
                            ConversationSession.chatbot_id == chatbot_id,
                            Message.created_at >= start_of_day,
                            Message.created_at <= end_of_day,
                        )
                    )
                ).scalar() or 0

                # Calculate average response time from assistant messages
                response_time_result = session.execute(
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
                ).scalar()

                # Calculate token totals
                token_result = session.execute(
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
                ).one()
                total_input_tokens = token_result[0] or 0
                total_output_tokens = token_result[1] or 0

                # Calculate retrieval metrics
                retrieval_result = session.execute(
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
                ).one()
                total_retrieval_count = retrieval_result[0] or 0
                avg_retrieval_time = retrieval_result[1]

                # Get or create stats record
                stats = session.execute(
                    select(ChatbotStats).where(
                        and_(
                            ChatbotStats.chatbot_id == chatbot_id,
                            ChatbotStats.date == stats_date,
                        )
                    )
                ).scalar_one_or_none()

                if stats:
                    stats.session_count = session_count
                    stats.message_count = message_count
                    stats.avg_response_time_ms = int(response_time_result) if response_time_result else None
                    stats.total_input_tokens = total_input_tokens
                    stats.total_output_tokens = total_output_tokens
                    stats.total_retrieval_count = total_retrieval_count
                    stats.avg_retrieval_time_ms = int(avg_retrieval_time) if avg_retrieval_time else None
                else:
                    stats = ChatbotStats(
                        id=str(uuid4()),
                        chatbot_id=chatbot_id,
                        date=stats_date,
                        session_count=session_count,
                        message_count=message_count,
                        avg_response_time_ms=int(response_time_result) if response_time_result else None,
                        total_input_tokens=total_input_tokens,
                        total_output_tokens=total_output_tokens,
                        total_retrieval_count=total_retrieval_count,
                        avg_retrieval_time_ms=int(avg_retrieval_time) if avg_retrieval_time else None,
                    )
                    session.add(stats)

                session.commit()
                results["stats_updated"] += 1

            except Exception as e:
                logger.error(
                    f"Failed to recalculate stats for {chatbot_id} on {stats_date}: {e}"
                )
                results["errors"].append(f"{stats_date}: {str(e)}")
                session.rollback()

            results["days_processed"] += 1

        logger.info(
            f"Stats recalculation complete for {chatbot_id}: "
            f"{results['days_processed']} days, {results['stats_updated']} updated"
        )

    except Exception as e:
        logger.error(f"Stats recalculation failed for {chatbot_id}: {e}")
        results["errors"].append(str(e))
        raise self.retry(exc=e)

    finally:
        session.close()

    return results
