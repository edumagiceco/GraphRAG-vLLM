"""
Context assembler for combining retrieval results.
Prioritizes and deduplicates context from vector and graph sources.
"""
from typing import Optional, Any
from dataclasses import dataclass


def sanitize_text(text: str) -> str:
    """
    Sanitize text for PostgreSQL storage.
    Removes null characters which are not supported in PostgreSQL JSONB.
    """
    if not text:
        return text
    return text.replace('\x00', '').replace('\u0000', '')


@dataclass
class ContextItem:
    """A single context item from retrieval."""

    text: str
    source: str  # "vector" or "graph"
    score: float  # Relevance score (0-1)
    document_id: Optional[str] = None
    filename: Optional[str] = None
    page_num: Optional[int] = None
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    relationship: Optional[str] = None


class ContextAssembler:
    """
    Assembles and prioritizes context from multiple retrieval sources.
    Combines vector search results and graph expansion results.
    """

    def __init__(
        self,
        max_context_length: int = 4000,
        vector_weight: float = 0.7,
        graph_weight: float = 0.3,
    ):
        """
        Initialize context assembler.

        Args:
            max_context_length: Maximum context length in characters
            vector_weight: Weight for vector search results
            graph_weight: Weight for graph expansion results
        """
        self.max_context_length = max_context_length
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight

    def assemble(
        self,
        vector_results: list[dict],
        graph_results: list[dict],
    ) -> tuple[str, list[dict]]:
        """
        Assemble context from vector and graph results.

        Args:
            vector_results: Results from vector search
            graph_results: Results from graph expansion

        Returns:
            Tuple of (assembled context text, source citations)
        """
        items = []

        # Process vector results
        for result in vector_results:
            text = result.get("text", "")
            items.append(ContextItem(
                text=sanitize_text(text),
                source="vector",
                score=result.get("score", 0) * self.vector_weight,
                document_id=result.get("document_id"),
                filename=sanitize_text(result.get("filename", "")),
                page_num=result.get("page_num"),
            ))

        # Process graph results
        for result in graph_results:
            description = result.get("description", "")
            if description:
                # Adjust score based on graph distance
                distance = result.get("distance", 1)
                base_score = 1.0 / (distance + 1)  # Closer = higher score

                items.append(ContextItem(
                    text=sanitize_text(description),
                    source="graph",
                    score=base_score * self.graph_weight,
                    document_id=result.get("document_id"),
                    entity_name=sanitize_text(result.get("name", "")),
                    entity_type=sanitize_text(result.get("type", "")),
                    relationship=", ".join(result.get("relationships", [])),
                ))

        # Sort by score and deduplicate
        items = self._deduplicate(items)
        items.sort(key=lambda x: x.score, reverse=True)

        # Assemble context within length limit
        context_parts = []
        citations = []
        current_length = 0

        for item in items:
            if current_length + len(item.text) > self.max_context_length:
                # Try truncating this item
                remaining = self.max_context_length - current_length
                if remaining > 100:  # Only add if meaningful
                    truncated_text = item.text[:remaining] + "..."
                    context_parts.append(truncated_text)
                    citations.append(self._create_citation(item))
                break

            context_parts.append(item.text)
            citations.append(self._create_citation(item))
            current_length += len(item.text) + 2  # +2 for newlines

        # Join context parts
        context = "\n\n".join(context_parts)

        return context, citations

    def _deduplicate(self, items: list[ContextItem]) -> list[ContextItem]:
        """
        Remove duplicate or highly similar items.

        Args:
            items: List of context items

        Returns:
            Deduplicated list
        """
        seen_texts = set()
        unique_items = []

        for item in items:
            # Normalize text for comparison
            normalized = item.text.lower().strip()[:100]

            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique_items.append(item)

        return unique_items

    def _create_citation(self, item: ContextItem) -> dict:
        """
        Create citation dict from context item.

        Args:
            item: Context item

        Returns:
            Citation dict
        """
        citation = {
            "source": item.source,
            "score": round(item.score, 3),
        }

        if item.filename:
            citation["filename"] = item.filename
        if item.page_num:
            citation["page"] = item.page_num
        if item.document_id:
            citation["document_id"] = item.document_id
        if item.entity_name:
            citation["entity"] = item.entity_name
        if item.entity_type:
            citation["entity_type"] = item.entity_type
        if item.relationship:
            citation["relationship"] = item.relationship

        # Include chunk text preview for source display
        if item.text:
            # Sanitize and truncate to 200 characters for preview
            sanitized = sanitize_text(item.text)
            citation["chunk_text"] = sanitized[:200] + "..." if len(sanitized) > 200 else sanitized

        return citation


def assemble_context(
    vector_results: list[dict],
    graph_results: list[dict],
    max_length: int = 4000,
) -> tuple[str, list[dict]]:
    """
    Convenience function to assemble context.

    Args:
        vector_results: Vector search results
        graph_results: Graph expansion results
        max_length: Maximum context length

    Returns:
        Tuple of (context text, citations)
    """
    assembler = ContextAssembler(max_context_length=max_length)
    return assembler.assemble(vector_results, graph_results)
