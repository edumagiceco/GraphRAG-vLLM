"""
Token counter utility for LLM responses.
Estimates token count based on text length with language-aware heuristics.
"""
import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage statistics."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


class TokenCounter:
    """
    Token counter for LLM responses.
    Uses estimation based on character count with language-aware heuristics.
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count for text.
        Uses approximation based on language characteristics:
        - Korean: ~2 characters per token (due to subword tokenization)
        - English/ASCII: ~4 characters per token

        Args:
            text: Input text to estimate tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Count Korean characters (Hangul syllables range)
        korean_chars = sum(1 for c in text if "\uac00" <= c <= "\ud7a3")
        # Count other characters (English, numbers, punctuation, etc.)
        other_chars = len(text) - korean_chars

        # Estimate tokens: Korean ~2 chars/token, Other ~4 chars/token
        estimated = (korean_chars / 2) + (other_chars / 4)

        return max(1, int(estimated))

    @staticmethod
    def extract_from_response(response: Any) -> Optional[TokenUsage]:
        """
        Try to extract token usage from LLM response metadata.
        Works with vLLM (OpenAI-compatible) and LangChain responses.

        Args:
            response: LLM response object

        Returns:
            TokenUsage if available, None otherwise
        """
        try:
            # Try LangChain response metadata (vLLM/OpenAI compatible)
            if hasattr(response, "response_metadata"):
                metadata = response.response_metadata
                usage = metadata.get("token_usage", {})
                if usage:
                    return TokenUsage(
                        input_tokens=usage.get("prompt_tokens", 0),
                        output_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                    )

            # Try usage_metadata (newer LangChain versions)
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                if usage:
                    return TokenUsage(
                        input_tokens=getattr(usage, "input_tokens", 0),
                        output_tokens=getattr(usage, "output_tokens", 0),
                        total_tokens=getattr(usage, "total_tokens", 0),
                    )

        except Exception as e:
            logger.debug(f"Failed to extract token usage from response: {e}")

        return None

    @staticmethod
    def calculate_usage(
        input_text: str,
        output_text: str,
        response: Any = None,
    ) -> TokenUsage:
        """
        Calculate token usage, preferring API response if available.

        Args:
            input_text: Input prompt text
            output_text: Generated output text
            response: Optional LLM response object to extract usage from

        Returns:
            TokenUsage with input and output token counts
        """
        # Try to extract from response first
        if response:
            usage = TokenCounter.extract_from_response(response)
            if usage and usage.total_tokens > 0:
                return usage

        # Fall back to estimation
        return TokenUsage(
            input_tokens=TokenCounter.estimate_tokens(input_text),
            output_tokens=TokenCounter.estimate_tokens(output_text),
        )
