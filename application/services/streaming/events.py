"""SSE event representation and formatting."""

import json
from datetime import datetime
from typing import Any, Dict, Optional


class StreamEvent:
    """Represents a streaming event to send to the client."""

    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        event_id: Optional[str] = None,
    ):
        """Initialize a stream event.

        Args:
            event_type: Type of event (start, agent, tool, content, progress, error, done)
            data: Event data dictionary
            event_id: Optional event ID for client tracking
        """
        self.event_type = event_type
        self.data = data
        self.event_id = event_id or str(int(datetime.utcnow().timestamp() * 1000))
        self.timestamp = datetime.utcnow().isoformat()

    def to_sse(self) -> str:
        """Convert event to SSE format.

        Returns:
            SSE-formatted string with event type, data, and optional ID
        """
        lines = [
            f"id: {self.event_id}",
            f"event: {self.event_type}",
        ]

        event_data = {**self.data, "timestamp": self.timestamp}
        lines.append(f"data: {json.dumps(event_data)}")

        return "\n".join(lines) + "\n\n"
