"""
Document embedding and Qdrant storage service.
"""
import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from src.core.config import settings
from src.core.embeddings import get_embedding_model, VECTOR_DIMENSION


class DocumentEmbedder:
    """Service for embedding documents and storing in Qdrant."""

    def __init__(self, qdrant_client: Optional[QdrantClient] = None):
        """
        Initialize document embedder.

        Args:
            qdrant_client: Optional Qdrant client (creates one if not provided)
        """
        if qdrant_client:
            self._client = qdrant_client
        else:
            self._client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
            )

        self._embedding_model = get_embedding_model()
        self._ensure_collection()

    @property
    def collection_name(self) -> str:
        """Get collection name from settings."""
        return settings.qdrant_collection_name

    def _ensure_collection(self) -> None:
        """Ensure the collection exists in Qdrant."""
        collections = self._client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=VECTOR_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )

    def embed_and_store(
        self,
        chunks: list[dict],
        chatbot_id: str,
        batch_size: int = 32,
    ) -> list[str]:
        """
        Embed chunks and store in Qdrant.

        Args:
            chunks: List of chunk dicts with text and metadata
            chatbot_id: Chatbot ID for filtering
            batch_size: Batch size for embedding

        Returns:
            List of point IDs
        """
        if not chunks:
            return []

        point_ids = []

        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c["text"] for c in batch]

            # Generate embeddings (sync for Celery)
            embeddings = self._embedding_model.embed_texts_sync(texts)

            # Create points
            points = []
            for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                point_id = str(uuid.uuid4())
                point_ids.append(point_id)

                metadata = chunk.get("metadata", {})
                metadata["chatbot_id"] = chatbot_id
                metadata["text"] = chunk["text"][:1000]  # Store truncated text for retrieval

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=metadata,
                    )
                )

            # Upsert to Qdrant
            self._client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

        return point_ids

    def search(
        self,
        query: str,
        chatbot_id: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> list[dict]:
        """
        Search for similar chunks.

        Args:
            query: Search query
            chatbot_id: Chatbot ID to filter by
            top_k: Number of results
            score_threshold: Minimum similarity score

        Returns:
            List of matching chunks with scores
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
                "metadata": {
                    k: v
                    for k, v in result.payload.items()
                    if k not in ["text", "chatbot_id"]
                },
            }
            for result in results
        ]

    def delete_by_document(self, document_id: str) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of deleted points
        """
        # Get points to delete
        scroll_result = self._client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
            limit=10000,
        )

        points, _ = scroll_result
        point_ids = [str(p.id) for p in points]

        if point_ids:
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids,
            )

        return len(point_ids)

    def delete_by_chatbot(self, chatbot_id: str) -> int:
        """
        Delete all chunks for a chatbot.

        Args:
            chatbot_id: Chatbot ID

        Returns:
            Number of deleted points
        """
        # Get all points for chatbot
        scroll_result = self._client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="chatbot_id",
                        match=MatchValue(value=chatbot_id),
                    )
                ]
            ),
            limit=100000,
        )

        points, _ = scroll_result
        point_ids = [str(p.id) for p in points]

        if point_ids:
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids,
            )

        return len(point_ids)

    def get_chunk_count(self, chatbot_id: str) -> int:
        """
        Get chunk count for a chatbot.

        Args:
            chatbot_id: Chatbot ID

        Returns:
            Number of chunks
        """
        result = self._client.count(
            collection_name=self.collection_name,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="chatbot_id",
                        match=MatchValue(value=chatbot_id),
                    )
                ]
            ),
        )
        return result.count


# Singleton instance
_embedder_instance: Optional[DocumentEmbedder] = None


def get_document_embedder() -> DocumentEmbedder:
    """Get or create singleton embedder instance."""
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = DocumentEmbedder()
    return _embedder_instance
