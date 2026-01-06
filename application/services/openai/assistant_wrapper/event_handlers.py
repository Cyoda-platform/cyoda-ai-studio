"""Event handling for OpenAI agent streaming."""

import logging
from typing import Any, Optional, Tuple

from .constants import (
    ITEM_TYPE_MESSAGE_OUTPUT,
    ITEM_TYPE_TOOL_CALL,
)

logger = logging.getLogger(__name__)


class EventHandlers:
    """Handlers for different types of streaming events."""

    @staticmethod
    def handle_raw_response_event(
        event: Any, accumulated_content: str
    ) -> Tuple[str, Optional[str]]:
        """Handle raw response event (text deltas from LLM).

        Args:
            event: Stream event from agent
            accumulated_content: Currently accumulated content

        Returns:
            Tuple of (updated_accumulated_content, content_to_yield)
        """
        if hasattr(event.data, 'delta'):
            content = event.data.delta
            if content:
                logger.debug(f"Raw response delta: {content[:50]}")
                return accumulated_content + content, content

        return accumulated_content, None

    @staticmethod
    def handle_run_item_event(
        event: Any, accumulated_content: str
    ) -> Tuple[str, Optional[str]]:
        """Handle run item event (completed messages, tool calls, etc.).

        Args:
            event: Stream event from agent
            accumulated_content: Currently accumulated content

        Returns:
            Tuple of (updated_accumulated_content, content_to_yield)
        """
        if not hasattr(event, 'item'):
            return accumulated_content, None

        # Handle message output items
        if event.item.type == ITEM_TYPE_MESSAGE_OUTPUT:
            if hasattr(event.item, 'content'):
                # Content is a list of content blocks
                for content_block in event.item.content:
                    if hasattr(content_block, 'text'):
                        text = content_block.text
                        if text and text not in accumulated_content:
                            logger.debug(f"Message output: {text[:50]}")
                            return accumulated_content + text, text

        # Handle tool call items (log but don't yield)
        elif event.item.type == ITEM_TYPE_TOOL_CALL:
            logger.info(
                f"Tool call detected: {event.item.name if hasattr(event.item, 'name') else 'unknown'}"
            )

        return accumulated_content, None

    @staticmethod
    def handle_agent_updated_event(event: Any) -> None:
        """Handle agent updated event (handoffs to sub-agents).

        Args:
            event: Stream event from agent
        """
        logger.info(f"Agent handoff detected: {event.new_agent.name}")
        # Continue streaming - the loop will capture events from the new agent
