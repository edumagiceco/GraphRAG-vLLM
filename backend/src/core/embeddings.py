"""
Embedding model wrapper using Ollama embeddings.
Provides unified interface for generating text embeddings.
"""
from typing import Optional

from langchain_ollama import OllamaEmbeddings

from src.core.config import settings


class OllamaEmbeddingModel:
    """
    Wrapper for Ollama embedding model.
    Uses nomic-embed-text for generating text embeddings.
    """

    # Embedding dimension for nomic-embed-text
    EMBEDDING_DIM = 768

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the embedding model wrapper.

        Args:
            model: Embedding model name (default: from settings)
            base_url: Ollama server URL (default: from settings)
        """
        self.model = model or settings.ollama_embedding_model
        self.base_url = base_url or settings.ollama_base_url

        # langchain-ollama 0.2.0+ supports base_url parameter
        self._embeddings = OllamaEmbeddings(
            model=self.model,
            base_url=self.base_url,
        )

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.EMBEDDING_DIM

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


def get_embedding_model() -> OllamaEmbeddingModel:
    """Get or create the singleton embedding model instance."""
    global _embedding_instance
    if _embedding_instance is None:
        _embedding_instance = OllamaEmbeddingModel()
    return _embedding_instance


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


# Vector dimension constant for Qdrant collection creation
VECTOR_DIMENSION = OllamaEmbeddingModel.EMBEDDING_DIM
