"""
Cyoda AI Assistant Agents

Supports both Google ADK and OpenAI Agents SDK.
SDK selection via AI_SDK environment variable:
- "google" (default): Google ADK Hierarchical Task Decomposition Pattern
- "openai": OpenAI Agents SDK

See: https://google.github.io/adk-docs/agents/multi-agents/#hierarchical-task-decomposition
"""

from application.agents.cyoda_assistant import (
    CyodaAssistantWrapper,
    create_cyoda_assistant,
)


def __getattr__(name: str):
    """Lazy import to avoid circular imports."""
    if name == "OpenAIAssistantWrapper":
        from application.services.openai_assistant_wrapper import OpenAIAssistantWrapper
        return OpenAIAssistantWrapper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "create_cyoda_assistant",
    "CyodaAssistantWrapper",
    "OpenAIAssistantWrapper",
]
