"""
Relationship extraction service for knowledge graph construction.
"""
import logging
import re
import json
from typing import Optional

from src.core.config import settings

logger = logging.getLogger(__name__)


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

    def __init__(self, use_llm: bool = True, model: Optional[str] = None):
        """
        Initialize relationship extractor.

        Args:
            use_llm: Whether to use LLM for extraction
            model: Optional model override. If None, uses default from settings/database.
        """
        self.use_llm = use_llm
        self._model = model
        self._llm = None

    def _get_llm(self):
        """Get or create the LLM instance."""
        if self._llm is None:
            from src.core.llm import get_llm
            self._llm = get_llm(model=self._model)
        return self._llm

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
        Extract relationships using LLM.

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

CRITICAL Rules:
- ONLY use entity names from the "Available entities" list above
- Do NOT use article numbers (제1조, 제2조, Article 1, etc.) as source or target
- Do NOT use section numbers, clause numbers, or any numbered references
- Source and target MUST be actual entity names from the list
- Extract 5-20 most important relationships between the listed entities
- Source and target must be different entities
- Only return valid JSON array, no other text
- Do NOT include any text before or after the JSON array
- IMPORTANT: Use entity names exactly as provided in the entity list. Do NOT translate names to other languages."""

        try:
            llm = self._get_llm()
            logger.info(f"Relationship extraction using backend={settings.llm_backend}, model={llm.model}")

            response_text = llm.generate_sync(
                user_message=f"Extract relationships from:\n\n{text}",
                system_prompt=system_prompt,
            )

            # Parse JSON from response - handle malformed responses
            relationships = self._parse_json_array(response_text)

            # Log parsed relationships for debugging
            logger.debug(f"Parsed relationships: {relationships}")
            logger.debug(f"Available entities: {[e['name'] for e in entities]}")

            # Validate relationships with improved fuzzy matching
            valid_relationships = []
            entity_names_lower = {e["name"].lower(): e["name"] for e in entities}

            def normalize_name(name: str) -> str:
                """Normalize entity name for matching."""
                # Remove extra spaces, convert to lowercase
                return " ".join(name.lower().strip().split())

            def get_words(name: str) -> set:
                """Get set of words from name."""
                return set(normalize_name(name).split())

            def find_matching_entity(name: str) -> Optional[str]:
                """Find matching entity name with improved fuzzy matching."""
                if not name:
                    return None

                name_normalized = normalize_name(name)
                name_words = get_words(name)

                # 1. Exact match (normalized)
                for entity_lower, entity_original in entity_names_lower.items():
                    if name_normalized == normalize_name(entity_lower):
                        return entity_original

                # 2. Partial match - entity contains the name or vice versa
                for entity_lower, entity_original in entity_names_lower.items():
                    entity_normalized = normalize_name(entity_lower)
                    if name_normalized in entity_normalized or entity_normalized in name_normalized:
                        return entity_original

                # 3. Word overlap matching - if significant word overlap exists
                best_match = None
                best_overlap = 0
                for entity_lower, entity_original in entity_names_lower.items():
                    entity_words = get_words(entity_lower)
                    overlap = len(name_words & entity_words)
                    # Require at least 1 word overlap and > 50% match
                    min_len = min(len(name_words), len(entity_words))
                    if overlap > 0 and overlap >= min_len * 0.5:
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_match = entity_original

                if best_match:
                    return best_match

                # 4. Check if any word in the name matches any entity exactly
                for word in name_words:
                    if len(word) > 2:  # Skip short words
                        for entity_lower, entity_original in entity_names_lower.items():
                            if word == normalize_name(entity_lower):
                                return entity_original

                return None

            unmatched_sources = []
            unmatched_targets = []

            for rel in relationships:
                if isinstance(rel, dict):
                    source = str(rel.get("source", ""))
                    target = str(rel.get("target", ""))
                    rel_type = str(rel.get("type", "RELATED_TO")).upper()

                    # Normalize relationship type
                    if rel_type not in self.RELATION_TYPES:
                        rel_type = "RELATED_TO"

                    # Find matching entities
                    matched_source = find_matching_entity(source)
                    matched_target = find_matching_entity(target)

                    if not matched_source:
                        unmatched_sources.append(source)
                    if not matched_target:
                        unmatched_targets.append(target)

                    if (
                        matched_source
                        and matched_target
                        and matched_source.lower() != matched_target.lower()
                    ):
                        valid_relationships.append({
                            "source": matched_source,
                            "target": matched_target,
                            "type": rel_type,
                        })

            if unmatched_sources or unmatched_targets:
                logger.warning(f"Unmatched sources: {unmatched_sources[:5]}, targets: {unmatched_targets[:5]}")

            logger.info(f"LLM returned {len(relationships)} relationships, {len(valid_relationships)} valid after matching")
            return valid_relationships
        except Exception as e:
            logger.error(f"LLM relationship extraction error: {e}")

        return []

    def _parse_json_array(self, response: str) -> list:
        """
        Parse JSON array from LLM response, handling malformed responses.

        Args:
            response: LLM response text

        Returns:
            Parsed list or empty list on failure
        """
        if not response:
            return []

        # Remove thinking tags (common in some models like phi4-mini, qwen)
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
        if '</think>' in cleaned.lower():
            think_end = cleaned.lower().rfind('</think>')
            cleaned = cleaned[think_end + 8:]

        # Remove markdown code blocks (```json ... ``` or ``` ... ```)
        cleaned = re.sub(r'```json\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = cleaned.strip()

        # Find the first JSON array
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1

        if start < 0 or end <= start:
            return []

        json_str = cleaned[start:end]

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
