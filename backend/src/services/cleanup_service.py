"""
Cleanup service for removing chatbot data from Neo4j and Qdrant.
"""
import logging

from qdrant_client.http import models as qdrant_models

from src.core.config import settings
from src.core.neo4j import Neo4jClient
from src.core.qdrant import QdrantManager

logger = logging.getLogger(__name__)


class CleanupService:
    """Service for cleaning up chatbot data from vector and graph databases."""

    @staticmethod
    async def cleanup_qdrant_data(chatbot_id: str) -> int:
        """
        Remove all vectors for a chatbot from Qdrant.

        Args:
            chatbot_id: Chatbot ID whose vectors to delete

        Returns:
            Number of deleted vectors (approximate)
        """
        client = QdrantManager.get_client()
        collection_name = settings.qdrant_collection_name

        try:
            # Check if collection exists first
            collections = client.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                logger.info(f"Collection {collection_name} does not exist, nothing to cleanup for chatbot {chatbot_id}")
                return 0

            # First count the vectors to delete
            count_result = client.count(
                collection_name=collection_name,
                count_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="chatbot_id",
                            match=qdrant_models.MatchValue(value=chatbot_id),
                        )
                    ]
                ),
            )
            deleted_count = count_result.count

            if deleted_count == 0:
                logger.info(f"No vectors found for chatbot {chatbot_id}")
                return 0

            # Delete all vectors for this chatbot
            client.delete(
                collection_name=collection_name,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="chatbot_id",
                                match=qdrant_models.MatchValue(value=chatbot_id),
                            )
                        ]
                    )
                ),
            )

            logger.info(f"Deleted {deleted_count} vectors for chatbot {chatbot_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup Qdrant data for chatbot {chatbot_id}: {e}")
            raise

    @staticmethod
    async def cleanup_neo4j_data(chatbot_id: str) -> dict:
        """
        Remove all graph nodes and relationships for a chatbot from Neo4j.

        Args:
            chatbot_id: Chatbot ID whose graph data to delete

        Returns:
            Dict with counts of deleted nodes and relationships
        """
        try:
            async with Neo4jClient.session() as session:
                # Delete all nodes and relationships for this chatbot
                # Using DETACH DELETE to remove relationships automatically
                result = await session.run(
                    """
                    MATCH (n)
                    WHERE n.chatbot_id = $chatbot_id
                    WITH n
                    DETACH DELETE n
                    RETURN count(n) as deleted_nodes
                    """,
                    chatbot_id=chatbot_id,
                )

                record = await result.single()
                deleted_nodes = record["deleted_nodes"] if record else 0

                logger.info(f"Deleted {deleted_nodes} nodes for chatbot {chatbot_id}")

                return {
                    "deleted_nodes": deleted_nodes,
                }

        except Exception as e:
            logger.error(f"Failed to cleanup Neo4j data for chatbot {chatbot_id}: {e}")
            raise

    @staticmethod
    async def cleanup_all(chatbot_id: str) -> dict:
        """
        Remove all data for a chatbot from both Qdrant and Neo4j.

        Args:
            chatbot_id: Chatbot ID to cleanup

        Returns:
            Dict with cleanup statistics
        """
        results = {
            "chatbot_id": chatbot_id,
            "qdrant_vectors_deleted": 0,
            "neo4j_nodes_deleted": 0,
            "errors": [],
        }

        # Cleanup Qdrant
        try:
            results["qdrant_vectors_deleted"] = await CleanupService.cleanup_qdrant_data(
                chatbot_id
            )
        except Exception as e:
            results["errors"].append(f"Qdrant cleanup failed: {str(e)}")
            logger.error(f"Qdrant cleanup failed: {e}")

        # Cleanup Neo4j
        try:
            neo4j_result = await CleanupService.cleanup_neo4j_data(chatbot_id)
            results["neo4j_nodes_deleted"] = neo4j_result.get("deleted_nodes", 0)
        except Exception as e:
            results["errors"].append(f"Neo4j cleanup failed: {str(e)}")
            logger.error(f"Neo4j cleanup failed: {e}")

        if results["errors"]:
            logger.warning(
                f"Cleanup for chatbot {chatbot_id} completed with errors: {results['errors']}"
            )
        else:
            logger.info(
                f"Cleanup for chatbot {chatbot_id} completed successfully: "
                f"{results['qdrant_vectors_deleted']} vectors, "
                f"{results['neo4j_nodes_deleted']} nodes"
            )

        return results


async def cleanup_chatbot_data(chatbot_id: str) -> dict:
    """
    Convenience function to cleanup all chatbot data.

    Args:
        chatbot_id: Chatbot ID to cleanup

    Returns:
        Cleanup statistics
    """
    return await CleanupService.cleanup_all(chatbot_id)
