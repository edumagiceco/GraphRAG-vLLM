"""
Application configuration using Pydantic Settings.
Loads configuration from environment variables.
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Application
    # ==========================================================================
    app_name: str = "GraphRAG Chatbot Platform"
    debug: bool = False

    # ==========================================================================
    # PostgreSQL Database
    # ==========================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://graphrag:password@localhost:5432/graphrag",
        description="PostgreSQL connection URL",
    )

    # ==========================================================================
    # Neo4j Graph Database
    # ==========================================================================
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="password")

    # ==========================================================================
    # Qdrant Vector Database
    # ==========================================================================
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_collection_name: str = Field(default="graphrag_chunks")

    # ==========================================================================
    # Redis
    # ==========================================================================
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ==========================================================================
    # Celery
    # ==========================================================================
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")

    # ==========================================================================
    # LLM Backend Selection
    # ==========================================================================
    llm_backend: str = Field(
        default="ollama",
        description="LLM backend: 'ollama' or 'vllm'",
    )

    # ==========================================================================
    # Ollama LLM (Local)
    # ==========================================================================
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen3:32b")
    ollama_embedding_model: str = Field(default="bge-m3:latest")

    # ==========================================================================
    # vLLM Server (LLM + Embeddings)
    # ==========================================================================
    vllm_base_url: str = Field(
        default="http://localhost:8000/v1",
        description="vLLM OpenAI-compatible API endpoint",
    )
    vllm_model: str = Field(
        default="spow12/Ko-Qwen2-7B-Instruct",
        description="HuggingFace model name for vLLM",
    )
    vllm_embedding_base_url: str = Field(
        default="http://localhost:8002/v1",
        description="vLLM embedding server endpoint",
    )
    vllm_embedding_model: str = Field(
        default="upskyy/bge-m3-korean",
        description="HuggingFace embedding model name",
    )

    # ==========================================================================
    # JWT Authentication
    # ==========================================================================
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        min_length=32,
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60)

    # ==========================================================================
    # Initial Admin Account
    # ==========================================================================
    admin_email: str = Field(default="admin@example.com")
    admin_password: str = Field(default="admin123")

    # ==========================================================================
    # File Storage
    # ==========================================================================
    storage_path: str = Field(default="/app/storage")
    max_file_size_mb: int = Field(default=100)

    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting middleware",
    )
    rate_limit_per_minute: int = Field(
        default=60,
        description="Maximum requests per minute per client",
    )
    rate_limit_per_hour: int = Field(
        default=1000,
        description="Maximum requests per hour per client",
    )

    # ==========================================================================
    # Document Processing
    # ==========================================================================
    chunk_size: int = Field(default=500)
    chunk_overlap: int = Field(default=100)
    max_concurrent_llm_requests: int = Field(default=4)

    # ==========================================================================
    # Validators
    # ==========================================================================
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
