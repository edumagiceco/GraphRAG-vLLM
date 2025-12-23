"""
Redis client for caching and progress tracking (Pub/Sub).
"""
import json
from typing import Any, Dict, Optional

import redis.asyncio as redis

from src.core.config import settings


class RedisClient:
    """Async Redis client for caching and pub/sub operations."""

    _client: Optional[redis.Redis] = None
    _pubsub: Optional[redis.client.PubSub] = None

    @classmethod
    async def connect(cls) -> None:
        """Initialize Redis connection."""
        if cls._client is None:
            cls._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Verify connectivity
            await cls._client.ping()

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection."""
        if cls._pubsub is not None:
            await cls._pubsub.close()
            cls._pubsub = None
        if cls._client is not None:
            await cls._client.close()
            cls._client = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get Redis client instance."""
        if cls._client is None:
            await cls.connect()
        return cls._client

    # =========================================================================
    # Basic Key-Value Operations
    # =========================================================================

    @classmethod
    async def get(cls, key: str) -> Optional[str]:
        """Get value by key."""
        client = await cls.get_client()
        return await client.get(key)

    @classmethod
    async def set(
        cls,
        key: str,
        value: str,
        expire_seconds: Optional[int] = None,
    ) -> None:
        """Set key-value pair with optional expiration."""
        client = await cls.get_client()
        await client.set(key, value, ex=expire_seconds)

    @classmethod
    async def delete(cls, key: str) -> None:
        """Delete key."""
        client = await cls.get_client()
        await client.delete(key)

    @classmethod
    async def exists(cls, key: str) -> bool:
        """Check if key exists."""
        client = await cls.get_client()
        return bool(await client.exists(key))

    # =========================================================================
    # Hash Operations (for structured data)
    # =========================================================================

    @classmethod
    async def hset(cls, name: str, mapping: Dict[str, Any]) -> None:
        """Set multiple hash fields."""
        client = await cls.get_client()
        # Convert non-string values to JSON
        serialized = {
            k: json.dumps(v) if not isinstance(v, str) else v
            for k, v in mapping.items()
        }
        await client.hset(name, mapping=serialized)

    @classmethod
    async def hget(cls, name: str, key: str) -> Optional[str]:
        """Get hash field value."""
        client = await cls.get_client()
        return await client.hget(name, key)

    @classmethod
    async def hgetall(cls, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        client = await cls.get_client()
        return await client.hgetall(name)

    # =========================================================================
    # Document Progress Tracking
    # =========================================================================

    @classmethod
    def get_progress_key(cls, document_id: str) -> str:
        """Get Redis key for document progress."""
        return f"doc_progress:{document_id}"

    @classmethod
    async def set_document_progress(
        cls,
        document_id: str,
        progress: int,
        stage: str,
        error: Optional[str] = None,
    ) -> None:
        """
        Update document processing progress.

        Args:
            document_id: Document ID
            progress: Progress percentage (0-100, -1 for error)
            stage: Current processing stage
            error: Error message if failed
        """
        key = cls.get_progress_key(document_id)
        data = {
            "progress": progress,
            "stage": stage,
            "error": error or "",
        }
        await cls.hset(key, data)

        # Also publish for real-time updates
        await cls.publish_progress(document_id, data)

        # Set expiration (1 hour after completion/failure)
        if progress == 100 or progress == -1:
            client = await cls.get_client()
            await client.expire(key, 3600)

    @classmethod
    async def get_document_progress(
        cls,
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get document processing progress.

        Args:
            document_id: Document ID

        Returns:
            Progress data dict or None if not found
        """
        key = cls.get_progress_key(document_id)
        data = await cls.hgetall(key)

        if not data:
            return None

        return {
            "progress": int(data.get("progress", 0)),
            "stage": data.get("stage", "unknown"),
            "error": data.get("error") or None,
        }

    @classmethod
    async def delete_document_progress(cls, document_id: str) -> None:
        """
        Delete document progress from Redis.

        Args:
            document_id: Document ID
        """
        key = cls.get_progress_key(document_id)
        await cls.delete(key)

    # =========================================================================
    # Pub/Sub Operations
    # =========================================================================

    @classmethod
    async def publish_progress(
        cls,
        document_id: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Publish document progress update.

        Args:
            document_id: Document ID
            data: Progress data
        """
        client = await cls.get_client()
        channel = f"doc_progress:{document_id}"
        await client.publish(channel, json.dumps(data))

    @classmethod
    async def subscribe_progress(
        cls,
        document_id: str,
    ) -> redis.client.PubSub:
        """
        Subscribe to document progress updates.

        Args:
            document_id: Document ID

        Returns:
            PubSub instance for receiving messages
        """
        client = await cls.get_client()
        pubsub = client.pubsub()
        channel = f"doc_progress:{document_id}"
        await pubsub.subscribe(channel)
        return pubsub


# Synchronous Redis client for Celery workers
class SyncRedisClient:
    """Synchronous Redis client for use in Celery tasks."""

    _client: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get synchronous Redis client."""
        if cls._client is None:
            # Use synchronous redis library
            import redis as sync_redis

            cls._client = sync_redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return cls._client

    @classmethod
    def set_document_progress(
        cls,
        document_id: str,
        progress: int,
        stage: str,
        error: Optional[str] = None,
    ) -> None:
        """Update document progress (synchronous version for Celery)."""
        client = cls.get_client()
        key = f"doc_progress:{document_id}"
        data = {
            "progress": str(progress),
            "stage": stage,
            "error": error or "",
        }
        client.hset(key, mapping=data)

        # Publish for real-time updates
        client.publish(key, json.dumps(data))

        # Set expiration on completion
        if progress == 100 or progress == -1:
            client.expire(key, 3600)


# Convenience functions for dependency injection
async def get_redis() -> RedisClient:
    """Get async Redis client."""
    return RedisClient


def get_sync_redis() -> SyncRedisClient:
    """Get sync Redis client for Celery tasks."""
    return SyncRedisClient
