"""
Embedding model wrapper supporting Ollama and vLLM backends.
Provides unified interface for generating text embeddings.
"""
import logging
from typing import Optional

from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Wrapper for embedding models.
    Supports both Ollama and vLLM (OpenAI-compatible) backends.
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
        backend: Optional[str] = None,
    ):
        """
        Initialize the embedding model wrapper.

        Args:
            model: Embedding model name (default: from settings/database)
            base_url: Server URL (default: from settings)
            dimension: Explicit dimension override (default: auto-detect)
            backend: 'ollama' or 'vllm' (default: from settings)
        """
        # Determine backend
        self.backend = backend or settings.llm_backend

        # Get model and base_url based on backend
        if self.backend == "vllm":
            self.model = model or settings.vllm_embedding_model
            self.base_url = base_url or settings.vllm_embedding_base_url

            # Use OpenAI-compatible embeddings for vLLM
            self._embeddings = OpenAIEmbeddings(
                model=self.model,
                openai_api_base=self.base_url,
                openai_api_key="not-needed",  # vLLM doesn't require API key
            )
            logger.debug(f"Initialized vLLM embedding model: {self.model} at {self.base_url}")
        else:
            # Ollama backend
            if model:
                self.model = model
            else:
                try:
                    from src.core.model_manager import ModelManager
                    self.model = ModelManager.get_embedding_model_sync()
                except Exception as e:
                    logger.warning(f"Failed to get embedding model from DB: {e}")
                    self.model = settings.ollama_embedding_model

            if base_url:
                self.base_url = base_url
            else:
                try:
                    from src.core.model_manager import ModelManager
                    self.base_url = ModelManager.get_ollama_base_url_sync()
                except Exception as e:
                    logger.warning(f"Failed to get Ollama URL from DB: {e}")
                    self.base_url = settings.ollama_base_url

            self._embeddings = OllamaEmbeddings(
                model=self.model,
                base_url=self.base_url,
            )
            logger.debug(f"Initialized Ollama embedding model: {self.model} at {self.base_url}")

        self._explicit_dimension = dimension

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


# Alias for backwards compatibility
OllamaEmbeddingModel = EmbeddingModel

# Singleton instance for convenience
_embedding_instance: Optional[EmbeddingModel] = None
_current_embedding_model: Optional[str] = None
_current_backend: Optional[str] = None


def get_embedding_model(model: Optional[str] = None) -> EmbeddingModel:
    """
    Get or create the embedding model instance.

    Args:
        model: Optional model override. If None, uses default from settings.

    Returns:
        EmbeddingModel instance
    """
    global _embedding_instance, _current_embedding_model, _current_backend

    backend = settings.llm_backend

    # Determine target model based on backend
    if model:
        target_model = model
    elif backend == "vllm":
        target_model = settings.vllm_embedding_model
    else:
        try:
            from src.core.model_manager import ModelManager
            target_model = ModelManager.get_embedding_model_sync()
        except Exception as e:
            logger.warning(f"Failed to get embedding model from DB: {e}")
            target_model = settings.ollama_embedding_model

    # Check if we need to create new instance
    if (_embedding_instance is None or
        _current_embedding_model != target_model or
        _current_backend != backend):
        _current_embedding_model = target_model
        _current_backend = backend
        _embedding_instance = EmbeddingModel(model=target_model, backend=backend)
        logger.info(f"Created new embedding model instance: {target_model} (backend: {backend})")

    return _embedding_instance


def reset_embedding_model() -> None:
    """Reset the embedding model singleton instance. Called when model settings change."""
    global _embedding_instance, _current_embedding_model, _current_backend
    _embedding_instance = None
    _current_embedding_model = None
    _current_backend = None
    EmbeddingModel._dimension_cache.clear()
    logger.info("Embedding model instance reset")


async def check_embedding_model() -> bool:
    """
    Check if embedding model is available.

    Returns:
        True if model is available
    """
    import httpx

    try:
        if settings.llm_backend == "vllm":
            # Check vLLM embedding server
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.vllm_embedding_base_url}/models",
                    timeout=5.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    models = [m["id"] for m in data.get("data", [])]
                    return settings.vllm_embedding_model in models
        else:
            # Check Ollama server
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
        return EmbeddingModel.DEFAULT_EMBEDDING_DIM


# Legacy constant for backwards compatibility (use get_vector_dimension() instead)
VECTOR_DIMENSION = EmbeddingModel.DEFAULT_EMBEDDING_DIM
