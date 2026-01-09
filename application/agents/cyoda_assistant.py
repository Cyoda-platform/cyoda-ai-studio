"""Cyoda AI Assistant supporting both Google ADK and OpenAI Agents SDK.

All implementation has been moved to cyoda_assistant/ subdirectory.
This file maintains backward compatibility by re-exporting all components.
"""

from __future__ import annotations

# Re-export all public components for backward compatibility
from .cyoda_assistant import (
    CyodaAssistantWrapper,
    _create_google_adk_assistant,
    _create_openai_assistant,
    create_cyoda_assistant,
)

__all__ = [
    "create_cyoda_assistant",
    "_create_google_adk_assistant",
    "_create_openai_assistant",
    "CyodaAssistantWrapper",
]
