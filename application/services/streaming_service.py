"""Backward compatibility wrapper for streaming service.

This module maintains backward compatibility by re-exporting from the new
modular streaming package. All new code should import from
application.services.streaming directly.
"""

import logging

# Re-export public API from new modules
from application.services.streaming.service import StreamingService
from application.services.streaming.events import StreamEvent
from application.services.streaming.cli_tracker import (
    check_cli_invocation_limit,
    reset_cli_invocation_count,
    get_cli_invocation_count,
    CLIInvocationTracker,
)
from application.services.streaming.hook_normalizer import normalize_hook
from application.services.streaming.constants import (
    STREAM_TIMEOUT,
    MAX_RESPONSE_SIZE,
    MAX_EVENTS_PER_STREAM,
)

logger = logging.getLogger(__name__)


def format_response_section(title: str, content: str, section_type: str = "info") -> str:
    """Format a response section with markdown styling for visual separation.

    Args:
        title: Section title
        content: Section content
        section_type: Type of section (info, tool_response, agent_message, etc.)

    Returns:
        Formatted markdown string with visual separation
    """
    if not content or not content.strip():
        return ""

    return f"\n\n---\n\n**{title}:**\n\n{content}"


__all__ = [
    "StreamingService",
    "StreamEvent",
    "check_cli_invocation_limit",
    "reset_cli_invocation_count",
    "get_cli_invocation_count",
    "CLIInvocationTracker",
    "normalize_hook",
    "format_response_section",
    "STREAM_TIMEOUT",
    "MAX_RESPONSE_SIZE",
    "MAX_EVENTS_PER_STREAM",
]

