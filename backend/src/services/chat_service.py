"""
Chat service for managing conversations.
"""
import asyncio
import re
import time
import uuid
from datetime import datetime
from typing import AsyncIterator, Optional, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chatbot_service import ChatbotService, ChatbotStatus
from src.models.conversation import ConversationSession, Message, MessageRole
from src.services.retrieval.hybrid_retriever import retrieve_context
from src.services.llm.answer_generator import get_answer_generator
from src.core.config import settings


def clean_llm_response(text: str) -> str:
    """
    Clean LLM response by removing thinking/reasoning content.

    Removes:
    - <think>...</think> tags and their content
    - Content before </think> (thinking without opening tag)
    - Any remaining tags

    Args:
        text: Raw LLM response text

    Returns:
        Cleaned text with only the answer
    """
    if not text:
        return text

    # If there's a </think> tag, take only the content after it
    # This handles cases where model outputs thinking without <think> opening tag
    think_end_match = re.search(r'</think>\s*', text, flags=re.IGNORECASE)
    if think_end_match:
        text = text[think_end_match.end():]

    # Remove <think>...</think> blocks (including multiline)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Remove any remaining tags
    text = re.sub(r'</?think>\s*', '', text, flags=re.IGNORECASE)

    return text.strip()


class StreamingThinkFilter:
    """
    Real-time filter for streaming LLM responses.
    Filters out <think>...</think> content while streaming.
    """

    def __init__(self):
        self.buffer = ""
        self.in_think_mode = False
        self.full_response = ""  # Keep track of full response for final cleanup

    def process_chunk(self, chunk: str) -> str:
        """
        Process a streaming chunk and return filtered content.

        Args:
            chunk: Raw chunk from LLM

        Returns:
            Filtered chunk (empty string if in thinking mode)
        """
        self.full_response += chunk
        self.buffer += chunk
        output = ""

        while self.buffer:
            if self.in_think_mode:
                # Look for </think> to exit thinking mode
                end_match = re.search(r'</think>', self.buffer, flags=re.IGNORECASE)
                if end_match:
                    # Exit thinking mode, discard everything before </think>
                    self.buffer = self.buffer[end_match.end():]
                    self.in_think_mode = False
                elif len(self.buffer) > 20:
                    # Keep only last 20 chars to detect partial </think>
                    self.buffer = self.buffer[-20:]
                    break
                else:
                    break
            else:
                # Look for <think> to enter thinking mode
                start_match = re.search(r'<think>', self.buffer, flags=re.IGNORECASE)
                if start_match:
                    # Output content before <think>
                    output += self.buffer[:start_match.start()]
                    self.buffer = self.buffer[start_match.end():]
                    self.in_think_mode = True
                elif '<' in self.buffer:
                    # Might be start of a tag, keep it in buffer
                    idx = self.buffer.rfind('<')
                    if idx > 0:
                        output += self.buffer[:idx]
                        self.buffer = self.buffer[idx:]
                    # If partial tag detected, wait for more data
                    if len(self.buffer) < 10:
                        break
                    else:
                        # Not a think tag, output it
                        output += self.buffer
                        self.buffer = ""
                else:
                    # No tags, output everything
                    output += self.buffer
                    self.buffer = ""

        return output

    def flush(self) -> str:
        """
        Flush remaining buffer content.

        Returns:
            Any remaining filtered content
        """
        if self.in_think_mode:
            return ""
        output = self.buffer
        self.buffer = ""
        return output

    def get_clean_response(self) -> str:
        """
        Get the full cleaned response (for final verification).

        Returns:
            Complete cleaned response
        """
        return clean_llm_response(self.full_response)


def sanitize_for_postgres(data: Any) -> Any:
    """
    Sanitize data for PostgreSQL JSONB storage.
    Removes null characters (\u0000) which are not supported in PostgreSQL.

    Args:
        data: Any data structure (dict, list, str, etc.)

    Returns:
        Sanitized data
    """
    if data is None:
        return None

    if isinstance(data, str):
        # Remove null characters
        return data.replace('\x00', '').replace('\u0000', '')

    if isinstance(data, dict):
        return {k: sanitize_for_postgres(v) for k, v in data.items()}

    if isinstance(data, list):
        return [sanitize_for_postgres(item) for item in data]

    return data




class ChatService:
    """Service for managing chat sessions and messages."""

    @staticmethod
    async def get_chatbot_by_url(
        db: AsyncSession,
        access_url: str,
    ) -> Optional[ChatbotService]:
        """
        Get active chatbot by access URL.

        Args:
            db: Database session
            access_url: Public access URL

        Returns:
            Active chatbot or None
        """
        result = await db.execute(
            select(ChatbotService).where(
                ChatbotService.access_url == access_url,
                ChatbotService.status == ChatbotStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_session(
        db: AsyncSession,
        chatbot_id: str,
    ) -> ConversationSession:
        """
        Create a new chat session.

        Args:
            db: Database session
            chatbot_id: Chatbot ID

        Returns:
            Created session
        """
        session = ConversationSession(
            id=str(uuid.uuid4()),
            chatbot_id=chatbot_id,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_session(
        db: AsyncSession,
        session_id: str,
        chatbot_id: Optional[str] = None,
    ) -> Optional[ConversationSession]:
        """
        Get a chat session.

        Args:
            db: Database session
            session_id: Session ID
            chatbot_id: Optional chatbot ID to verify

        Returns:
            Session or None
        """
        query = select(ConversationSession).where(
            ConversationSession.id == session_id
        )
        if chatbot_id:
            query = query.where(ConversationSession.chatbot_id == chatbot_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_session_messages(
        db: AsyncSession,
        session_id: str,
        limit: int = 50,
    ) -> list[Message]:
        """
        Get messages for a session.

        Args:
            db: Database session
            session_id: Session ID
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_message(
        db: AsyncSession,
        session_id: str,
        role: MessageRole,
        content: str,
        sources: Optional[list[dict]] = None,
        # Performance metrics (for assistant messages)
        response_time_ms: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        retrieval_count: Optional[int] = None,
        retrieval_time_ms: Optional[int] = None,
    ) -> Message:
        """
        Add a message to a session with optional metrics.

        Args:
            db: Database session
            session_id: Session ID
            role: Message role
            content: Message content
            sources: Optional source citations
            response_time_ms: Response generation time in milliseconds
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            retrieval_count: Number of retrieved chunks
            retrieval_time_ms: Context retrieval time in milliseconds

        Returns:
            Created message
        """
        # Sanitize content and sources for PostgreSQL (remove null characters)
        sanitized_content = sanitize_for_postgres(content) if content else content
        sanitized_sources = sanitize_for_postgres(sources) if sources else sources

        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=sanitized_content,
            sources=sanitized_sources,
            response_time_ms=response_time_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            retrieval_count=retrieval_count,
            retrieval_time_ms=retrieval_time_ms,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_chat_history(
        db: AsyncSession,
        session_id: str,
        max_messages: int = 10,
    ) -> list[dict]:
        """
        Get chat history formatted for LLM.

        Args:
            db: Database session
            session_id: Session ID
            max_messages: Maximum messages to include

        Returns:
            List of message dicts
        """
        messages = await ChatService.get_session_messages(
            db, session_id, limit=max_messages
        )

        return [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in messages
        ]

    @staticmethod
    async def generate_response(
        db: AsyncSession,
        session_id: str,
        chatbot: ChatbotService,
        user_message: str,
    ) -> tuple[str, list[dict]]:
        """
        Generate a response to user message (non-streaming).

        Args:
            db: Database session
            session_id: Session ID
            chatbot: Chatbot service
            user_message: User's message

        Returns:
            Tuple of (response text, citations)
        """
        # Get chat history
        chat_history = await ChatService.get_chat_history(db, session_id)

        # Retrieve context
        retrieval_result = await retrieve_context(
            query=user_message,
            chatbot_id=chatbot.id,
            include_graph=True,
        )

        context = retrieval_result.get("context", "")
        citations = retrieval_result.get("citations", [])

        # Generate response
        generator = get_answer_generator()
        response = await generator.generate(
            user_message=user_message,
            context=context,
            persona=chatbot.persona,
            citations=citations,
            chat_history=chat_history,
        )

        return response, citations

    @staticmethod
    async def generate_response_stream(
        db: AsyncSession,
        session_id: str,
        chatbot: ChatbotService,
        user_message: str,
    ) -> AsyncIterator[dict]:
        """
        Generate a streaming response to user message.

        Args:
            db: Database session
            session_id: Session ID
            chatbot: Chatbot service
            user_message: User's message

        Yields:
            Stream chunks with type and content
        """
        from src.core.token_counter import TokenCounter

        # Record start time
        start_time = time.time()

        # Send thinking/reasoning start signal
        yield {"type": "thinking_status", "stage": "history", "message": "대화 기록 분석 중..."}
        await asyncio.sleep(0.01)  # Ensure flush to client

        # Get chat history
        chat_history = await ChatService.get_chat_history(db, session_id)

        # Send retrieval stage
        yield {"type": "thinking_status", "stage": "retrieval", "message": "관련 문서 검색 중..."}
        await asyncio.sleep(0.01)  # Ensure flush to client

        # Record retrieval start time
        retrieval_start_time = time.time()

        # Retrieve context
        retrieval_result = await retrieve_context(
            query=user_message,
            chatbot_id=chatbot.id,
            include_graph=True,
        )

        # Calculate retrieval time
        retrieval_time_ms = int((time.time() - retrieval_start_time) * 1000)

        context = retrieval_result.get("context", "")
        citations = retrieval_result.get("citations", [])
        vector_count = retrieval_result.get("vector_count", 0)
        graph_count = retrieval_result.get("graph_count", 0)
        retrieval_count = vector_count + graph_count

        # Check if we have relevant context
        no_relevant_context = vector_count == 0 or not context.strip()

        if no_relevant_context:
            # No relevant context found, return helpful message
            response = "죄송합니다. 업로드된 문서에서 해당 질문에 대한 관련 정보를 찾을 수 없습니다. 문서와 관련된 다른 질문이 있으시면 말씀해주세요."
            yield {"type": "content", "content": response}
            yield {"type": "sources", "sources": []}
            elapsed_time = round(time.time() - start_time, 2)
            yield {"type": "done", "content": response, "elapsed_time": elapsed_time, "model": "N/A (no retrieval)"}
            return

        # Send context found signal
        if citations:
            yield {
                "type": "thinking_status",
                "stage": "context_found",
                "message": f"{len(citations)}개의 관련 출처를 찾았습니다.",
                "source_count": len(citations)
            }
            await asyncio.sleep(0.01)  # Ensure flush to client

        # Send generating stage
        yield {"type": "thinking_status", "stage": "generating", "message": "답변 생성 중..."}
        await asyncio.sleep(0.01)  # Ensure flush to client

        # Real-time streaming with thinking content filter
        generator = get_answer_generator()
        think_filter = StreamingThinkFilter()
        streamed_content = ""

        try:
            # Stream response in real-time with thinking filter
            async for chunk in generator.generate_stream(
                user_message=user_message,
                context=context,
                persona=chatbot.persona,
                citations=citations,
                chat_history=chat_history,
            ):
                # Filter thinking content in real-time
                filtered_chunk = think_filter.process_chunk(chunk)
                if filtered_chunk:
                    streamed_content += filtered_chunk
                    yield {"type": "content", "content": filtered_chunk}

            # Flush any remaining content in buffer
            remaining = think_filter.flush()
            if remaining:
                streamed_content += remaining
                yield {"type": "content", "content": remaining}

            # Get the final cleaned response (for storage and verification)
            cleaned_response = think_filter.get_clean_response()

            # Send sources with detailed info
            if citations:
                enhanced_citations = []
                for citation in citations:
                    enhanced = dict(citation)
                    if "source" not in enhanced:
                        enhanced["source"] = "document" if enhanced.get("filename") else "graph"
                    enhanced_citations.append(enhanced)
                yield {"type": "sources", "sources": enhanced_citations}

            # Calculate elapsed time
            elapsed_time = round(time.time() - start_time, 2)
            response_time_ms = int(elapsed_time * 1000)

            # Get actual model from ModelManager (DB setting)
            from src.core.model_manager import ModelManager
            current_model = ModelManager.get_default_llm_model_sync()

            # Calculate token usage (estimation)
            # Build input text from system prompt, context, and user message
            input_text = f"{chatbot.persona.get('system_prompt', '')} {context} {user_message}"
            token_usage = TokenCounter.calculate_usage(
                input_text=input_text,
                output_text=cleaned_response,
            )

            # Build metrics object
            metrics = {
                "response_time_ms": response_time_ms,
                "input_tokens": token_usage.input_tokens,
                "output_tokens": token_usage.output_tokens,
                "retrieval_count": retrieval_count,
                "retrieval_time_ms": retrieval_time_ms,
            }

            # Send done signal with cleaned content, elapsed time, model info, and metrics
            yield {
                "type": "done",
                "content": cleaned_response,
                "elapsed_time": elapsed_time,
                "model": current_model,
                "metrics": metrics,
            }

        except Exception as e:
            yield {"type": "error", "error": str(e)}

    @staticmethod
    async def get_session_count(
        db: AsyncSession,
        chatbot_id: str,
    ) -> int:
        """
        Get total session count for a chatbot.

        Args:
            db: Database session
            chatbot_id: Chatbot ID

        Returns:
            Session count
        """
        result = await db.execute(
            select(func.count())
            .select_from(ConversationSession)
            .where(ConversationSession.chatbot_id == chatbot_id)
        )
        return result.scalar() or 0

    @staticmethod
    async def get_message_count(
        db: AsyncSession,
        session_id: str,
    ) -> int:
        """
        Get message count for a session.

        Args:
            db: Database session
            session_id: Session ID

        Returns:
            Message count
        """
        result = await db.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.session_id == session_id)
        )
        return result.scalar() or 0
