"""
Hybrid retriever combining vector search and graph expansion.
Implements the GraphRAG retrieval strategy.
"""
import re
from typing import Optional

from src.services.retrieval.vector_search import get_vector_search, VectorSearch
from src.services.retrieval.graph_expansion import get_graph_expansion, GraphExpansion
from src.services.retrieval.context_assembler import assemble_context


class HybridRetriever:
    """
    Hybrid retriever implementing GraphRAG retrieval strategy:
    1. Vector search for Top-K similar chunks
    2. Extract key terms from query and results
    3. Graph expansion (2-hop) from matching entities
    4. Combine and prioritize context
    """

    def __init__(
        self,
        vector_search: Optional[VectorSearch] = None,
        graph_expansion: Optional[GraphExpansion] = None,
        vector_top_k: int = 5,
        graph_max_hops: int = 2,
        graph_limit_per_entity: int = 5,
        max_context_length: int = 4000,
    ):
        """
        Initialize hybrid retriever.

        Args:
            vector_search: Vector search service
            graph_expansion: Graph expansion service
            vector_top_k: Number of vector search results
            graph_max_hops: Maximum graph traversal depth
            graph_limit_per_entity: Max related entities per starting entity
            max_context_length: Maximum context length
        """
        self._vector_search = vector_search
        self._graph_expansion = graph_expansion
        self.vector_top_k = vector_top_k
        self.graph_max_hops = graph_max_hops
        self.graph_limit_per_entity = graph_limit_per_entity
        self.max_context_length = max_context_length

    async def _get_vector_search(self) -> VectorSearch:
        """Get vector search service."""
        if self._vector_search is None:
            self._vector_search = get_vector_search()
        return self._vector_search

    async def _get_graph_expansion(self) -> GraphExpansion:
        """Get graph expansion service."""
        if self._graph_expansion is None:
            self._graph_expansion = await get_graph_expansion()
        return self._graph_expansion

    def _extract_key_terms(self, query: str, results: list[dict]) -> list[str]:
        """
        Extract key terms from query and results for graph matching.

        Args:
            query: User query
            results: Vector search results

        Returns:
            List of key terms
        """
        terms = set()

        # Extract terms from query (simple tokenization)
        # Remove common stopwords
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into", "through",
            "during", "before", "after", "above", "below", "between",
            "under", "again", "further", "then", "once", "here", "there",
            "when", "where", "why", "how", "all", "each", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only",
            "own", "same", "so", "than", "too", "very", "just", "and",
            "but", "if", "or", "because", "as", "until", "while", "this",
            "that", "these", "those", "what", "which", "who", "whom",
            # Korean stopwords
            "은", "는", "이", "가", "을", "를", "에", "의", "와", "과",
            "도", "로", "으로", "에서", "까지", "부터", "보다",
        }

        # Tokenize query
        words = re.findall(r'\b[a-zA-Z가-힣]+\b', query.lower())
        for word in words:
            if len(word) > 2 and word not in stopwords:
                terms.add(word)

        # Extract important terms from results
        for result in results[:3]:  # Top 3 results
            text = result.get("text", "")
            words = re.findall(r'\b[a-zA-Z가-힣]+\b', text.lower())
            for word in words:
                if len(word) > 3 and word not in stopwords:
                    terms.add(word)
                    if len(terms) >= 10:  # Limit terms
                        break

        return list(terms)[:10]

    async def retrieve(
        self,
        query: str,
        chatbot_id: str,
        include_graph: bool = True,
    ) -> dict:
        """
        Retrieve context using hybrid strategy.

        Args:
            query: User query
            chatbot_id: Chatbot ID
            include_graph: Whether to include graph expansion

        Returns:
            Dict with context, citations, and metadata
        """
        # Step 1: Vector search
        vector_search = await self._get_vector_search()
        vector_results = await vector_search.search(
            query=query,
            chatbot_id=chatbot_id,
            top_k=self.vector_top_k,
        )

        graph_results = []

        if include_graph and vector_results:
            # Step 2: Extract key terms
            key_terms = self._extract_key_terms(query, vector_results)

            if key_terms:
                # Step 3: Find matching entities
                graph_expansion = await self._get_graph_expansion()
                matching_entities = await graph_expansion.find_matching_entities(
                    terms=key_terms,
                    chatbot_id=chatbot_id,
                    limit=5,
                )

                if matching_entities:
                    # Step 4: Graph expansion (2-hop)
                    entity_names = [e["name"] for e in matching_entities]
                    graph_results = await graph_expansion.expand_entities(
                        entity_names=entity_names,
                        chatbot_id=chatbot_id,
                        max_hops=self.graph_max_hops,
                        limit_per_entity=self.graph_limit_per_entity,
                    )

        # Step 5: Assemble context
        context, citations = assemble_context(
            vector_results=vector_results,
            graph_results=graph_results,
            max_length=self.max_context_length,
        )

        return {
            "context": context,
            "citations": citations,
            "vector_count": len(vector_results),
            "graph_count": len(graph_results),
        }


# Singleton instance
_retriever_instance: Optional[HybridRetriever] = None


async def get_hybrid_retriever() -> HybridRetriever:
    """Get or create singleton hybrid retriever."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HybridRetriever()
    return _retriever_instance


async def retrieve_context(
    query: str,
    chatbot_id: str,
    include_graph: bool = True,
) -> dict:
    """
    Convenience function to retrieve context.

    Args:
        query: User query
        chatbot_id: Chatbot ID
        include_graph: Whether to include graph expansion

    Returns:
        Retrieval result dict
    """
    retriever = await get_hybrid_retriever()
    return await retriever.retrieve(query, chatbot_id, include_graph)
