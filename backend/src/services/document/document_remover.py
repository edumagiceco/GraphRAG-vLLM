"""
Document remover service for cleaning up document data from vector and graph databases.
"""
import logging
from typing import Optional

from qdrant_client.http import models as qdrant_models

from src.core.config import settings
from src.core.neo4j import Neo4jClient
from src.core.qdrant import QdrantManager

logger = logging.getLogger(__name__)


class DocumentRemover:
    """Service for removing document data from Qdrant and Neo4j."""

    @staticmethod
    async def remove_from_qdrant(
        document_id: str,
        chatbot_id: Optional[str] = None,
    ) -> int:
        """
        Remove document vectors from Qdrant.

        Args:
            document_id: Document ID
            chatbot_id: Optional chatbot ID for additional filtering

        Returns:
            Number of deleted vectors (approximate)
        """
        client = QdrantManager.get_client()

        try:
            # Build filter conditions
            filter_conditions = [
                qdrant_models.FieldCondition(
                    key="document_id",
                    match=qdrant_models.MatchValue(value=document_id),
                )
            ]

            if chatbot_id:
                filter_conditions.append(
                    qdrant_models.FieldCondition(
                        key="chatbot_id",
                        match=qdrant_models.MatchValue(value=chatbot_id),
                    )
                )

            # Get all collections and delete from each
            collections = client.get_collections().collections
            total_deleted = 0

            for collection in collections:
                try:
                    # Count vectors to delete
                    count_result = client.count(
                        collection_name=collection.name,
                        count_filter=qdrant_models.Filter(must=filter_conditions),
                    )

                    if count_result.count > 0:
                        # Delete vectors
                        client.delete(
                            collection_name=collection.name,
                            points_selector=qdrant_models.FilterSelector(
                                filter=qdrant_models.Filter(must=filter_conditions)
                            ),
                        )
                        total_deleted += count_result.count
                except Exception:
                    # Collection may not have the required fields, skip
                    pass

            if total_deleted == 0:
                logger.info(f"No vectors found for document {document_id}")
            else:
                logger.info(f"Deleted {total_deleted} vectors for document {document_id}")

            return total_deleted

        except Exception as e:
            logger.error(f"Failed to remove vectors for document {document_id}: {e}")
            raise

    @staticmethod
    async def remove_from_neo4j(
        document_id: str,
        chatbot_id: Optional[str] = None,
    ) -> dict:
        """
        Remove document entities and relationships from Neo4j.

        Args:
            document_id: Document ID
            chatbot_id: Optional chatbot ID for additional filtering

        Returns:
            Dict with counts of deleted nodes and relationships
        """
        try:
            # Build Cypher query based on parameters
            if chatbot_id:
                query = """
                    MATCH (n)
                    WHERE n.document_id = $document_id AND n.chatbot_id = $chatbot_id
                    WITH n
                    DETACH DELETE n
                    RETURN count(n) as deleted_nodes
                """
                params = {"document_id": document_id, "chatbot_id": chatbot_id}
            else:
                query = """
                    MATCH (n)
                    WHERE n.document_id = $document_id
                    WITH n
                    DETACH DELETE n
                    RETURN count(n) as deleted_nodes
                """
                params = {"document_id": document_id}

            result = await Neo4jClient.execute_query(query, params)
            deleted_nodes = result[0]["deleted_nodes"] if result else 0

            logger.info(f"Deleted {deleted_nodes} nodes for document {document_id}")

            return {
                "deleted_nodes": deleted_nodes,
            }

        except Exception as e:
            logger.error(f"Failed to remove Neo4j data for document {document_id}: {e}")
            raise

    @staticmethod
    async def remove_all(
        document_id: str,
        chatbot_id: Optional[str] = None,
    ) -> dict:
        """
        Remove all data for a document from both Qdrant and Neo4j.

        Args:
            document_id: Document ID
            chatbot_id: Optional chatbot ID

        Returns:
            Dict with removal statistics
        """
        results = {
            "document_id": document_id,
            "qdrant_vectors_deleted": 0,
            "neo4j_nodes_deleted": 0,
            "errors": [],
        }

        # Remove from Qdrant
        try:
            results["qdrant_vectors_deleted"] = await DocumentRemover.remove_from_qdrant(
                document_id, chatbot_id
            )
        except Exception as e:
            results["errors"].append(f"Qdrant removal failed: {str(e)}")
            logger.error(f"Qdrant removal failed: {e}")

        # Remove from Neo4j
        try:
            neo4j_result = await DocumentRemover.remove_from_neo4j(
                document_id, chatbot_id
            )
            results["neo4j_nodes_deleted"] = neo4j_result.get("deleted_nodes", 0)
        except Exception as e:
            results["errors"].append(f"Neo4j removal failed: {str(e)}")
            logger.error(f"Neo4j removal failed: {e}")

        if results["errors"]:
            logger.warning(
                f"Document {document_id} removal completed with errors: {results['errors']}"
            )
        else:
            logger.info(
                f"Document {document_id} removal completed: "
                f"{results['qdrant_vectors_deleted']} vectors, "
                f"{results['neo4j_nodes_deleted']} nodes"
            )

        return results


async def remove_document_data(
    document_id: str,
    chatbot_id: Optional[str] = None,
) -> dict:
    """
    Convenience function to remove all document data.

    Args:
        document_id: Document ID
        chatbot_id: Optional chatbot ID

    Returns:
        Removal statistics
    """
    return await DocumentRemover.remove_all(document_id, chatbot_id)
