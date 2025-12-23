"""
Chat service for managing conversations.
"""
import uuid
from datetime import datetime
from typing import AsyncIterator, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chatbot_service import ChatbotService, ChatbotStatus
from src.models.conversation import ConversationSession, Message, MessageRole
from src.services.retrieval.hybrid_retriever import retrieve_context
from src.services.llm.answer_generator import get_answer_generator


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
    ) -> Message:
        """
        Add a message to a session.

        Args:
            db: Database session
            session_id: Session ID
            role: Message role
            content: Message content
            sources: Optional source citations

        Returns:
            Created message
        """
        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            sources=sources,
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

        # Stream response
        generator = get_answer_generator()
        full_response = ""

        try:
            async for chunk in generator.generate_stream(
                user_message=user_message,
                context=context,
                persona=chatbot.persona,
                citations=citations,
                chat_history=chat_history,
            ):
                full_response += chunk
                yield {"type": "content", "content": chunk}

            # Send sources
            if citations:
                yield {"type": "sources", "sources": citations}

            # Send done signal
            yield {"type": "done", "content": full_response}

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
