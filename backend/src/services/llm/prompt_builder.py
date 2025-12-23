"""
Prompt builder for LLM interactions.
Constructs prompts with persona, context, and conversation history.
"""
from typing import Optional


class PromptBuilder:
    """
    Builder for constructing LLM prompts with:
    - Persona/system prompts
    - Retrieved context
    - Conversation history
    - Source citation instructions
    """

    DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on the provided context.

Guidelines:
1. Only answer based on the provided context
2. If the context doesn't contain enough information, say so honestly
3. Cite your sources using [Source: filename, page X] format when possible
4. Be concise but complete in your answers
5. Maintain a professional and helpful tone"""

    DEFAULT_GREETING = "안녕하세요! 무엇을 도와드릴까요?"

    def __init__(
        self,
        persona_name: Optional[str] = None,
        persona_description: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
        greeting: Optional[str] = None,
    ):
        """
        Initialize prompt builder.

        Args:
            persona_name: Chatbot persona name
            persona_description: Persona description
            custom_system_prompt: Custom system prompt (overrides default)
            greeting: Custom greeting message
        """
        self.persona_name = persona_name
        self.persona_description = persona_description
        self.custom_system_prompt = custom_system_prompt
        self.greeting = greeting or self.DEFAULT_GREETING

    def build_system_prompt(self) -> str:
        """
        Build the system prompt with persona.

        Returns:
            Complete system prompt
        """
        if self.custom_system_prompt:
            base_prompt = self.custom_system_prompt
        else:
            base_prompt = self.DEFAULT_SYSTEM_PROMPT

        if self.persona_name or self.persona_description:
            persona_section = "\n\nYour persona:"
            if self.persona_name:
                persona_section += f"\nName: {self.persona_name}"
            if self.persona_description:
                persona_section += f"\nDescription: {self.persona_description}"
            return base_prompt + persona_section

        return base_prompt

    def build_context_prompt(
        self,
        context: str,
        citations: Optional[list[dict]] = None,
    ) -> str:
        """
        Build the context section of the prompt.

        Args:
            context: Retrieved context text
            citations: Source citations

        Returns:
            Formatted context section
        """
        if not context:
            return "No relevant context found for this question."

        context_prompt = f"""## Retrieved Context

{context}

"""
        if citations:
            context_prompt += "## Available Sources\n"
            for i, citation in enumerate(citations, 1):
                source_info = []
                if citation.get("filename"):
                    source_info.append(citation["filename"])
                if citation.get("page"):
                    source_info.append(f"page {citation['page']}")
                if citation.get("entity"):
                    source_info.append(f"entity: {citation['entity']}")

                if source_info:
                    context_prompt += f"[{i}] {', '.join(source_info)}\n"

        return context_prompt

    def build_conversation_context(
        self,
        chat_history: Optional[list[dict]] = None,
        max_messages: int = 10,
    ) -> list[dict]:
        """
        Build conversation history for the prompt.

        Args:
            chat_history: List of previous messages
            max_messages: Maximum messages to include

        Returns:
            Formatted chat history
        """
        if not chat_history:
            return []

        # Limit to recent messages
        recent_history = chat_history[-max_messages:]

        return [
            {
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            }
            for msg in recent_history
        ]

    def build_full_prompt(
        self,
        user_message: str,
        context: str,
        citations: Optional[list[dict]] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> tuple[str, list[dict]]:
        """
        Build the complete prompt for LLM.

        Args:
            user_message: Current user message
            context: Retrieved context
            citations: Source citations
            chat_history: Conversation history

        Returns:
            Tuple of (system_prompt, messages)
        """
        system_prompt = self.build_system_prompt()
        context_section = self.build_context_prompt(context, citations)
        history = self.build_conversation_context(chat_history)

        # Combine context with user message
        full_user_message = f"""{context_section}

## User Question
{user_message}

Please answer the question based on the context above. If citing sources, use the format [Source: X] where X is the source number."""

        # Build message list
        messages = history + [{"role": "user", "content": full_user_message}]

        return system_prompt, messages

    @classmethod
    def from_persona_config(cls, persona: dict) -> "PromptBuilder":
        """
        Create builder from persona configuration dict.

        Args:
            persona: Persona config dict

        Returns:
            PromptBuilder instance
        """
        return cls(
            persona_name=persona.get("name"),
            persona_description=persona.get("description"),
            custom_system_prompt=persona.get("system_prompt"),
            greeting=persona.get("greeting"),
        )


def build_chat_prompt(
    user_message: str,
    context: str,
    persona: Optional[dict] = None,
    citations: Optional[list[dict]] = None,
    chat_history: Optional[list[dict]] = None,
) -> tuple[str, list[dict]]:
    """
    Convenience function to build a chat prompt.

    Args:
        user_message: User's question
        context: Retrieved context
        persona: Optional persona config
        citations: Optional source citations
        chat_history: Optional conversation history

    Returns:
        Tuple of (system_prompt, messages)
    """
    if persona:
        builder = PromptBuilder.from_persona_config(persona)
    else:
        builder = PromptBuilder()

    return builder.build_full_prompt(
        user_message=user_message,
        context=context,
        citations=citations,
        chat_history=chat_history,
    )
