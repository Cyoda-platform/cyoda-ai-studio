"""OpenAI Assistant Wrapper for Cyoda AI Assistant.

This module provides a backward-compatible wrapper for the refactored assistant_wrapper package.
All functionality has been split into focused modules within assistant_wrapper/.
"""

# Re-export all public APIs from the package
from .assistant_wrapper import (
    EVENT_TYPE_AGENT_UPDATED,
    EVENT_TYPE_RAW_RESPONSE,
    EVENT_TYPE_RUN_ITEM,
    ITEM_TYPE_MESSAGE_OUTPUT,
    ITEM_TYPE_TOOL_CALL,
    Agent,
    EventHandlers,
    OpenAIAgentsService,
    OpenAIAssistantWrapper,
    Runner,
    StreamingState,
    streaming_config,
)

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
