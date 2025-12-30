"""
Graph expansion service using Neo4j.
Expands context by traversing knowledge graph relationships.
"""
from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

from src.core.config import settings


class GraphExpansion:
    """
    Service for expanding context through knowledge graph traversal.
    Implements 2-hop expansion from initial entities.
    """

    def __init__(self, driver: Optional[AsyncDriver] = None):
        """
        Initialize graph expansion.

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
        """Close Neo4j driver."""
        await self._driver.close()

    async def find_matching_entities(
        self,
        terms: list[str],
        chatbot_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Find entities matching given terms (fuzzy match).

        Searches in both entity name and description for better matching.

        Args:
            terms: Search terms to match
            chatbot_id: Chatbot ID
            limit: Maximum results

        Returns:
            List of matching entities
        """
        if not terms:
            return []

        async with self._driver.session() as session:
            # Search in both name and description for better matching
            # Score: name match = 2, description match = 1
            query = """
            MATCH (e {chatbot_id: $chatbot_id})
            WITH e,
                 CASE WHEN any(term IN $terms WHERE toLower(e.name) CONTAINS toLower(term)) THEN 2 ELSE 0 END +
                 CASE WHEN any(term IN $terms WHERE e.description IS NOT NULL AND toLower(e.description) CONTAINS toLower(term)) THEN 1 ELSE 0 END
                 AS match_score
            WHERE match_score > 0
            RETURN e.name as name,
                   labels(e)[0] as type,
                   e.description as description,
                   e.document_id as document_id,
                   match_score
            ORDER BY match_score DESC
            LIMIT $limit
            """

            result = await session.run(
                query,
                terms=terms,
                chatbot_id=chatbot_id,
                limit=limit,
            )

            entities = []
            async for record in result:
                entities.append({
                    "name": record["name"],
                    "type": record["type"],
                    "description": record["description"],
                    "document_id": record["document_id"],
                })

            return entities

    async def expand_entities(
        self,
        entity_names: list[str],
        chatbot_id: str,
        max_hops: int = 2,
        limit_per_entity: int = 5,
    ) -> list[dict]:
        """
        Expand from given entities by traversing graph relationships.

        Args:
            entity_names: Starting entity names
            chatbot_id: Chatbot ID
            max_hops: Maximum traversal depth (default: 2)
            limit_per_entity: Max related entities per starting entity

        Returns:
            List of related entities with relationship info
        """
        if not entity_names:
            return []

        async with self._driver.session() as session:
            # Variable-length path traversal
            query = f"""
            MATCH (start {{chatbot_id: $chatbot_id}})
            WHERE start.name IN $entity_names
            MATCH path = (start)-[rels*1..{max_hops}]-(related {{chatbot_id: $chatbot_id}})
            WHERE start <> related
            WITH start.name as source,
                 related,
                 [r in rels | type(r)] as rel_types,
                 length(path) as distance
            ORDER BY distance
            WITH source, collect({{
                name: related.name,
                type: labels(related)[0],
                description: related.description,
                document_id: related.document_id,
                rel_types: rel_types,
                distance: distance
            }})[0..$limit_per_entity] as related_list
            UNWIND related_list as rel
            RETURN DISTINCT rel.name as name,
                   rel.type as type,
                   rel.description as description,
                   rel.document_id as document_id,
                   rel.rel_types as relationships,
                   rel.distance as distance,
                   source as from_entity
            """

            result = await session.run(
                query,
                entity_names=entity_names,
                chatbot_id=chatbot_id,
                limit_per_entity=limit_per_entity,
            )

            expanded = []
            seen_names = set()

            async for record in result:
                name = record["name"]
                if name not in seen_names and name not in entity_names:
                    seen_names.add(name)
                    expanded.append({
                        "name": name,
                        "type": record["type"],
                        "description": record["description"],
                        "document_id": record["document_id"],
                        "relationships": record["relationships"],
                        "distance": record["distance"],
                        "from_entity": record["from_entity"],
                    })

            return expanded

    async def get_entity_subgraph(
        self,
        entity_names: list[str],
        chatbot_id: str,
        max_hops: int = 2,
    ) -> dict:
        """
        Get subgraph around given entities.

        Args:
            entity_names: Central entity names
            chatbot_id: Chatbot ID
            max_hops: Maximum traversal depth

        Returns:
            Dict with nodes and edges
        """
        if not entity_names:
            return {"nodes": [], "edges": []}

        async with self._driver.session() as session:
            query = f"""
            MATCH (start {{chatbot_id: $chatbot_id}})
            WHERE start.name IN $entity_names
            OPTIONAL MATCH path = (start)-[*1..{max_hops}]-(related {{chatbot_id: $chatbot_id}})
            WITH collect(DISTINCT start) + collect(DISTINCT related) as all_nodes
            UNWIND all_nodes as node
            WITH collect(DISTINCT node) as nodes
            UNWIND nodes as n
            OPTIONAL MATCH (n)-[r]-(m)
            WHERE m IN nodes
            WITH nodes, collect(DISTINCT {{
                source: n.name,
                target: m.name,
                type: type(r)
            }}) as edges
            RETURN [node IN nodes | {{
                name: node.name,
                type: labels(node)[0],
                description: node.description
            }}] as nodes,
            [e IN edges WHERE e.source IS NOT NULL AND e.target IS NOT NULL] as edges
            """

            result = await session.run(
                query,
                entity_names=entity_names,
                chatbot_id=chatbot_id,
            )

            record = await result.single()
            if not record:
                return {"nodes": [], "edges": []}

            return {
                "nodes": record["nodes"],
                "edges": record["edges"],
            }


# Singleton instance
_expansion_instance: Optional[GraphExpansion] = None


async def get_graph_expansion() -> GraphExpansion:
    """Get or create singleton graph expansion instance."""
    global _expansion_instance
    if _expansion_instance is None:
        _expansion_instance = GraphExpansion()
    return _expansion_instance
