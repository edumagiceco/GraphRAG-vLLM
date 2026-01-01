"""
Vector search service using Qdrant.
"""
import asyncio
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from src.core.config import settings
from src.core.embeddings import get_embedding_model


class VectorSearch:
    """Service for vector similarity search in Qdrant."""

    def __init__(self, qdrant_client: Optional[QdrantClient] = None):
        """
        Initialize vector search.

        Args:
            qdrant_client: Optional Qdrant client
        """
        if qdrant_client:
            self._client = qdrant_client
        else:
            self._client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
            )

        self._embedding_model = get_embedding_model()

    @property
    def collection_name(self) -> str:
        """Get collection name from settings."""
        return settings.qdrant_collection_name

    async def search(
        self,
        query: str,
        chatbot_id: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> list[dict]:
        """
        Search for similar chunks using vector similarity.

        Args:
            query: Search query text
            chatbot_id: Chatbot ID to filter by
            top_k: Number of top results to return
            score_threshold: Minimum similarity score

        Returns:
            List of matching chunks with scores
        """
        # Generate query embedding
        query_embedding = await self._embedding_model.embed_query(query)

        # Run synchronous Qdrant search in thread pool to avoid blocking event loop
        results = await asyncio.to_thread(
            self._client.search,
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="chatbot_id",
                        match=MatchValue(value=chatbot_id),
                    )
                ]
            ),
            limit=top_k,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": str(result.id),
                "text": result.payload.get("text", ""),
                "score": result.score,
                "document_id": result.payload.get("document_id"),
                "filename": result.payload.get("filename"),
                "page_num": result.payload.get("page_num"),
                "chunk_index": result.payload.get("chunk_index"),
            }
            for result in results
        ]

    def search_sync(
        self,
        query: str,
        chatbot_id: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> list[dict]:
        """
        Synchronous search for similar chunks.

        Args:
            query: Search query text
            chatbot_id: Chatbot ID to filter by
            top_k: Number of top results
            score_threshold: Minimum similarity score

        Returns:
            List of matching chunks
        """
        # Generate query embedding (sync)
        query_embedding = self._embedding_model.embed_text_sync(query)

        # Search
        results = self._client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="chatbot_id",
                        match=MatchValue(value=chatbot_id),
                    )
                ]
            ),
            limit=top_k,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": str(result.id),
                "text": result.payload.get("text", ""),
                "score": result.score,
                "document_id": result.payload.get("document_id"),
                "filename": result.payload.get("filename"),
                "page_num": result.payload.get("page_num"),
                "chunk_index": result.payload.get("chunk_index"),
            }
            for result in results
        ]


# Singleton instance
_search_instance: Optional[VectorSearch] = None


def get_vector_search() -> VectorSearch:
    """Get or create singleton vector search instance."""
    global _search_instance
    if _search_instance is None:
        _search_instance = VectorSearch()
    return _search_instance
