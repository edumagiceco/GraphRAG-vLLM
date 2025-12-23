"""
Source citation formatter for LLM responses.
Formats and validates source references in generated text.
"""
import re
from typing import Optional


def format_sources_in_response(
    response: str,
    citations: list[dict],
) -> str:
    """
    Format source references in LLM response.
    Converts [Source: X] patterns to formatted citations.

    Args:
        response: LLM response text
        citations: Available source citations

    Returns:
        Response with formatted source references
    """
    if not citations:
        return response

    # Find all source references
    pattern = r'\[Source:\s*(\d+)\]'

    def replace_source(match):
        try:
            source_num = int(match.group(1))
            if 1 <= source_num <= len(citations):
                citation = citations[source_num - 1]
                return format_citation(citation)
        except (ValueError, IndexError):
            pass
        return match.group(0)

    return re.sub(pattern, replace_source, response)


def format_citation(citation: dict) -> str:
    """
    Format a single citation for display.

    Args:
        citation: Citation dict

    Returns:
        Formatted citation string
    """
    parts = []

    if citation.get("filename"):
        parts.append(citation["filename"])

    if citation.get("page"):
        parts.append(f"p.{citation['page']}")

    if citation.get("entity"):
        entity_str = citation["entity"]
        if citation.get("entity_type"):
            entity_str += f" ({citation['entity_type']})"
        parts.append(entity_str)

    if not parts:
        return "[출처]"

    return f"[{', '.join(parts)}]"


def extract_source_references(text: str) -> list[int]:
    """
    Extract source reference numbers from text.

    Args:
        text: Text containing source references

    Returns:
        List of source numbers referenced
    """
    pattern = r'\[Source:\s*(\d+)\]'
    matches = re.findall(pattern, text)
    return [int(m) for m in matches]


def build_sources_section(
    citations: list[dict],
    used_indices: Optional[list[int]] = None,
) -> str:
    """
    Build a formatted sources section for the response.

    Args:
        citations: All available citations
        used_indices: Optional list of used citation indices (1-indexed)

    Returns:
        Formatted sources section
    """
    if not citations:
        return ""

    # Filter to used citations if specified
    if used_indices:
        filtered = [
            (i, c) for i, c in enumerate(citations, 1)
            if i in used_indices
        ]
    else:
        filtered = [(i, c) for i, c in enumerate(citations, 1)]

    if not filtered:
        return ""

    lines = ["\n---\n**출처:**"]
    for idx, citation in filtered:
        source_type = citation.get("source", "unknown")
        formatted = format_citation_detail(citation, idx)
        lines.append(f"- {formatted}")

    return "\n".join(lines)


def format_citation_detail(citation: dict, index: int) -> str:
    """
    Format detailed citation for sources section.

    Args:
        citation: Citation dict
        index: Citation index

    Returns:
        Detailed formatted string
    """
    parts = [f"[{index}]"]

    if citation.get("filename"):
        parts.append(citation["filename"])

    if citation.get("page"):
        parts.append(f"(페이지 {citation['page']})")

    source_type = citation.get("source", "unknown")
    if source_type == "vector":
        parts.append("- 문서 검색")
    elif source_type == "graph":
        parts.append("- 지식 그래프")
        if citation.get("entity"):
            parts.append(f"[{citation['entity']}]")

    if citation.get("score"):
        score_pct = int(citation["score"] * 100)
        parts.append(f"(관련도: {score_pct}%)")

    return " ".join(parts)


def append_sources_to_response(
    response: str,
    citations: list[dict],
    include_unused: bool = False,
) -> str:
    """
    Append sources section to response if sources were used.

    Args:
        response: LLM response text
        citations: Available citations
        include_unused: Whether to include unused sources

    Returns:
        Response with sources section appended
    """
    if not citations:
        return response

    # Find which sources were referenced
    used_indices = extract_source_references(response)

    if not used_indices and not include_unused:
        # No sources referenced, return as is
        return response

    # Format response with proper citations
    formatted_response = format_sources_in_response(response, citations)

    # Build and append sources section
    if include_unused:
        sources_section = build_sources_section(citations)
    else:
        sources_section = build_sources_section(citations, used_indices)

    if sources_section:
        formatted_response += sources_section

    return formatted_response
