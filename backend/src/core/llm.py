"""
Ollama LLM wrapper using LangChain ChatOllama.
Provides unified interface for chat completion with streaming support.
"""
from typing import AsyncIterator, Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from src.core.config import settings


class OllamaLLM:
    """
    Wrapper for Ollama LLM using LangChain's ChatOllama.
    Supports both synchronous and streaming chat completions.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        num_ctx: int = 4096,
    ):
        """
        Initialize the Ollama LLM wrapper.

        Args:
            model: Model name (default: from settings)
            base_url: Ollama server URL (default: from settings)
            temperature: Sampling temperature (0.0-1.0)
            num_ctx: Context window size
        """
        self.model = model or settings.ollama_model
        self.base_url = base_url or settings.ollama_base_url
        self.temperature = temperature
        self.num_ctx = num_ctx

        self._llm = ChatOllama(
            model=self.model,
            base_url=self.base_url,
            temperature=self.temperature,
            num_ctx=self.num_ctx,
        )

    def _build_messages(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> list:
        """
        Build message list for the LLM.

        Args:
            user_message: Current user message
            system_prompt: Optional system prompt
            chat_history: Optional list of previous messages

        Returns:
            List of LangChain message objects
        """
        messages = []

        # Add system prompt if provided
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        # Add chat history if provided
        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        # Add current user message
        messages.append(HumanMessage(content=user_message))

        return messages

    def generate_sync(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> str:
        """
        Generate a response synchronously (for Celery workers).

        Args:
            user_message: User's message
            system_prompt: Optional system prompt for persona
            chat_history: Optional conversation history

        Returns:
            Generated response text
        """
        messages = self._build_messages(user_message, system_prompt, chat_history)
        response = self._llm.invoke(messages)
        return response.content

    async def generate(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> str:
        """
        Generate a response (non-streaming).

        Args:
            user_message: User's message
            system_prompt: Optional system prompt for persona
            chat_history: Optional conversation history

        Returns:
            Generated response text
        """
        messages = self._build_messages(user_message, system_prompt, chat_history)
        response = await self._llm.ainvoke(messages)
        return response.content

    async def generate_stream(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        """
        Generate a response with streaming.

        Args:
            user_message: User's message
            system_prompt: Optional system prompt for persona
            chat_history: Optional conversation history

        Yields:
            Response text chunks as they are generated
        """
        messages = self._build_messages(user_message, system_prompt, chat_history)

        async for chunk in self._llm.astream(messages):
            if chunk.content:
                yield chunk.content

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[list[str]] = None,
    ) -> dict:
        """
        Extract entities from text for knowledge graph construction.

        Args:
            text: Input text to extract entities from
            entity_types: Types of entities to extract (default: Concept, Definition, Process)

        Returns:
            Dict containing extracted entities
        """
        if entity_types is None:
            entity_types = ["Concept", "Definition", "Process"]

        system_prompt = """You are an entity extraction assistant.
Extract entities and their relationships from the given text.
Return a JSON object with the following structure:
{
    "entities": [
        {"name": "entity name", "type": "entity type", "description": "brief description"}
    ],
    "relationships": [
        {"source": "entity1", "target": "entity2", "type": "relationship type"}
    ]
}
Only extract entities of types: """ + ", ".join(entity_types)

        response = await self.generate(
            user_message=f"Extract entities from the following text:\n\n{text}",
            system_prompt=system_prompt,
        )

        # Parse JSON response (basic parsing, will be enhanced)
        import json
        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return {"entities": [], "relationships": []}

    async def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        Generate a summary of the given text.

        Args:
            text: Text to summarize
            max_length: Maximum summary length in words

        Returns:
            Summary text
        """
        system_prompt = f"""You are a summarization assistant.
Summarize the given text concisely in no more than {max_length} words.
Focus on the key points and main ideas."""

        return await self.generate(
            user_message=f"Summarize the following text:\n\n{text}",
            system_prompt=system_prompt,
        )


# Singleton instance for convenience
_llm_instance: Optional[OllamaLLM] = None


def get_llm() -> OllamaLLM:
    """Get or create the singleton LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = OllamaLLM()
    return _llm_instance


async def check_ollama_connection() -> bool:
    """
    Check if Ollama server is reachable and model is available.

    Returns:
        True if connection is successful
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.ollama_base_url}/api/tags",
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return settings.ollama_model in models or any(
                    settings.ollama_model.split(":")[0] in m for m in models
                )
    except Exception:
        pass

    return False
