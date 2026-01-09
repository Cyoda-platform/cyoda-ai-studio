"""Tool call tracking and loop detection."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS_PER_STREAM = 50
MAX_CONSECUTIVE_SAME_TOOL = 7


class LoopDetector:
    """Detects infinite loops in tool call sequences."""

    def __init__(
        self,
        max_tool_calls: int = MAX_TOOL_CALLS_PER_STREAM,
        max_consecutive_same: int = MAX_CONSECUTIVE_SAME_TOOL,
    ):
        self.max_tool_calls = max_tool_calls
        self.max_consecutive_same = max_consecutive_same
        self.tool_call_history = []
        self.tool_call_count = 0

    def record_tool_call(self, tool_name: str, tool_args: str) -> Optional[str]:
        """Record a tool call and check for loops.

        Args:
            tool_name: Name of the tool being called
            tool_args: String representation of tool arguments

        Returns:
            Error message if loop detected, None otherwise
        """
        tool_call_key = (tool_name, tool_args)
        self.tool_call_history.append(tool_call_key)
        self.tool_call_count += 1

        if self._exceeds_total_calls():
            return self._get_total_calls_error()

        if self._has_consecutive_identical_calls():
            return self._get_consecutive_calls_error(tool_name)

        return None

    def _exceeds_total_calls(self) -> bool:
        """Check if total tool calls exceed limit."""
        return self.tool_call_count > self.max_tool_calls

    def _get_total_calls_error(self) -> str:
        """Get error message for exceeding total calls."""
        return (
            f"🔄 LOOP DETECTED: Exceeded {self.max_tool_calls} tool calls. "
            f"Stopping stream."
        )

    def _has_consecutive_identical_calls(self) -> bool:
        """Check if same tool called consecutively with identical args."""
        if len(self.tool_call_history) < self.max_consecutive_same:
            return False

        recent = self.tool_call_history[-self.max_consecutive_same :]
        return all(call == recent[0] for call in recent)

    def _get_consecutive_calls_error(self, tool_name: str) -> str:
        """Get error message for consecutive identical calls."""
        return (
            f"🔄 LOOP DETECTED: Tool '{tool_name}' called "
            f"{self.max_consecutive_same} times with identical args. "
            f"Stopping stream."
        )

    def reset(self) -> None:
        """Reset loop detector for new stream."""
        self.tool_call_history = []
        self.tool_call_count = 0
