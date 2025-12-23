"""
Neo4j graph database connection client.
"""
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from src.core.config import settings


class Neo4jClient:
    """Async Neo4j client for graph operations."""

    _driver: Optional[AsyncDriver] = None

    @classmethod
    async def connect(cls) -> None:
        """Initialize Neo4j driver connection."""
        if cls._driver is None:
            cls._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            # Verify connectivity
            await cls._driver.verify_connectivity()

    @classmethod
    async def close(cls) -> None:
        """Close Neo4j driver connection."""
        if cls._driver is not None:
            await cls._driver.close()
            cls._driver = None

    @classmethod
    @asynccontextmanager
    async def session(cls) -> AsyncGenerator[AsyncSession, None]:
        """Get a Neo4j session context manager."""
        if cls._driver is None:
            await cls.connect()
        async with cls._driver.session() as session:
            yield session

    @classmethod
    async def execute_query(
        cls,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        async with cls.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    @classmethod
    async def execute_write(
        cls,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Execute a write Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters
        """
        async with cls.session() as session:
            await session.run(query, parameters or {})

    # =========================================================================
    # Graph Node Operations
    # =========================================================================

    @classmethod
    async def create_node(
        cls,
        label: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a node with given label and properties.

        Args:
            label: Node label (Concept, Definition, Process)
            properties: Node properties

        Returns:
            Created node properties
        """
        query = f"""
        CREATE (n:{label} $props)
        RETURN n
        """
        result = await cls.execute_query(query, {"props": properties})
        return result[0]["n"] if result else {}

    @classmethod
    async def create_relationship(
        cls,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create a relationship between two nodes.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            rel_type: Relationship type (RELATED_TO, DEFINES, DEPENDS_ON)
            properties: Relationship properties
        """
        query = f"""
        MATCH (a {{id: $from_id}})
        MATCH (b {{id: $to_id}})
        CREATE (a)-[r:{rel_type} $props]->(b)
        """
        await cls.execute_write(
            query,
            {
                "from_id": from_id,
                "to_id": to_id,
                "props": properties or {},
            },
        )

    @classmethod
    async def get_node_by_id(
        cls,
        node_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a node by its ID."""
        query = """
        MATCH (n {id: $node_id})
        RETURN n
        """
        result = await cls.execute_query(query, {"node_id": node_id})
        return result[0]["n"] if result else None

    @classmethod
    async def get_nodes_by_chatbot_version(
        cls,
        chatbot_id: str,
        version: int,
        label: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all nodes for a specific chatbot version.

        Args:
            chatbot_id: Chatbot service ID
            version: Index version number
            label: Optional node label filter

        Returns:
            List of nodes
        """
        label_filter = f":{label}" if label else ""
        query = f"""
        MATCH (n{label_filter} {{chatbot_id: $chatbot_id, version: $version}})
        RETURN n
        """
        result = await cls.execute_query(
            query,
            {"chatbot_id": chatbot_id, "version": version},
        )
        return [r["n"] for r in result]

    @classmethod
    async def expand_graph(
        cls,
        seed_ids: List[str],
        chatbot_id: str,
        version: int,
        max_hops: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Expand graph from seed nodes up to max_hops.

        Args:
            seed_ids: Starting node IDs
            chatbot_id: Chatbot service ID
            version: Index version number
            max_hops: Maximum traversal depth (default: 2)

        Returns:
            List of related nodes with paths
        """
        query = f"""
        MATCH (start {{chatbot_id: $chatbot_id, version: $version}})
        WHERE start.id IN $seed_ids
        MATCH path = (start)-[*1..{max_hops}]-(related)
        WHERE related.chatbot_id = $chatbot_id AND related.version = $version
        RETURN DISTINCT related, length(path) as distance
        ORDER BY distance
        """
        result = await cls.execute_query(
            query,
            {
                "seed_ids": seed_ids,
                "chatbot_id": chatbot_id,
                "version": version,
            },
        )
        return result

    @classmethod
    async def delete_chatbot_version(
        cls,
        chatbot_id: str,
        version: int,
    ) -> int:
        """
        Delete all nodes for a specific chatbot version.

        Args:
            chatbot_id: Chatbot service ID
            version: Index version number

        Returns:
            Number of deleted nodes
        """
        query = """
        MATCH (n {chatbot_id: $chatbot_id, version: $version})
        WITH n, count(n) as cnt
        DETACH DELETE n
        RETURN cnt
        """
        result = await cls.execute_query(
            query,
            {"chatbot_id": chatbot_id, "version": version},
        )
        return result[0]["cnt"] if result else 0


# Convenience function for dependency injection
async def get_neo4j() -> Neo4jClient:
    """Get Neo4j client instance."""
    return Neo4jClient
