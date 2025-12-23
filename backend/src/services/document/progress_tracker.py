"""
Document processing progress tracker using Redis Pub/Sub.
"""
import asyncio
from typing import AsyncIterator, Optional

import redis.asyncio as aioredis

from src.core.config import settings


class ProgressTracker:
    """
    Progress tracker for document processing using Redis Pub/Sub.
    Allows real-time progress updates to connected clients.
    """

    PROGRESS_KEY_PREFIX = "doc_progress:"
    PROGRESS_CHANNEL_PREFIX = "progress:"
    PROGRESS_TTL = 86400  # 24 hours

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize progress tracker.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url)
        return self._redis

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _get_progress_key(self, document_id: str) -> str:
        """Get Redis key for document progress."""
        return f"{self.PROGRESS_KEY_PREFIX}{document_id}"

    def _get_channel_name(self, document_id: str) -> str:
        """Get Redis Pub/Sub channel name."""
        return f"{self.PROGRESS_CHANNEL_PREFIX}{document_id}"

    async def set_progress(
        self,
        document_id: str,
        progress: int,
        stage: str,
        message: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Set document processing progress.

        Args:
            document_id: Document ID
            progress: Progress percentage (0-100, -1 for error)
            stage: Current processing stage
            message: Optional status message
            error: Optional error message
        """
        redis = await self._get_redis()
        key = self._get_progress_key(document_id)

        data = {
            "progress": str(progress),
            "stage": stage,
        }
        if message:
            data["message"] = message
        if error:
            data["error"] = error

        # Store progress in hash
        await redis.hset(key, mapping=data)
        await redis.expire(key, self.PROGRESS_TTL)

        # Publish progress update
        channel = self._get_channel_name(document_id)
        await redis.publish(channel, f"{progress}:{stage}:{error or ''}")

    async def get_progress(self, document_id: str) -> Optional[dict]:
        """
        Get current progress for a document.

        Args:
            document_id: Document ID

        Returns:
            Progress dict or None if not found
        """
        redis = await self._get_redis()
        key = self._get_progress_key(document_id)

        data = await redis.hgetall(key)
        if not data:
            return None

        return {
            "progress": int(data.get(b"progress", 0)),
            "stage": data.get(b"stage", b"").decode(),
            "message": data.get(b"message", b"").decode() or None,
            "error": data.get(b"error", b"").decode() or None,
        }

    async def delete_progress(self, document_id: str) -> bool:
        """
        Delete progress data for a document.

        Args:
            document_id: Document ID

        Returns:
            True if deleted
        """
        redis = await self._get_redis()
        key = self._get_progress_key(document_id)
        result = await redis.delete(key)
        return result > 0

    async def subscribe_progress(
        self,
        document_id: str,
        timeout: float = 300.0,
    ) -> AsyncIterator[dict]:
        """
        Subscribe to progress updates for a document.

        Args:
            document_id: Document ID
            timeout: Subscription timeout in seconds

        Yields:
            Progress update dicts
        """
        redis = await self._get_redis()
        channel = self._get_channel_name(document_id)

        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        try:
            start_time = asyncio.get_event_loop().time()

            async for message in pubsub.listen():
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    break

                if message["type"] == "message":
                    data = message["data"].decode()
                    parts = data.split(":", 2)

                    progress = int(parts[0]) if parts else 0
                    stage = parts[1] if len(parts) > 1 else ""
                    error = parts[2] if len(parts) > 2 and parts[2] else None

                    yield {
                        "progress": progress,
                        "stage": stage,
                        "error": error,
                    }

                    # Stop if completed or failed
                    if progress == 100 or progress < 0:
                        break

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()


# Singleton instance
_tracker_instance: Optional[ProgressTracker] = None


async def get_progress_tracker() -> ProgressTracker:
    """Get or create singleton progress tracker."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ProgressTracker()
    return _tracker_instance


async def set_document_progress(
    document_id: str,
    progress: int,
    stage: str,
    error: Optional[str] = None,
) -> None:
    """
    Convenience function to set document progress.

    Args:
        document_id: Document ID
        progress: Progress percentage
        stage: Current stage
        error: Optional error message
    """
    tracker = await get_progress_tracker()
    await tracker.set_progress(document_id, progress, stage, error=error)


async def get_document_progress(document_id: str) -> Optional[dict]:
    """
    Convenience function to get document progress.

    Args:
        document_id: Document ID

    Returns:
        Progress dict or None
    """
    tracker = await get_progress_tracker()
    return await tracker.get_progress(document_id)
