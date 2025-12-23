"""
Qdrant vector database client.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from src.core.config import settings


class QdrantManager:
    """Qdrant client manager for vector operations."""

    _client: Optional[QdrantClient] = None

    @classmethod
    def get_client(cls) -> QdrantClient:
        """Get or create Qdrant client instance."""
        if cls._client is None:
            cls._client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
            )
        return cls._client

    @classmethod
    def close(cls) -> None:
        """Close Qdrant client connection."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None

    @classmethod
    def get_collection_name(cls, chatbot_id: str, version: int) -> str:
        """
        Generate collection name for chatbot version.

        Args:
            chatbot_id: Chatbot service ID
            version: Index version number

        Returns:
            Collection name string
        """
        return f"chatbot_{chatbot_id}_v{version}"

    # =========================================================================
    # Collection Operations
    # =========================================================================

    @classmethod
    def create_collection(
        cls,
        chatbot_id: str,
        version: int,
        vector_size: int = 768,  # nomic-embed-text dimension
    ) -> None:
        """
        Create a new collection for a chatbot version.

        Args:
            chatbot_id: Chatbot service ID
            version: Index version number
            vector_size: Embedding dimension size
        """
        client = cls.get_client()
        collection_name = cls.get_collection_name(chatbot_id, version)

        # Check if collection exists
        collections = client.get_collections().collections
        if any(c.name == collection_name for c in collections):
            return

        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

        # Create payload indexes for filtering
        client.create_payload_index(
            collection_name=collection_name,
            field_name="document_id",
            field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="page_number",
            field_schema=qdrant_models.PayloadSchemaType.INTEGER,
        )

    @classmethod
    def delete_collection(cls, chatbot_id: str, version: int) -> bool:
        """
        Delete a collection for a chatbot version.

        Args:
            chatbot_id: Chatbot service ID
            version: Index version number

        Returns:
            True if deleted, False if not found
        """
        client = cls.get_client()
        collection_name = cls.get_collection_name(chatbot_id, version)

        try:
            client.delete_collection(collection_name)
            return True
        except Exception:
            return False

    @classmethod
    def collection_exists(cls, chatbot_id: str, version: int) -> bool:
        """Check if a collection exists."""
        client = cls.get_client()
        collection_name = cls.get_collection_name(chatbot_id, version)

        collections = client.get_collections().collections
        return any(c.name == collection_name for c in collections)

    # =========================================================================
    # Vector Operations
    # =========================================================================

    @classmethod
    def upsert_vectors(
        cls,
        chatbot_id: str,
        version: int,
        points: List[Dict[str, Any]],
    ) -> None:
        """
        Upsert vectors into a collection.

        Args:
            chatbot_id: Chatbot service ID
            version: Index version number
            points: List of points with id, vector, and payload
        """
        client = cls.get_client()
        collection_name = cls.get_collection_name(chatbot_id, version)

        # Ensure collection exists
        cls.create_collection(chatbot_id, version)

        # Convert to Qdrant points
        qdrant_points = [
            PointStruct(
                id=point["id"],
                vector=point["vector"],
                payload=point.get("payload", {}),
            )
            for point in points
        ]

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i : i + batch_size]
            client.upsert(
                collection_name=collection_name,
                points=batch,
            )

    @classmethod
    def search(
        cls,
        chatbot_id: str,
        version: int,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            chatbot_id: Chatbot service ID
            version: Index version number
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Optional payload filters

        Returns:
            List of search results with id, score, and payload
        """
        client = cls.get_client()
        collection_name = cls.get_collection_name(chatbot_id, version)

        # Build filter if provided
        query_filter = None
        if filter_conditions:
            must_conditions = []
            for key, value in filter_conditions.items():
                must_conditions.append(
                    qdrant_models.FieldCondition(
                        key=key,
                        match=qdrant_models.MatchValue(value=value),
                    )
                )
            query_filter = qdrant_models.Filter(must=must_conditions)

        # Execute search
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
            with_payload=True,
        )

        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results
        ]

    @classmethod
    def delete_by_document(
        cls,
        chatbot_id: str,
        version: int,
        document_id: str,
    ) -> int:
        """
        Delete all vectors for a specific document.

        Args:
            chatbot_id: Chatbot service ID
            version: Index version number
            document_id: Document ID to delete

        Returns:
            Number of deleted vectors
        """
        client = cls.get_client()
        collection_name = cls.get_collection_name(chatbot_id, version)

        # Delete by filter
        client.delete(
            collection_name=collection_name,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="document_id",
                            match=qdrant_models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )

        return 0  # Qdrant doesn't return count

    @classmethod
    def get_collection_info(
        cls,
        chatbot_id: str,
        version: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get collection information.

        Args:
            chatbot_id: Chatbot service ID
            version: Index version number

        Returns:
            Collection info dict or None if not found
        """
        client = cls.get_client()
        collection_name = cls.get_collection_name(chatbot_id, version)

        try:
            info = client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.value,
            }
        except Exception:
            return None


# Convenience function for dependency injection
def get_qdrant() -> QdrantManager:
    """Get Qdrant manager instance."""
    return QdrantManager
