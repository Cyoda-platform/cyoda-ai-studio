"""Agent stream processing - main streaming logic.

Internal organization:
- processor.py: Core AgentStreamProcessor class
- event_processing.py: Event stream handling
- finalization.py: Stream cleanup and done event
"""

from .processor import AgentStreamProcessor

__all__ = ["AgentStreamProcessor"]
