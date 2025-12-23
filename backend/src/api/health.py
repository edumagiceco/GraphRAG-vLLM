"""
Health check API endpoint.
"""
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from src.core.neo4j import Neo4jClient
from src.core.redis import RedisClient
from src.core.qdrant import QdrantManager
from src.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class ServiceHealth(BaseModel):
    """Health status for a service."""

    name: str
    status: str  # "healthy", "unhealthy", "degraded"
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str  # "healthy", "unhealthy", "degraded"
    services: list[ServiceHealth]


async def check_neo4j_health() -> ServiceHealth:
    """Check Neo4j connection health."""
    try:
        result = await Neo4jClient.execute_query("RETURN 1 as n")
        if result:
            return ServiceHealth(name="neo4j", status="healthy")
        return ServiceHealth(
            name="neo4j",
            status="unhealthy",
            message="No response from query",
        )
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        return ServiceHealth(
            name="neo4j",
            status="unhealthy",
            message=str(e),
        )


async def check_redis_health() -> ServiceHealth:
    """Check Redis connection health."""
    try:
        client = await RedisClient.get_client()
        await client.ping()
        return ServiceHealth(name="redis", status="healthy")
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return ServiceHealth(
            name="redis",
            status="unhealthy",
            message=str(e),
        )


async def check_qdrant_health() -> ServiceHealth:
    """Check Qdrant connection health."""
    try:
        client = QdrantManager.get_client()
        client.get_collections()
        return ServiceHealth(name="qdrant", status="healthy")
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        return ServiceHealth(
            name="qdrant",
            status="unhealthy",
            message=str(e),
        )


async def check_celery_health() -> ServiceHealth:
    """Check Celery worker health."""
    try:
        from src.core.celery_app import celery_app

        inspector = celery_app.control.inspect()
        stats = inspector.stats()

        if stats:
            worker_count = len(stats)
            return ServiceHealth(
                name="celery",
                status="healthy",
                message=f"{worker_count} worker(s) active",
            )
        return ServiceHealth(
            name="celery",
            status="degraded",
            message="No active workers",
        )
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return ServiceHealth(
            name="celery",
            status="unhealthy",
            message=str(e),
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check endpoint.

    Checks the health of all dependent services:
    - Neo4j
    - Redis
    - Qdrant
    - Celery workers

    Returns:
        Health status of all services
    """
    services = []

    # Check all services
    services.append(await check_neo4j_health())
    services.append(await check_redis_health())
    services.append(await check_qdrant_health())
    services.append(await check_celery_health())

    # Determine overall status
    statuses = [s.status for s in services]

    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        services=services,
    )


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.

    Simply returns OK if the application is running.
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.

    Returns OK if critical services (Neo4j, Redis) are available.
    """
    neo4j_health = await check_neo4j_health()
    redis_health = await check_redis_health()

    if neo4j_health.status == "healthy" and redis_health.status == "healthy":
        return {"status": "ready"}

    return {
        "status": "not ready",
        "services": {
            "neo4j": neo4j_health.status,
            "redis": redis_health.status,
        },
    }
