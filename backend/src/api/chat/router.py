"""
Public chat API router.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.chat.schemas import (
    SendMessageRequest,
    MessageResponse,
    SessionResponse,
    SessionDetailResponse,
    CreateSessionRequest,
    ChatbotPublicInfo,
    MessageRole,
)
from src.services.chat_service import ChatService
from src.services.stats_service import StatsService
from src.models.conversation import MessageRole as DBMessageRole
from src.core.redis import RedisClient

router = APIRouter()


async def get_active_chatbot(
    access_url: str,
    db: AsyncSession = Depends(get_db),
):
    """Dependency to get active chatbot by URL."""
    chatbot = await ChatService.get_chatbot_by_url(db, access_url)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found or not active",
        )
    return chatbot


@router.get("/{access_url}", response_model=ChatbotPublicInfo)
async def get_chatbot_info(
    access_url: str,
    db: AsyncSession = Depends(get_db),
) -> ChatbotPublicInfo:
    """
    Get public chatbot information.

    Args:
        access_url: Chatbot access URL
        db: Database session

    Returns:
        Public chatbot info
    """
    chatbot = await get_active_chatbot(access_url, db)

    persona = chatbot.persona or {}
    return ChatbotPublicInfo(
        name=chatbot.name,
        persona_name=persona.get("name", chatbot.name),
        greeting=persona.get("greeting", "안녕하세요! 무엇을 도와드릴까요?"),
    )


@router.post("/{access_url}/sessions", response_model=SessionResponse)
async def create_session(
    access_url: str,
    request: CreateSessionRequest = None,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """
    Create a new chat session.

    If initial_message is provided, automatically generates a response.

    Args:
        access_url: Chatbot access URL
        request: Optional session creation request with initial message
        db: Database session

    Returns:
        Created session info with optional initial response
    """
    chatbot = await get_active_chatbot(access_url, db)

    session = await ChatService.create_session(
        db=db,
        chatbot_id=chatbot.id,
    )

    initial_response = None
    message_count = 0

    # Process initial message if provided
    if request and request.initial_message:
        # Save user message
        await ChatService.add_message(
            db=db,
            session_id=session.id,
            role=DBMessageRole.USER,
            content=request.initial_message,
        )
        message_count += 1

        # Update daily message count for user message
        await StatsService.increment_message_count(db, chatbot.id, count=1)

        # Generate response (non-streaming for session creation)
        response_text, citations, metrics = await ChatService.generate_response(
            db=db,
            session_id=session.id,
            chatbot=chatbot,
            user_message=request.initial_message,
        )

        # Save assistant message with metrics
        assistant_message = await ChatService.add_message(
            db=db,
            session_id=session.id,
            role=DBMessageRole.ASSISTANT,
            content=response_text,
            sources=citations,
            response_time_ms=metrics.get("response_time_ms"),
            input_tokens=metrics.get("input_tokens"),
            output_tokens=metrics.get("output_tokens"),
            retrieval_count=metrics.get("retrieval_count"),
            retrieval_time_ms=metrics.get("retrieval_time_ms"),
        )
        message_count += 1

        # Update daily message count for assistant message
        await StatsService.increment_message_count(db, chatbot.id, count=1)

        # Build initial response
        initial_response = MessageResponse(
            id=assistant_message.id,
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
            sources=citations,
            created_at=assistant_message.created_at,
        )

    return SessionResponse(
        id=session.id,
        chatbot_id=session.chatbot_id,
        started_at=session.created_at,
        message_count=message_count,
        initial_response=initial_response,
    )


@router.get("/{access_url}/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    access_url: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionDetailResponse:
    """
    Get session details with messages.

    Args:
        access_url: Chatbot access URL
        session_id: Session ID
        db: Database session

    Returns:
        Session details with messages
    """
    chatbot = await get_active_chatbot(access_url, db)

    session = await ChatService.get_session(
        db=db,
        session_id=session_id,
        chatbot_id=chatbot.id,
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    messages = await ChatService.get_session_messages(db, session_id)
    message_count = len(messages)

    return SessionDetailResponse(
        id=session.id,
        chatbot_id=session.chatbot_id,
        started_at=session.created_at,
        message_count=message_count,
        messages=[
            MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=MessageRole(msg.role.value),
                content=msg.content,
                sources=msg.sources,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )


@router.post("/{access_url}/sessions/{session_id}/messages")
async def send_message(
    access_url: str,
    session_id: str,
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and get response.

    Args:
        access_url: Chatbot access URL
        session_id: Session ID
        request: Message request
        db: Database session

    Returns:
        Response message or SSE stream
    """
    chatbot = await get_active_chatbot(access_url, db)

    session = await ChatService.get_session(
        db=db,
        session_id=session_id,
        chatbot_id=chatbot.id,
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Save user message
    user_message = await ChatService.add_message(
        db=db,
        session_id=session_id,
        role=DBMessageRole.USER,
        content=request.content,
    )

    # Update daily message count for user message
    await StatsService.increment_message_count(db, chatbot.id, count=1)

    if request.stream:
        # Return SSE stream
        async def generate_sse():
            import json

            full_response = ""
            citations = []

            try:
                async for chunk in ChatService.generate_response_stream(
                    db=db,
                    session_id=session_id,
                    chatbot=chatbot,
                    user_message=request.content,
                ):
                    chunk_type = chunk.get("type")

                    if chunk_type == "thinking_status":
                        # Send processing status updates (검색 중, 생성 중 등)
                        yield f"data: {json.dumps(chunk)}\n\n"

                    elif chunk_type == "content":
                        full_response += chunk.get("content", "")
                        yield f"data: {json.dumps(chunk)}\n\n"

                    elif chunk_type == "sources":
                        citations = chunk.get("sources", [])
                        yield f"data: {json.dumps(chunk)}\n\n"

                    elif chunk_type == "done":
                        # Extract metrics from the chunk
                        metrics = chunk.get("metrics", {})

                        # Save assistant message with metrics
                        assistant_message = await ChatService.add_message(
                            db=db,
                            session_id=session_id,
                            role=DBMessageRole.ASSISTANT,
                            content=full_response,
                            sources=citations,
                            response_time_ms=metrics.get("response_time_ms"),
                            input_tokens=metrics.get("input_tokens"),
                            output_tokens=metrics.get("output_tokens"),
                            retrieval_count=metrics.get("retrieval_count"),
                            retrieval_time_ms=metrics.get("retrieval_time_ms"),
                        )

                        # Update daily message count for assistant message
                        await StatsService.increment_message_count(db, chatbot.id, count=1)

                        # Include elapsed_time, model and metrics from the original chunk
                        done_response = {
                            'type': 'done',
                            'message_id': assistant_message.id,
                            'elapsed_time': chunk.get('elapsed_time'),
                            'model': chunk.get('model'),
                            'metrics': metrics,
                        }
                        yield f"data: {json.dumps(done_response)}\n\n"

                    elif chunk_type == "error":
                        yield f"data: {json.dumps(chunk)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        return StreamingResponse(
            generate_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Non-streaming response
        response_text, citations, metrics = await ChatService.generate_response(
            db=db,
            session_id=session_id,
            chatbot=chatbot,
            user_message=request.content,
        )

        # Save assistant message with metrics
        assistant_message = await ChatService.add_message(
            db=db,
            session_id=session_id,
            role=DBMessageRole.ASSISTANT,
            content=response_text,
            sources=citations,
            response_time_ms=metrics.get("response_time_ms"),
            input_tokens=metrics.get("input_tokens"),
            output_tokens=metrics.get("output_tokens"),
            retrieval_count=metrics.get("retrieval_count"),
            retrieval_time_ms=metrics.get("retrieval_time_ms"),
        )

        # Update daily message count for assistant message
        await StatsService.increment_message_count(db, chatbot.id, count=1)

        return MessageResponse(
            id=assistant_message.id,
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=response_text,
            sources=citations,
            created_at=assistant_message.created_at,
        )


@router.post("/{access_url}/sessions/{session_id}/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_generation(
    access_url: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Stop ongoing response generation for a session.

    Args:
        access_url: Chatbot access URL
        session_id: Session ID
        db: Database session

    Note:
        This endpoint sets a cancellation token in Redis.
        The streaming generator checks this token and stops if set.
    """
    chatbot = await get_active_chatbot(access_url, db)

    session = await ChatService.get_session(
        db=db,
        session_id=session_id,
        chatbot_id=chatbot.id,
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Set cancellation token in Redis
    # The streaming generator will check this and stop
    await RedisClient.set_cancel_token(session_id, expire_seconds=60)
