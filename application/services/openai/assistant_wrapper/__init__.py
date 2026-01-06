"""OpenAI assistant wrapper package."""

from .wrapper import OpenAIAssistantWrapper, Agent, Runner
from .models import StreamingState
from .constants import (
    EVENT_TYPE_RAW_RESPONSE,
    EVENT_TYPE_RUN_ITEM,
    EVENT_TYPE_AGENT_UPDATED,
    ITEM_TYPE_MESSAGE_OUTPUT,
    ITEM_TYPE_TOOL_CALL,
)
from .event_handlers import EventHandlers
from ..agents_service import OpenAIAgentsService

# Re-export dependencies (for test mocking)
from application.config.streaming_config import streaming_config

__all__ = [
    "OpenAIAssistantWrapper",
    "Agent",
    "Runner",
    "StreamingState",
    "EVENT_TYPE_RAW_RESPONSE",
    "EVENT_TYPE_RUN_ITEM",
    "EVENT_TYPE_AGENT_UPDATED",
    "ITEM_TYPE_MESSAGE_OUTPUT",
    "ITEM_TYPE_TOOL_CALL",
    "EventHandlers",
    "OpenAIAgentsService",
    "streaming_config",
]
