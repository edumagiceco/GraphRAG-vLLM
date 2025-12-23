"""
FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import init_db, close_db
from src.core.neo4j import Neo4jClient
from src.core.redis import RedisClient
from src.core.logging import setup_logging, setup_request_logging
from src.core.exceptions import setup_exception_handlers


# Setup logging before anything else
setup_logging()


async def create_initial_admin() -> None:
    """Create initial admin user if not exists."""
    import logging
    from src.core.database import async_session_maker
    from src.services.auth_service import AuthService

    logger = logging.getLogger(__name__)

    async with async_session_maker() as session:
        admin = await AuthService.create_initial_admin(session)
        if admin:
            logger.info(f"Created initial admin user: {admin.email}")
        else:
            logger.info("Admin user already exists")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.
    Manages startup and shutdown events.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Startup
    logger.info("Starting up GraphRAG Chatbot Platform...")

    # Initialize database connections
    await init_db()
    logger.info("PostgreSQL connected")

    # Create initial admin user
    await create_initial_admin()

    await Neo4jClient.connect()
    logger.info("Neo4j connected")

    await RedisClient.connect()
    logger.info("Redis connected")

    # Qdrant is connected on-demand (no persistent connection needed)
    logger.info("Qdrant ready")

    logger.info("All services initialized successfully!")

    yield

    # Shutdown
    logger.info("Shutting down...")

    await RedisClient.close()
    await Neo4jClient.close()
    await close_db()

    logger.info("All connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="PDF 기반 GraphRAG 챗봇 플랫폼 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Setup exception handlers
setup_exception_handlers(app)

# Setup request logging
setup_request_logging(app)

# Configure CORS
cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:13000",
    "http://127.0.0.1:13000",
    "http://192.168.1.39:13000",
]

# Add production origin from settings if available
if hasattr(settings, 'cors_origins') and settings.cors_origins:
    cors_origins.extend(settings.cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# API Routes
# =============================================================================

# API version prefix
API_V1_PREFIX = "/api/v1"


# Import and include routers
from src.api.auth.router import router as auth_router
from src.api.admin.chatbot_router import router as chatbot_router
from src.api.admin.document_router import router as document_router
from src.api.chat.router import router as chat_router
from src.api.admin.stats_router import router as stats_router
from src.api.admin.version_router import router as version_router
from src.api.health import router as health_router

app.include_router(auth_router, prefix=f"{API_V1_PREFIX}/auth", tags=["Auth"])
app.include_router(chatbot_router, prefix=f"{API_V1_PREFIX}/chatbots", tags=["Chatbots"])
app.include_router(document_router, prefix=f"{API_V1_PREFIX}/chatbots", tags=["Documents"])
app.include_router(chat_router, prefix=f"{API_V1_PREFIX}/chat", tags=["Chat"])
app.include_router(stats_router, prefix=f"{API_V1_PREFIX}/chatbots", tags=["Stats"])
app.include_router(version_router, prefix=f"{API_V1_PREFIX}/chatbots", tags=["Versions"])
app.include_router(health_router, prefix=f"{API_V1_PREFIX}", tags=["Health"])


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "health": f"{API_V1_PREFIX}/health",
        "api": API_V1_PREFIX,
    }


# Simple health check (backwards compatibility)
@app.get("/health", tags=["Health"])
async def simple_health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
