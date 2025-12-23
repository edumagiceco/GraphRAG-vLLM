"""
Server-Sent Events helpers for streaming responses.
"""
import json
from typing import Any, AsyncIterator


def format_sse_event(data: Any, event: str = None, id: str = None) -> str:
    """
    Format data as an SSE event string.

    Args:
        data: Data to send (will be JSON serialized if not string)
        event: Optional event type
        id: Optional event ID

    Returns:
        Formatted SSE event string
    """
    lines = []

    if id:
        lines.append(f"id: {id}")

    if event:
        lines.append(f"event: {event}")

    if isinstance(data, str):
        lines.append(f"data: {data}")
    else:
        lines.append(f"data: {json.dumps(data)}")

    return "\n".join(lines) + "\n\n"


def format_content_event(content: str) -> str:
    """Format a content chunk event."""
    return format_sse_event({"type": "content", "content": content})


def format_sources_event(sources: list[dict]) -> str:
    """Format a sources event."""
    return format_sse_event({"type": "sources", "sources": sources})


def format_done_event(message_id: str = None) -> str:
    """Format a completion event."""
    data = {"type": "done"}
    if message_id:
        data["message_id"] = message_id
    return format_sse_event(data)


def format_error_event(error: str) -> str:
    """Format an error event."""
    return format_sse_event({"type": "error", "error": error})


async def sse_generator(
    stream: AsyncIterator[dict],
) -> AsyncIterator[str]:
    """
    Convert a stream of dicts to SSE formatted strings.

    Args:
        stream: Async iterator yielding event dicts

    Yields:
        SSE formatted strings
    """
    try:
        async for chunk in stream:
            chunk_type = chunk.get("type", "content")

            if chunk_type == "content":
                yield format_content_event(chunk.get("content", ""))
            elif chunk_type == "sources":
                yield format_sources_event(chunk.get("sources", []))
            elif chunk_type == "done":
                yield format_done_event(chunk.get("message_id"))
            elif chunk_type == "error":
                yield format_error_event(chunk.get("error", "Unknown error"))
            else:
                yield format_sse_event(chunk)

    except Exception as e:
        yield format_error_event(str(e))
