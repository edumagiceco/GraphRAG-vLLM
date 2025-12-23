"""
Answer generator using Ollama LLM.
Supports both streaming and non-streaming responses.
"""
from typing import AsyncIterator, Optional

from src.core.llm import get_llm, OllamaLLM
from src.services.llm.prompt_builder import build_chat_prompt
from src.services.llm.source_formatter import format_sources_in_response


class AnswerGenerator:
    """
    Generator for chat answers using Ollama LLM.
    Supports streaming responses with source citation formatting.
    """

    def __init__(self, llm: Optional[OllamaLLM] = None):
        """
        Initialize answer generator.

        Args:
            llm: Optional LLM instance
        """
        self._llm = llm or get_llm()

    async def generate(
        self,
        user_message: str,
        context: str,
        persona: Optional[dict] = None,
        citations: Optional[list[dict]] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> str:
        """
        Generate a complete answer (non-streaming).

        Args:
            user_message: User's question
            context: Retrieved context
            persona: Optional persona configuration
            citations: Source citations
            chat_history: Conversation history

        Returns:
            Generated answer text
        """
        system_prompt, messages = build_chat_prompt(
            user_message=user_message,
            context=context,
            persona=persona,
            citations=citations,
            chat_history=chat_history,
        )

        # Get the last user message (with context)
        full_message = messages[-1]["content"] if messages else user_message

        # Generate response
        response = await self._llm.generate(
            user_message=full_message,
            system_prompt=system_prompt,
            chat_history=messages[:-1] if len(messages) > 1 else None,
        )

        # Format sources in response
        if citations:
            response = format_sources_in_response(response, citations)

        return response

    async def generate_stream(
        self,
        user_message: str,
        context: str,
        persona: Optional[dict] = None,
        citations: Optional[list[dict]] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        """
        Generate answer with streaming.

        Args:
            user_message: User's question
            context: Retrieved context
            persona: Optional persona configuration
            citations: Source citations
            chat_history: Conversation history

        Yields:
            Answer text chunks as they are generated
        """
        system_prompt, messages = build_chat_prompt(
            user_message=user_message,
            context=context,
            persona=persona,
            citations=citations,
            chat_history=chat_history,
        )

        # Get the last user message (with context)
        full_message = messages[-1]["content"] if messages else user_message

        # Stream response
        async for chunk in self._llm.generate_stream(
            user_message=full_message,
            system_prompt=system_prompt,
            chat_history=messages[:-1] if len(messages) > 1 else None,
        ):
            yield chunk

    async def generate_with_retrieval(
        self,
        user_message: str,
        chatbot_id: str,
        persona: Optional[dict] = None,
        chat_history: Optional[list[dict]] = None,
        stream: bool = True,
    ):
        """
        Generate answer with automatic context retrieval.

        Args:
            user_message: User's question
            chatbot_id: Chatbot ID for retrieval
            persona: Optional persona configuration
            chat_history: Conversation history
            stream: Whether to stream response

        Returns/Yields:
            Generated answer (string or async iterator)
        """
        # Retrieve context
        from src.services.retrieval.hybrid_retriever import retrieve_context

        retrieval_result = await retrieve_context(
            query=user_message,
            chatbot_id=chatbot_id,
            include_graph=True,
        )

        context = retrieval_result.get("context", "")
        citations = retrieval_result.get("citations", [])

        if stream:
            return self.generate_stream(
                user_message=user_message,
                context=context,
                persona=persona,
                citations=citations,
                chat_history=chat_history,
            )
        else:
            return await self.generate(
                user_message=user_message,
                context=context,
                persona=persona,
                citations=citations,
                chat_history=chat_history,
            )


# Singleton instance
_generator_instance: Optional[AnswerGenerator] = None


def get_answer_generator() -> AnswerGenerator:
    """Get or create singleton answer generator."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = AnswerGenerator()
    return _generator_instance


async def generate_answer(
    user_message: str,
    context: str,
    persona: Optional[dict] = None,
    citations: Optional[list[dict]] = None,
    chat_history: Optional[list[dict]] = None,
) -> str:
    """
    Convenience function to generate an answer.

    Args:
        user_message: User's question
        context: Retrieved context
        persona: Optional persona
        citations: Source citations
        chat_history: Conversation history

    Returns:
        Generated answer
    """
    generator = get_answer_generator()
    return await generator.generate(
        user_message=user_message,
        context=context,
        persona=persona,
        citations=citations,
        chat_history=chat_history,
    )


async def generate_answer_stream(
    user_message: str,
    context: str,
    persona: Optional[dict] = None,
    citations: Optional[list[dict]] = None,
    chat_history: Optional[list[dict]] = None,
) -> AsyncIterator[str]:
    """
    Convenience function to generate a streaming answer.

    Args:
        user_message: User's question
        context: Retrieved context
        persona: Optional persona
        citations: Source citations
        chat_history: Conversation history

    Yields:
        Answer text chunks
    """
    generator = get_answer_generator()
    async for chunk in generator.generate_stream(
        user_message=user_message,
        context=context,
        persona=persona,
        citations=citations,
        chat_history=chat_history,
    ):
        yield chunk
