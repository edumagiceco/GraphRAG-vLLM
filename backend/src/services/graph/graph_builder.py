"""
Knowledge graph builder for Neo4j storage.
"""
import re
from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

from src.core.config import settings


def sanitize_label(label: str) -> str:
    """
    Sanitize a string to be a valid Neo4j label.
    Neo4j labels can only contain letters, numbers, and underscores.

    Args:
        label: Raw label string

    Returns:
        Sanitized label string
    """
    if not label:
        return "Concept"

    # Replace common separators with underscore
    sanitized = re.sub(r'[/\-\s]+', '_', label)
    # Remove any other invalid characters
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', sanitized)
    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'E_' + sanitized
    # Default to Concept if empty
    return sanitized if sanitized else "Concept"


class GraphBuilder:
    """Service for building and managing knowledge graphs in Neo4j."""

    def __init__(self, driver: Optional[AsyncDriver] = None):
        """
        Initialize graph builder.

        Args:
            driver: Optional Neo4j async driver
        """
        if driver:
            self._driver = driver
        else:
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )

    async def close(self) -> None:
        """Close the Neo4j driver."""
        await self._driver.close()

    async def add_entities(
        self,
        entities: list[dict],
        chatbot_id: str,
        document_id: str,
    ) -> int:
        """
        Add entities as nodes to the knowledge graph.

        Args:
            entities: List of entity dicts
            chatbot_id: Chatbot ID
            document_id: Source document ID

        Returns:
            Number of entities added
        """
        if not entities:
            return 0

        async with self._driver.session() as session:
            count = 0
            for entity in entities:
                raw_type = entity.get("type", "Concept")
                entity_type = sanitize_label(raw_type)
                name = entity.get("name", "").strip()
                description = entity.get("description", "")

                if not name:
                    continue

                # Create entity node with appropriate label
                query = f"""
                MERGE (e:{entity_type} {{name: $name, chatbot_id: $chatbot_id}})
                ON CREATE SET
                    e.description = $description,
                    e.document_id = $document_id,
                    e.created_at = datetime()
                ON MATCH SET
                    e.description = CASE
                        WHEN size(e.description) < size($description)
                        THEN $description
                        ELSE e.description
                    END
                RETURN e
                """

                await session.run(
                    query,
                    name=name,
                    description=description,
                    chatbot_id=chatbot_id,
                    document_id=document_id,
                )
                count += 1

            return count

    async def add_relationships(
        self,
        relationships: list[dict],
        chatbot_id: str,
        document_id: str,
    ) -> int:
        """
        Add relationships as edges to the knowledge graph.

        Args:
            relationships: List of relationship dicts
            chatbot_id: Chatbot ID
            document_id: Source document ID

        Returns:
            Number of relationships added
        """
        if not relationships:
            return 0

        async with self._driver.session() as session:
            count = 0
            for rel in relationships:
                source = rel.get("source", "").strip()
                target = rel.get("target", "").strip()
                raw_rel_type = rel.get("type", "RELATED_TO")
                # Sanitize relationship type (uppercase, underscores only)
                rel_type = re.sub(r'[^A-Z0-9_]', '_', raw_rel_type.upper())
                rel_type = rel_type if rel_type else "RELATED_TO"

                if not source or not target:
                    continue

                # Create relationship between entities
                # Using dynamic relationship type
                query = f"""
                MATCH (s {{name: $source, chatbot_id: $chatbot_id}})
                MATCH (t {{name: $target, chatbot_id: $chatbot_id}})
                MERGE (s)-[r:{rel_type}]->(t)
                ON CREATE SET
                    r.document_id = $document_id,
                    r.created_at = datetime()
                RETURN r
                """

                result = await session.run(
                    query,
                    source=source,
                    target=target,
                    chatbot_id=chatbot_id,
                    document_id=document_id,
                )

                # Check if relationship was created
                records = [r async for r in result]
                if records:
                    count += 1

            return count

    async def get_related_entities(
        self,
        entity_names: list[str],
        chatbot_id: str,
        max_hops: int = 2,
        limit: int = 20,
    ) -> list[dict]:
        """
        Get entities related to given entities within N hops.

        Args:
            entity_names: Starting entity names
            chatbot_id: Chatbot ID
            max_hops: Maximum traversal depth
            limit: Maximum results

        Returns:
            List of related entities with paths
        """
        if not entity_names:
            return []

        async with self._driver.session() as session:
            # Variable-length path query
            query = f"""
            MATCH (start {{chatbot_id: $chatbot_id}})
            WHERE start.name IN $entity_names
            MATCH path = (start)-[*1..{max_hops}]-(related {{chatbot_id: $chatbot_id}})
            WHERE start <> related
            WITH DISTINCT related, min(length(path)) as distance
            RETURN related.name as name,
                   labels(related)[0] as type,
                   related.description as description,
                   distance
            ORDER BY distance, related.name
            LIMIT $limit
            """

            result = await session.run(
                query,
                entity_names=entity_names,
                chatbot_id=chatbot_id,
                limit=limit,
            )

            entities = []
            async for record in result:
                entities.append({
                    "name": record["name"],
                    "type": record["type"],
                    "description": record["description"],
                    "distance": record["distance"],
                })

            return entities

    async def get_entity_context(
        self,
        entity_name: str,
        chatbot_id: str,
    ) -> dict:
        """
        Get full context for an entity including related entities.

        Args:
            entity_name: Entity name
            chatbot_id: Chatbot ID

        Returns:
            Entity with related entities and relationships
        """
        async with self._driver.session() as session:
            # Get entity and its direct relationships
            query = """
            MATCH (e {name: $entity_name, chatbot_id: $chatbot_id})
            OPTIONAL MATCH (e)-[r]-(related {chatbot_id: $chatbot_id})
            RETURN e.name as name,
                   labels(e)[0] as type,
                   e.description as description,
                   collect(DISTINCT {
                       name: related.name,
                       type: labels(related)[0],
                       relation: type(r),
                       direction: CASE WHEN startNode(r) = e THEN 'outgoing' ELSE 'incoming' END
                   }) as related
            """

            result = await session.run(
                query,
                entity_name=entity_name,
                chatbot_id=chatbot_id,
            )

            record = await result.single()
            if not record:
                return {}

            return {
                "name": record["name"],
                "type": record["type"],
                "description": record["description"],
                "related": [r for r in record["related"] if r["name"]],
            }

    async def delete_by_document(self, document_id: str) -> int:
        """
        Delete all entities and relationships from a document.

        Args:
            document_id: Document ID

        Returns:
            Number of nodes deleted
        """
        async with self._driver.session() as session:
            query = """
            MATCH (e {document_id: $document_id})
            DETACH DELETE e
            RETURN count(e) as deleted
            """

            result = await session.run(query, document_id=document_id)
            record = await result.single()
            return record["deleted"] if record else 0

    async def delete_by_chatbot(self, chatbot_id: str) -> int:
        """
        Delete all entities and relationships for a chatbot.

        Args:
            chatbot_id: Chatbot ID

        Returns:
            Number of nodes deleted
        """
        async with self._driver.session() as session:
            query = """
            MATCH (e {chatbot_id: $chatbot_id})
            DETACH DELETE e
            RETURN count(e) as deleted
            """

            result = await session.run(query, chatbot_id=chatbot_id)
            record = await result.single()
            return record["deleted"] if record else 0

    async def get_stats(self, chatbot_id: str) -> dict:
        """
        Get knowledge graph statistics for a chatbot.

        Args:
            chatbot_id: Chatbot ID

        Returns:
            Statistics dict
        """
        async with self._driver.session() as session:
            query = """
            MATCH (e {chatbot_id: $chatbot_id})
            WITH count(e) as node_count,
                 collect(labels(e)[0]) as labels
            OPTIONAL MATCH ({chatbot_id: $chatbot_id})-[r]-({chatbot_id: $chatbot_id})
            WITH node_count, labels, count(DISTINCT r) as edge_count
            RETURN node_count, edge_count,
                   reduce(s = {}, l IN labels |
                       CASE
                           WHEN s[l] IS NULL THEN s{[l]: 1}
                           ELSE s{[l]: s[l] + 1}
                       END
                   ) as label_counts
            """

            result = await session.run(query, chatbot_id=chatbot_id)
            record = await result.single()

            if not record:
                return {"node_count": 0, "edge_count": 0, "label_counts": {}}

            return {
                "node_count": record["node_count"],
                "edge_count": record["edge_count"],
                "label_counts": dict(record["label_counts"]) if record["label_counts"] else {},
            }


# Singleton instance
_builder_instance: Optional[GraphBuilder] = None


async def get_graph_builder() -> GraphBuilder:
    """Get or create singleton graph builder instance."""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = GraphBuilder()
    return _builder_instance
