"""
Celery application configuration for background task processing.
"""
import asyncio
import logging

from celery import Celery
from celery.signals import worker_process_init

from src.core.config import settings

logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    "graphrag",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.workers.document_tasks",
        "src.workers.stats_tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="Asia/Seoul",
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Worker settings
    worker_concurrency=3,  # Number of concurrent workers
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory management)

    # Result backend
    result_expires=86400,  # Results expire after 24 hours

    # Task acknowledgment
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies

    # Task routing (optional)
    task_routes={
        "src.workers.document_tasks.*": {"queue": "documents"},
        "src.workers.stats_tasks.*": {"queue": "stats"},
    },

    # Beat schedule for periodic tasks
    beat_schedule={
        "aggregate-daily-stats": {
            "task": "src.workers.stats_tasks.aggregate_daily_stats",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-expired-sessions": {
            "task": "src.workers.stats_tasks.cleanup_expired_sessions",
            "schedule": 1800.0,  # Every 30 minutes
        },
    },
)


# Task base class with rate limiting for LLM operations
class OllamaRateLimitedTask(celery_app.Task):
    """
    Base task class with rate limiting for Ollama LLM requests.
    Limits concurrent LLM operations to prevent overloading.
    """

    import threading

    _semaphore = threading.Semaphore(settings.max_concurrent_llm_requests)

    def __call__(self, *args, **kwargs):
        """Execute task with semaphore for rate limiting."""
        with self._semaphore:
            return super().__call__(*args, **kwargs)


# Worker initialization - load settings from database
@worker_process_init.connect
def init_worker_process(**kwargs):
    """
    Initialize ModelManager settings when worker process starts.
    This ensures Celery workers use database settings, not just environment variables.
    """
    logger.info("Initializing ModelManager for Celery worker...")

    try:
        from src.core.model_manager import ModelManager

        # Run async initialization in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(ModelManager.initialize())
            logger.info("ModelManager initialized successfully for Celery worker")
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Failed to initialize ModelManager for Celery worker: {e}")
        # Continue anyway - will fall back to environment variables


# Export for task decorators
__all__ = ["celery_app", "OllamaRateLimitedTask"]
