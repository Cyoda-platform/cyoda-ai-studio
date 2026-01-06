"""
Cyoda AI Assistant Agents

Supports both Google ADK and OpenAI Agents SDK.
SDK selection via AI_SDK environment variable:
- "google" (default): Google ADK Hierarchical Task Decomposition Pattern
- "openai": OpenAI Agents SDK

See: https://google.github.io/adk-docs/agents/multi-agents/#hierarchical-task-decomposition
"""


def __getattr__(name: str):
    """Lazy import to avoid circular imports."""
    if name == "create_cyoda_assistant":
        from application.agents.cyoda_assistant import create_cyoda_assistant
        return create_cyoda_assistant
    elif name == "CyodaAssistantWrapper":
        from application.services.assistant.wrapper import CyodaAssistantWrapper
        return CyodaAssistantWrapper
    elif name == "OpenAIAssistantWrapper":
        from application.services.openai.assistant_wrapper import OpenAIAssistantWrapper
        return OpenAIAssistantWrapper
    elif name == "agent":
        # Import agent module for ADK evaluation
        import importlib
        agent_module = importlib.import_module("application.agents.agent")
        return agent_module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "create_cyoda_assistant",
    "CyodaAssistantWrapper",
    "OpenAIAssistantWrapper",
]
