"""Data models for assistant wrapper."""

from typing import Optional

from pydantic import BaseModel


class StreamingState(BaseModel):
    """State container for message streaming."""

    accumulated_content: str = ""
    user_message: str = ""
    conversation_history: list[dict[str, str]] = []
    conversation_id: Optional[str] = None
    user_id: str = "guest.anonymous"
