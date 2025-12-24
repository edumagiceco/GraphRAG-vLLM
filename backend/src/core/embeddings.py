"""
Embedding model wrapper using Ollama embeddings.
Provides unified interface for generating text embeddings.
"""
import logging
from typing import Optional

from langchain_ollama import OllamaEmbeddings

from src.core.config import settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingModel:
    """
    Wrapper for Ollama embedding model.
    Supports dynamic model selection and dimension detection.
    """

    # Default embedding dimension (bge-m3)
    DEFAULT_EMBEDDING_DIM = 1024

    # Cache for model dimensions
    _dimension_cache: dict[str, int] = {}

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        dimension: Optional[int] = None,
    ):
        """
        Initialize the embedding model wrapper.

        Args:
            model: Embedding model name (default: from settings/database)
            base_url: Ollama server URL (default: from settings)
            dimension: Explicit dimension override (default: auto-detect)
        """
        # Get model from parameter, or try ModelManager, fallback to settings
        if model:
            self.model = model
        else:
            try:
                from src.core.model_manager import ModelManager
                self.model = ModelManager.get_embedding_model_sync()
            except Exception as e:
                logger.warning(f"Failed to get embedding model from DB: {e}")
                self.model = settings.ollama_embedding_model

        # Get base_url from parameter, or try ModelManager, fallback to settings
        if base_url:
            self.base_url = base_url
        else:
            try:
                from src.core.model_manager import ModelManager
                self.base_url = ModelManager.get_ollama_base_url_sync()
            except Exception as e:
                logger.warning(f"Failed to get Ollama URL from DB: {e}")
                self.base_url = settings.ollama_base_url
        self._explicit_dimension = dimension

        # langchain-ollama 0.2.0+ supports base_url parameter
        self._embeddings = OllamaEmbeddings(
            model=self.model,
            base_url=self.base_url,
        )

        logger.debug(f"Initialized embedding model: {self.model}")

    @property
    def dimension(self) -> int:
        """Get embedding dimension for current model."""
        if self._explicit_dimension:
            return self._explicit_dimension

        # Check cache
        if self.model in self._dimension_cache:
            return self._dimension_cache[self.model]

        # Try to get from ModelManager
        try:
            from src.core.model_manager import ModelManager
            dim = ModelManager.get_embedding_dimension_sync()
            self._dimension_cache[self.model] = dim
            return dim
        except Exception as e:
            logger.warning(f"Failed to get embedding dimension: {e}")

        return self.DEFAULT_EMBEDDING_DIM

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        # Use async method if available, otherwise use sync
        embeddings = await self._embeddings.aembed_documents([text])
        return embeddings[0]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return await self._embeddings.aembed_documents(texts)

    async def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.
        May use different embedding strategy than documents.

        Args:
            query: Query text to embed

        Returns:
            Query embedding vector
        """
        return await self._embeddings.aembed_query(query)

    def embed_text_sync(self, text: str) -> list[float]:
        """
        Generate embedding synchronously (for Celery tasks).

        Args:
            text: Input text to embed

        Returns:
            Embedding vector
        """
        embeddings = self._embeddings.embed_documents([text])
        return embeddings[0]

    def embed_texts_sync(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings synchronously (for Celery tasks).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return self._embeddings.embed_documents(texts)


# Singleton instance for convenience
_embedding_instance: Optional[OllamaEmbeddingModel] = None
_current_embedding_model: Optional[str] = None


def get_embedding_model(model: Optional[str] = None) -> OllamaEmbeddingModel:
    """
    Get or create the embedding model instance.

    Args:
        model: Optional model override. If None, uses default from settings/database.

    Returns:
        OllamaEmbeddingModel instance
    """
    global _embedding_instance, _current_embedding_model

    # Determine target model
    if model:
        target_model = model
    else:
        try:
            from src.core.model_manager import ModelManager
            target_model = ModelManager.get_embedding_model_sync()
        except Exception as e:
            logger.warning(f"Failed to get embedding model from DB: {e}")
            target_model = settings.ollama_embedding_model

    # Check if we need to create new instance
    if _embedding_instance is None or _current_embedding_model != target_model:
        _current_embedding_model = target_model
        _embedding_instance = OllamaEmbeddingModel(model=target_model)
        logger.debug(f"Created new embedding model instance: {target_model}")

    return _embedding_instance


def reset_embedding_model() -> None:
    """Reset the embedding model singleton instance. Called when model settings change."""
    global _embedding_instance, _current_embedding_model
    _embedding_instance = None
    _current_embedding_model = None
    OllamaEmbeddingModel._dimension_cache.clear()
    logger.info("Embedding model instance reset")


async def check_embedding_model() -> bool:
    """
    Check if embedding model is available.

    Returns:
        True if model is available
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.ollama_base_url}/api/tags",
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return settings.ollama_embedding_model in models or any(
                    settings.ollama_embedding_model.split(":")[0] in m for m in models
                )
    except Exception:
        pass

    return False


# Vector dimension - now a function to support dynamic model settings
def get_vector_dimension() -> int:
    """
    Get the vector dimension for the current embedding model.
    Used for Qdrant collection creation.
    """
    try:
        from src.core.model_manager import ModelManager
        return ModelManager.get_embedding_dimension_sync()
    except Exception:
        return OllamaEmbeddingModel.DEFAULT_EMBEDDING_DIM


# Legacy constant for backwards compatibility (use get_vector_dimension() instead)
VECTOR_DIMENSION = OllamaEmbeddingModel.DEFAULT_EMBEDDING_DIM
