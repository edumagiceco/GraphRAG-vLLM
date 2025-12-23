"""
Relationship extraction service for knowledge graph construction.
"""
import re
import json
from typing import Optional

import requests

from src.core.config import settings


class RelationExtractor:
    """
    Relationship extractor for building knowledge graph edges.
    Extracts relationships between entities.
    """

    # Relationship types
    RELATION_TYPES = [
        "RELATED_TO",      # General relationship
        "DEFINES",         # Definition relationship
        "PART_OF",         # Hierarchical relationship
        "FOLLOWS",         # Sequential relationship (process steps)
        "DEPENDS_ON",      # Dependency relationship
        "EXAMPLE_OF",      # Instance relationship
        "SIMILAR_TO",      # Similarity relationship
    ]

    # Rule-based patterns for relationship extraction
    PATTERNS = {
        "DEFINES": [
            r"(?P<source>[\w\s]+)(?:은|는|이)\s+(?P<target>[\w\s]+)(?:을|를)?\s*(?:정의|설명|의미)",
            r"(?P<source>[\w\s]+)\s+defines?\s+(?P<target>[\w\s]+)",
        ],
        "PART_OF": [
            r"(?P<source>[\w\s]+)(?:은|는|이)\s+(?P<target>[\w\s]+)(?:의|에)\s*(?:일부|부분|포함)",
            r"(?P<source>[\w\s]+)\s+is\s+part\s+of\s+(?P<target>[\w\s]+)",
            r"(?P<source>[\w\s]+)\s+belongs?\s+to\s+(?P<target>[\w\s]+)",
        ],
        "FOLLOWS": [
            r"(?P<source>[\w\s]+)\s+(?:다음|후|이후)(?:에|로)?\s+(?P<target>[\w\s]+)",
            r"(?P<source>[\w\s]+)\s+(?:follows?|after)\s+(?P<target>[\w\s]+)",
            r"(?P<target>[\w\s]+)\s+(?:before|precedes?)\s+(?P<source>[\w\s]+)",
        ],
        "DEPENDS_ON": [
            r"(?P<source>[\w\s]+)(?:은|는|이)\s+(?P<target>[\w\s]+)(?:에|을|를)?\s*(?:의존|필요|기반)",
            r"(?P<source>[\w\s]+)\s+(?:depends?\s+on|requires?)\s+(?P<target>[\w\s]+)",
        ],
    }

    def __init__(self, use_llm: bool = True):
        """
        Initialize relationship extractor.

        Args:
            use_llm: Whether to use LLM for extraction
        """
        self.use_llm = use_llm
        self._ollama_url = f"{settings.ollama_base_url}/api/chat"
        self._model = settings.ollama_model

    def extract_with_rules(
        self,
        text: str,
        entities: list[dict],
    ) -> list[dict]:
        """
        Extract relationships using rule-based patterns.

        Args:
            text: Input text
            entities: List of extracted entities

        Returns:
            List of relationships
        """
        relationships = []
        entity_names = {e["name"].lower() for e in entities}

        for rel_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    source = match.group("source").strip()
                    target = match.group("target").strip()

                    # Validate entities exist
                    if (
                        source.lower() in entity_names
                        and target.lower() in entity_names
                        and source.lower() != target.lower()
                    ):
                        relationships.append({
                            "source": source,
                            "target": target,
                            "type": rel_type,
                        })

        return relationships

    def extract_with_llm(
        self,
        text: str,
        entities: list[dict],
        max_length: int = 3000,
    ) -> list[dict]:
        """
        Extract relationships using LLM via direct HTTP call to Ollama.

        Args:
            text: Input text
            entities: List of extracted entities
            max_length: Max text length

        Returns:
            List of relationships
        """
        if not self.use_llm or not entities:
            return []

        # Truncate text if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."

        # Prepare entity list for prompt
        entity_names = [e["name"] for e in entities[:30]]  # Limit to 30 entities
        entity_list = ", ".join(entity_names)

        system_prompt = f"""You are a relationship extraction assistant for building knowledge graphs.
Extract relationships between entities from the given text.

Available entities: {entity_list}

Relationship types:
- RELATED_TO: General relationship
- DEFINES: Definition relationship
- PART_OF: Hierarchical relationship
- FOLLOWS: Sequential relationship
- DEPENDS_ON: Dependency relationship
- EXAMPLE_OF: Instance relationship
- SIMILAR_TO: Similarity relationship

Return format (JSON array):
[
    {{"source": "entity1", "target": "entity2", "type": "RELATIONSHIP_TYPE"}}
]

Rules:
- Only use entities from the provided list
- Extract 5-20 most important relationships
- Source and target must be different entities
- Only return valid JSON array, no other text
- Do NOT include any text before or after the JSON array"""

        try:
            # Direct HTTP call to Ollama API (avoids event loop issues in Celery)
            payload = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract relationships from:\n\n{text}"},
                ],
                "stream": False,
            }

            response = requests.post(
                self._ollama_url,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()

            result = response.json()
            response_text = result.get("message", {}).get("content", "")

            # Parse JSON from response - handle malformed responses
            relationships = self._parse_json_array(response_text)

            # Validate relationships
            valid_relationships = []
            entity_names_set = {e["name"].lower() for e in entities}

            for rel in relationships:
                if isinstance(rel, dict):
                    source = str(rel.get("source", ""))
                    target = str(rel.get("target", ""))
                    rel_type = str(rel.get("type", "RELATED_TO"))

                    if (
                        source.lower() in entity_names_set
                        and target.lower() in entity_names_set
                        and source.lower() != target.lower()
                        and rel_type in self.RELATION_TYPES
                    ):
                        valid_relationships.append({
                            "source": source,
                            "target": target,
                            "type": rel_type,
                        })

            return valid_relationships
        except Exception as e:
            print(f"LLM relationship extraction error: {e}")

        return []

    def _parse_json_array(self, response: str) -> list:
        """
        Parse JSON array from LLM response, handling malformed responses.

        Args:
            response: LLM response text

        Returns:
            Parsed list or empty list on failure
        """
        # Find the first JSON array
        start = response.find("[")
        end = response.rfind("]") + 1

        if start < 0 or end <= start:
            return []

        json_str = response[start:end]

        # Try direct parsing first
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Try to fix common issues: multiple JSON arrays concatenated
        # Find the first complete array by counting brackets
        bracket_count = 0
        first_array_end = -1
        for i, char in enumerate(json_str):
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    first_array_end = i + 1
                    break

        if first_array_end > 0:
            try:
                return json.loads(json_str[:first_array_end])
            except json.JSONDecodeError:
                pass

        # Try to extract individual objects and build array
        try:
            objects = re.findall(r'\{[^{}]*\}', json_str)
            if objects:
                return [json.loads(obj) for obj in objects]
        except (json.JSONDecodeError, Exception):
            pass

        return []

    def extract(
        self,
        text: str,
        entities: list[dict],
    ) -> list[dict]:
        """
        Extract relationships using both rule-based and LLM approaches.

        Args:
            text: Input text
            entities: List of extracted entities

        Returns:
            List of unique relationships
        """
        relationships = []

        # Rule-based extraction
        rule_rels = self.extract_with_rules(text, entities)
        relationships.extend(rule_rels)

        # LLM extraction
        if self.use_llm:
            llm_rels = self.extract_with_llm(text, entities)
            relationships.extend(llm_rels)

        # Deduplicate
        seen = set()
        unique_rels = []
        for rel in relationships:
            key = (rel["source"].lower(), rel["target"].lower(), rel["type"])
            if key not in seen:
                seen.add(key)
                unique_rels.append(rel)

        return unique_rels


def extract_relationships(
    text: str,
    entities: list[dict],
    use_llm: bool = True,
) -> list[dict]:
    """
    Convenience function to extract relationships.

    Args:
        text: Input text
        entities: List of extracted entities
        use_llm: Whether to use LLM

    Returns:
        List of relationships
    """
    extractor = RelationExtractor(use_llm=use_llm)
    return extractor.extract(text, entities)
