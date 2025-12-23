"""
Entity extraction service using rule-based and LLM approaches.
"""
import re
import json
from typing import Optional

from src.core.llm import get_llm


class EntityExtractor:
    """
    Entity extractor combining rule-based and LLM approaches.
    Extracts Concept, Definition, and Process entities.
    """

    # Entity types to extract
    ENTITY_TYPES = ["Concept", "Definition", "Process"]

    # Rule-based patterns for quick extraction
    PATTERNS = {
        "Definition": [
            r"(?P<term>[\w\s]+)(?:은|는|란|이란)\s+(?P<definition>[^.]+)[.입니다]",
            r"(?P<term>[\w\s]+)\s*[:：]\s*(?P<definition>[^.]+)",
            r"(?P<term>[\w\s]+)\s+is\s+(?:a|an|the)?\s*(?P<definition>[^.]+)\.",
            r"(?P<term>[\w\s]+)\s+refers to\s+(?P<definition>[^.]+)\.",
        ],
        "Process": [
            r"(?:단계|step|phase)\s*\d+[.:\s]+(?P<step>[^.]+)",
            r"(?:첫째|둘째|셋째|first|second|third)[,\s]+(?P<step>[^.]+)",
            r"(?:먼저|다음으로|마지막으로)[,\s]+(?P<step>[^.]+)",
        ],
    }

    def __init__(self, use_llm: bool = True):
        """
        Initialize entity extractor.

        Args:
            use_llm: Whether to use LLM for extraction
        """
        self.use_llm = use_llm
        self._llm = get_llm() if use_llm else None

    def extract_with_rules(self, text: str) -> list[dict]:
        """
        Extract entities using rule-based patterns.

        Args:
            text: Input text

        Returns:
            List of extracted entities
        """
        entities = []

        # Extract definitions
        for pattern in self.PATTERNS["Definition"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                term = match.group("term").strip()
                definition = match.group("definition").strip()
                if term and definition and len(term) > 2:
                    entities.append({
                        "name": term,
                        "type": "Definition",
                        "description": definition[:500],
                    })

        # Extract process steps
        for pattern in self.PATTERNS["Process"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                step = match.group("step").strip()
                if step and len(step) > 5:
                    entities.append({
                        "name": step[:100],
                        "type": "Process",
                        "description": step,
                    })

        return entities

    def extract_with_llm(self, text: str, max_length: int = 3000) -> list[dict]:
        """
        Extract entities using LLM.

        Args:
            text: Input text
            max_length: Max text length to process

        Returns:
            List of extracted entities
        """
        if not self._llm:
            return []

        # Truncate text if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."

        system_prompt = """You are an entity extraction assistant for building knowledge graphs.
Extract entities from the given text and return them as a JSON array.

Entity types to extract:
- Concept: Key terms, topics, or ideas
- Definition: Terms with their definitions/explanations
- Process: Steps, procedures, or workflows

Return format:
[
    {"name": "entity name", "type": "entity type", "description": "brief description"}
]

Rules:
- Extract 5-15 most important entities
- Names should be concise (1-5 words)
- Descriptions should be brief but informative (1-2 sentences)
- Only return valid JSON array, no other text
- Do NOT include any text before or after the JSON array"""

        try:
            # Use sync version for Celery compatibility (avoids event loop issues)
            response = self._llm.generate_sync(
                user_message=f"Extract entities from:\n\n{text}",
                system_prompt=system_prompt,
            )

            # Parse JSON from response - handle multiple JSON arrays
            entities = self._parse_json_array(response)

            # Validate and clean entities
            valid_entities = []
            for entity in entities:
                if isinstance(entity, dict) and "name" in entity:
                    valid_entities.append({
                        "name": str(entity.get("name", ""))[:100],
                        "type": entity.get("type", "Concept"),
                        "description": str(entity.get("description", ""))[:500],
                    })
            return valid_entities
        except Exception as e:
            print(f"LLM entity extraction error: {e}")

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
            import re
            objects = re.findall(r'\{[^{}]*\}', json_str)
            if objects:
                return [json.loads(obj) for obj in objects]
        except (json.JSONDecodeError, Exception):
            pass

        return []

    def extract(self, text: str) -> list[dict]:
        """
        Extract entities using both rule-based and LLM approaches.

        Args:
            text: Input text

        Returns:
            List of unique extracted entities
        """
        entities = []

        # Rule-based extraction (fast)
        rule_entities = self.extract_with_rules(text)
        entities.extend(rule_entities)

        # LLM extraction (comprehensive)
        if self.use_llm:
            llm_entities = self.extract_with_llm(text)
            entities.extend(llm_entities)

        # Deduplicate by name (case-insensitive)
        seen_names = set()
        unique_entities = []
        for entity in entities:
            name_lower = entity["name"].lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_entities.append(entity)

        return unique_entities


def extract_entities(text: str, use_llm: bool = True) -> list[dict]:
    """
    Convenience function to extract entities.

    Args:
        text: Input text
        use_llm: Whether to use LLM

    Returns:
        List of extracted entities
    """
    extractor = EntityExtractor(use_llm=use_llm)
    return extractor.extract(text)
