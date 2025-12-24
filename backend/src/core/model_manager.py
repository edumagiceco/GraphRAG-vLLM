"""
Model Manager - Central management for LLM and embedding model settings.
Provides dynamic model configuration with database persistence.
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import async_session_maker
from src.models.system_settings import SystemSettings, SettingKeys

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about an Ollama model."""
    name: str
    size: int  # bytes
    modified_at: str
    digest: str
    family: Optional[str] = None
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None

    @property
    def size_gb(self) -> float:
        """Get size in GB."""
        return self.size / (1024 ** 3)

    @property
    def size_formatted(self) -> str:
        """Get human-readable size."""
        if self.size >= 1024 ** 3:
            return f"{self.size_gb:.1f} GB"
        elif self.size >= 1024 ** 2:
            return f"{self.size / (1024 ** 2):.1f} MB"
        else:
            return f"{self.size / 1024:.1f} KB"


@dataclass
class ModelDetail:
    """Detailed model information from Ollama."""
    name: str
    family: Optional[str] = None
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None
    embedding_length: Optional[int] = None  # For embedding models


class ModelManager:
    """
    Manages LLM and embedding model settings.
    Settings are stored in the database with fallback to environment variables.
    """

    # Cache for model dimension (to avoid repeated API calls)
    _embedding_dimension_cache: dict[str, int] = {}

    # In-memory cache for settings (populated by async methods, used by sync methods)
    _settings_cache: dict[str, str] = {}

    # Flag to track if settings have been initialized
    _initialized: bool = False

    # =========================================================================
    # Initialization
    # =========================================================================

    @classmethod
    async def initialize(cls) -> None:
        """
        Initialize settings cache from database.
        Should be called at application startup.
        """
        if cls._initialized:
            return

        logger.info("Initializing ModelManager settings from database...")

        try:
            # Load all settings from DB
            all_settings = await cls.get_all_settings()

            # Populate cache
            for key, value in all_settings.items():
                cls._settings_cache[key] = value
                logger.debug(f"Loaded setting: {key}={value[:50] if len(value) > 50 else value}")

            # Also populate dimension cache if available
            if SettingKeys.EMBEDDING_MODEL in cls._settings_cache:
                model = cls._settings_cache[SettingKeys.EMBEDDING_MODEL]
                if SettingKeys.EMBEDDING_DIMENSION in cls._settings_cache:
                    try:
                        dim = int(cls._settings_cache[SettingKeys.EMBEDDING_DIMENSION])
                        cls._embedding_dimension_cache[model] = dim
                    except ValueError:
                        pass

            cls._initialized = True
            logger.info(f"ModelManager initialized with {len(cls._settings_cache)} settings from database")

        except Exception as e:
            logger.warning(f"Failed to initialize settings from database: {e}. Using defaults.")
            cls._initialized = True  # Mark as initialized to avoid repeated attempts

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if settings have been initialized."""
        return cls._initialized

    # =========================================================================
    # System Settings CRUD
    # =========================================================================

    @classmethod
    async def get_setting(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value from database."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(SystemSettings).where(SystemSettings.key == key)
            )
            setting = result.scalar_one_or_none()
            return setting.value if setting else default

    @classmethod
    async def set_setting(
        cls,
        key: str,
        value: str,
        description: Optional[str] = None
    ) -> None:
        """Set a setting value in database."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(SystemSettings).where(SystemSettings.key == key)
            )
            setting = result.scalar_one_or_none()

            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
                if description:
                    setting.description = description
            else:
                setting = SystemSettings(
                    key=key,
                    value=value,
                    description=description,
                )
                session.add(setting)

            await session.commit()

    @classmethod
    async def get_all_settings(cls) -> dict[str, str]:
        """Get all settings as a dictionary."""
        async with async_session_maker() as session:
            result = await session.execute(select(SystemSettings))
            settings_list = result.scalars().all()
            return {s.key: s.value for s in settings_list}

    # =========================================================================
    # LLM Model Settings
    # =========================================================================

    @classmethod
    async def get_default_llm_model(cls) -> str:
        """Get the default LLM model name."""
        model = await cls.get_setting(SettingKeys.DEFAULT_LLM_MODEL)
        result = model or settings.ollama_model
        # Update cache for sync methods
        cls._settings_cache[SettingKeys.DEFAULT_LLM_MODEL] = result
        return result

    @classmethod
    async def set_default_llm_model(cls, model: str) -> None:
        """Set the default LLM model name."""
        await cls.set_setting(
            SettingKeys.DEFAULT_LLM_MODEL,
            model,
            "Default LLM model for chat completion"
        )
        logger.info(f"Default LLM model set to: {model}")

    @classmethod
    async def get_chatbot_llm_model(
        cls,
        session: AsyncSession,
        chatbot_id: str
    ) -> str:
        """
        Get the LLM model for a specific chatbot.
        Returns chatbot-specific model if set, otherwise returns default.
        """
        from src.models.chatbot_service import ChatbotService

        result = await session.execute(
            select(ChatbotService.llm_model).where(ChatbotService.id == chatbot_id)
        )
        llm_model = result.scalar_one_or_none()

        if llm_model:
            return llm_model

        return await cls.get_default_llm_model()

    # =========================================================================
    # Embedding Model Settings
    # =========================================================================

    @classmethod
    async def get_embedding_model(cls) -> str:
        """Get the embedding model name."""
        model = await cls.get_setting(SettingKeys.EMBEDDING_MODEL)
        result = model or settings.ollama_embedding_model
        # Update cache for sync methods
        cls._settings_cache[SettingKeys.EMBEDDING_MODEL] = result
        return result

    @classmethod
    async def set_embedding_model(cls, model: str) -> None:
        """Set the embedding model name."""
        # Clear dimension cache when model changes
        cls._embedding_dimension_cache.clear()

        await cls.set_setting(
            SettingKeys.EMBEDDING_MODEL,
            model,
            "Embedding model for vector generation"
        )

        # Try to get and cache the new dimension
        dimension = await cls.get_embedding_dimension_from_ollama(model)
        if dimension:
            await cls.set_setting(
                SettingKeys.EMBEDDING_DIMENSION,
                str(dimension),
                "Embedding vector dimension"
            )

        logger.info(f"Embedding model set to: {model}")

    @classmethod
    async def get_embedding_dimension(cls) -> int:
        """Get the embedding dimension for the current model."""
        # First try cached value
        current_model = await cls.get_embedding_model()
        if current_model in cls._embedding_dimension_cache:
            return cls._embedding_dimension_cache[current_model]

        # Try from database
        dim_str = await cls.get_setting(SettingKeys.EMBEDDING_DIMENSION)
        if dim_str:
            try:
                dim = int(dim_str)
                cls._embedding_dimension_cache[current_model] = dim
                # Update settings cache for sync methods
                cls._settings_cache[SettingKeys.EMBEDDING_DIMENSION] = dim_str
                return dim
            except ValueError:
                pass

        # Try from Ollama API
        dim = await cls.get_embedding_dimension_from_ollama(current_model)
        if dim:
            cls._embedding_dimension_cache[current_model] = dim
            # Update settings cache for sync methods
            cls._settings_cache[SettingKeys.EMBEDDING_DIMENSION] = str(dim)
            return dim

        # Default fallback (bge-m3)
        logger.warning(f"Could not determine dimension for {current_model}, using default 1024")
        return 1024

    @classmethod
    async def get_embedding_dimension_from_ollama(cls, model: str) -> Optional[int]:
        """Query Ollama API for model embedding dimension."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/show",
                    json={"name": model},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    model_info = data.get("model_info", {})
                    # Try different keys for embedding length
                    for key in ["embedding_length", "embedding.dimension", "context_length"]:
                        if "." in key:
                            parts = key.split(".")
                            value = model_info
                            for part in parts:
                                value = value.get(part, {})
                            if isinstance(value, int):
                                return value
                        elif key in model_info:
                            return model_info[key]

                    # Check modelfile parameters
                    details = data.get("details", {})
                    if "embedding_length" in details:
                        return details["embedding_length"]

        except Exception as e:
            logger.warning(f"Failed to get embedding dimension from Ollama: {e}")

        return None

    # =========================================================================
    # Ollama Connection
    # =========================================================================

    @classmethod
    async def get_ollama_base_url(cls) -> str:
        """Get the Ollama base URL."""
        url = await cls.get_setting(SettingKeys.OLLAMA_BASE_URL)
        result = url or settings.ollama_base_url
        # Update cache for sync methods
        cls._settings_cache[SettingKeys.OLLAMA_BASE_URL] = result
        return result

    @classmethod
    async def set_ollama_base_url(cls, url: str) -> None:
        """Set the Ollama base URL."""
        # Normalize URL (remove trailing slash)
        url = url.rstrip("/")
        await cls.set_setting(
            SettingKeys.OLLAMA_BASE_URL,
            url,
            "Ollama server base URL"
        )
        # Reset instances to use new URL
        cls.reset_all_instances()
        logger.info(f"Ollama base URL set to: {url}")

    @classmethod
    async def test_connection(cls) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Test connection to Ollama server.
        Returns: (connected, version, error)
        """
        try:
            base_url = await cls.get_ollama_base_url()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{base_url}/api/version",
                    timeout=5.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    version = data.get("version", "unknown")
                    return True, version, None

                return False, None, f"HTTP {response.status_code}"

        except httpx.ConnectError as e:
            return False, None, f"Connection failed: {str(e)}"
        except Exception as e:
            return False, None, str(e)

    @classmethod
    async def list_available_models(cls) -> list[ModelInfo]:
        """List all available models from Ollama."""
        try:
            base_url = await cls.get_ollama_base_url()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{base_url}/api/tags",
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for m in data.get("models", []):
                        details = m.get("details", {})
                        models.append(ModelInfo(
                            name=m.get("name", ""),
                            size=m.get("size", 0),
                            modified_at=m.get("modified_at", ""),
                            digest=m.get("digest", ""),
                            family=details.get("family"),
                            parameter_size=details.get("parameter_size"),
                            quantization_level=details.get("quantization_level"),
                        ))
                    return models

        except Exception as e:
            logger.error(f"Failed to list models: {e}")

        return []

    @classmethod
    async def get_model_info(cls, model_name: str) -> Optional[ModelDetail]:
        """Get detailed information about a specific model."""
        try:
            base_url = await cls.get_ollama_base_url()
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/api/show",
                    json={"name": model_name},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    details = data.get("details", {})
                    model_info = data.get("model_info", {})

                    return ModelDetail(
                        name=model_name,
                        family=details.get("family"),
                        parameter_size=details.get("parameter_size"),
                        quantization_level=details.get("quantization_level"),
                        embedding_length=model_info.get("embedding_length"),
                    )

        except Exception as e:
            logger.error(f"Failed to get model info for {model_name}: {e}")

        return None

    @classmethod
    def classify_models(cls, models: list[ModelInfo]) -> tuple[list[ModelInfo], list[ModelInfo]]:
        """
        Classify models into chat models and embedding models.
        Returns: (chat_models, embedding_models)
        """
        chat_models = []
        embedding_models = []

        # Known embedding model patterns
        embedding_patterns = [
            "embed", "bge", "e5", "gte", "nomic-embed", "mxbai-embed",
            "all-minilm", "sentence-", "paraphrase-"
        ]

        for model in models:
            name_lower = model.name.lower()
            is_embedding = any(pattern in name_lower for pattern in embedding_patterns)

            if is_embedding:
                embedding_models.append(model)
            else:
                chat_models.append(model)

        return chat_models, embedding_models

    # =========================================================================
    # Singleton Instance Management
    # =========================================================================

    @classmethod
    def reset_llm_instance(cls) -> None:
        """Reset the global LLM instance to force re-creation with new settings."""
        from src.core import llm
        llm._llm_instance = None
        llm._current_model = None
        logger.info("LLM instance reset")

    @classmethod
    def reset_embedding_instance(cls) -> None:
        """Reset the global embedding model instance."""
        from src.core import embeddings
        embeddings._embedding_instance = None
        cls._embedding_dimension_cache.clear()
        logger.info("Embedding instance reset")

    @classmethod
    def reset_all_instances(cls) -> None:
        """Reset all model instances."""
        cls.reset_llm_instance()
        cls.reset_embedding_instance()
        logger.info("All model instances reset")

    # =========================================================================
    # Synchronous helpers (for Celery workers and sync contexts)
    # =========================================================================

    @classmethod
    def get_default_llm_model_sync(cls) -> str:
        """
        Synchronous version - uses cache or falls back to settings.
        Safe to call from any context (sync/async).
        """
        # First try cache (populated by async methods)
        if SettingKeys.DEFAULT_LLM_MODEL in cls._settings_cache:
            return cls._settings_cache[SettingKeys.DEFAULT_LLM_MODEL]
        # Fallback to settings
        return settings.ollama_model

    @classmethod
    def get_embedding_model_sync(cls) -> str:
        """
        Synchronous version - uses cache or falls back to settings.
        Safe to call from any context (sync/async).
        """
        # First try cache (populated by async methods)
        if SettingKeys.EMBEDDING_MODEL in cls._settings_cache:
            return cls._settings_cache[SettingKeys.EMBEDDING_MODEL]
        # Fallback to settings
        return settings.ollama_embedding_model

    @classmethod
    def get_embedding_dimension_sync(cls) -> int:
        """
        Synchronous version - uses dimension cache or settings.
        Safe to call from any context (sync/async).
        """
        # First try dimension cache
        current_model = cls.get_embedding_model_sync()
        if current_model in cls._embedding_dimension_cache:
            return cls._embedding_dimension_cache[current_model]

        # Try from settings cache
        if SettingKeys.EMBEDDING_DIMENSION in cls._settings_cache:
            try:
                return int(cls._settings_cache[SettingKeys.EMBEDDING_DIMENSION])
            except ValueError:
                pass

        # Default fallback
        return 1024

    @classmethod
    def get_ollama_base_url_sync(cls) -> str:
        """
        Synchronous version - uses cache or falls back to settings.
        Safe to call from any context (sync/async).
        """
        # First try cache (populated by async methods)
        if SettingKeys.OLLAMA_BASE_URL in cls._settings_cache:
            return cls._settings_cache[SettingKeys.OLLAMA_BASE_URL]
        # Fallback to settings
        return settings.ollama_base_url
