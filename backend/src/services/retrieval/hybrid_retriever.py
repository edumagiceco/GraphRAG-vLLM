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
        max_context_length: int = 2000,
        score_threshold: float = 0.15,
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
            score_threshold: Minimum similarity score threshold
        """
        self._vector_search = vector_search
        self._graph_expansion = graph_expansion
        self.vector_top_k = vector_top_k
        self.graph_max_hops = graph_max_hops
        self.graph_limit_per_entity = graph_limit_per_entity
        self.max_context_length = max_context_length
        self.score_threshold = score_threshold

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

        # Korean verb/adjective endings and particles to remove
        korean_suffixes = [
            # Verb endings
            "해줘", "해줘요", "해주세요", "알려줘", "알려줘요", "알려주세요",
            "하세요", "할까요", "할게요", "합니다", "해요", "하다",
            "인가요", "인지", "일까", "인데", "이야", "예요",
            # Noun particles/suffixes
            "에서", "에게", "으로", "에는", "에도", "까지", "부터",
            "이란", "이라", "란", "라", "라는",
        ]

        # Stopwords (common non-content words)
        stopwords = {
            # English
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "and", "or",
            "but", "if", "this", "that", "what", "which", "who", "how",
            # Korean particles and common words
            "은", "는", "이", "가", "을", "를", "에", "의", "와", "과",
            "도", "로", "으로", "좀", "뭐", "어떻게", "어떤", "무엇",
            "것", "거", "수", "때", "중", "및", "등", "더", "또", "그",
        }

        # Common question patterns and verbs to filter out
        question_patterns = {
            "알려", "알려줘", "설명", "말해", "뭐야", "뭔지", "무엇", "어떻게",
            "방법", "이유", "원인", "결과", "의미", "있을", "없을", "하는",
            "되는", "되었", "인정하는", "소속", "기타", "해당",
        }

        def clean_korean_word(word: str) -> str:
            """Remove Korean suffixes from word."""
            cleaned = word
            for suffix in sorted(korean_suffixes, key=len, reverse=True):
                if cleaned.endswith(suffix) and len(cleaned) > len(suffix):
                    cleaned = cleaned[:-len(suffix)]
                    break
            # Also remove single character particles at the end
            if len(cleaned) > 1 and cleaned[-1] in "을를이가은는에서의":
                cleaned = cleaned[:-1]
            return cleaned

        # Extract from query
        words = re.findall(r'[가-힣]+', query)
        for word in words:
            cleaned = clean_korean_word(word)
            if (len(cleaned) >= 2 and
                cleaned not in stopwords and
                cleaned not in question_patterns):
                terms.add(cleaned)

        # Priority terms that often match Neo4j entities
        priority_terms = {
            "급여", "지급", "직원", "회사", "퇴직금", "복리", "후생",
            "출장", "여비", "정산", "교통", "숙박", "식대", "수당",
            "휴가", "근무", "임금", "보수", "상여", "인사", "채용",
        }

        # Extract from vector search results (top 3)
        for result in results[:3]:
            text = result.get("text", "")
            # Clean text: remove null characters and normalize whitespace
            text = re.sub(r'[\x00\r]', '', text)
            text = re.sub(r'\s+', ' ', text)

            # 1. Look for bracketed terms (often important concepts in Korean documents)
            bracketed = re.findall(r'【([^】]+)】', text)
            for term in bracketed:
                clean_term = re.sub(r'[^가-힣a-zA-Z]', '', term)
                if 2 <= len(clean_term) <= 10 and clean_term not in question_patterns:
                    terms.add(clean_term)

            # 2. First priority: find known entity-matching terms
            for priority in priority_terms:
                if priority in text:
                    terms.add(priority)

            # 3. Extract Korean compound nouns (2-4 characters, likely content words)
            words = re.findall(r'[가-힣]{2,4}', text)
            for word in words:
                if (word not in stopwords and
                    word not in question_patterns and
                    len(terms) < 20):
                    terms.add(word)

        # Final filter: remove any remaining question words
        terms = {t for t in terms if t not in question_patterns and len(t) >= 2}

        # Prioritize known entity terms
        priority_in_terms = [t for t in terms if t in priority_terms]
        other_terms = [t for t in terms if t not in priority_terms]

        return priority_in_terms + other_terms[:15 - len(priority_in_terms)]

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
        # Step 1: Vector search with score threshold
        vector_search = await self._get_vector_search()
        vector_results = await vector_search.search(
            query=query,
            chatbot_id=chatbot_id,
            top_k=self.vector_top_k,
            score_threshold=self.score_threshold,
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
