"""Factory functions for creating different types of AI assistants."""

from __future__ import annotations

import logging
from typing import Any

from application.services.sdk_factory import is_using_openai_sdk

logger = logging.getLogger(__name__)


def _create_google_adk_assistant(entity_service: Any) -> Any:
    """Create Cyoda Assistant using Google ADK SDK.

    Args:
        entity_service: Cyoda entity service for session persistence

    Returns:
        CyodaAssistantWrapper with Google ADK agent
    """
    # Import coordinator agent (single source of truth)
    from application.agents.coordinator.agent import root_agent as coordinator_agent
    from common.config.config import AI_MODEL

    # Import wrapper
    from .wrapper import CyodaAssistantWrapper

    logger.info("Initializing Google ADK Assistant")
    logger.info(f"Using model: {AI_MODEL} with retry support")

    # Use coordinator agent directly
    logger.info(
        "✓ Cyoda Assistant created with QA, Environment, "
        "GitHub, and Cyoda Data sub-agents"
    )
    logger.info("✓ Using Google ADK with sub_agents pattern")

    # Wrap in Cyoda-specific wrapper
    wrapper = CyodaAssistantWrapper(
        adk_agent=coordinator_agent, entity_service=entity_service
    )
    return wrapper


def _create_openai_assistant(entity_service: Any) -> Any:
    """Create Cyoda Assistant using OpenAI Agents SDK.

    Args:
        entity_service: Cyoda entity service for session persistence

    Returns:
        OpenAIAssistantWrapper with OpenAI agent
    """
    from application.agents.openai_agents import create_openai_coordinator_agent
    from application.services.openai.assistant_wrapper import OpenAIAssistantWrapper

    logger.info("Initializing OpenAI Agents Assistant")

    # Create coordinator agent with handoffs to all sub-agents
    coordinator = create_openai_coordinator_agent()

    logger.info("✓ Cyoda Assistant created with OpenAI Agents SDK")
    logger.info("✓ Using OpenAI Agents with coordinator pattern and handoffs")

    # Wrap in Cyoda-specific wrapper
    wrapper = OpenAIAssistantWrapper(agent=coordinator, entity_service=entity_service)
    return wrapper


def create_cyoda_assistant(google_adk_service: Any, entity_service: Any) -> Any:
    """Create the Cyoda AI Assistant using configured SDK (Google ADK or OpenAI).

    Selects SDK based on AI_SDK environment variable:
    - "google" (default): Uses Google ADK with Coordinator/Dispatcher pattern
    - "openai": Uses OpenAI Agents SDK

    Args:
        google_adk_service: Google ADK service (not used - agents use their own client)
        entity_service: Cyoda entity service for session persistence

    Returns:
        CyodaAssistantWrapper (Google ADK) or OpenAIAssistantWrapper (OpenAI)
    """
    from application.services.sdk_factory import get_sdk_name

    sdk_name = get_sdk_name()
    logger.info(f"Creating Cyoda Assistant with {sdk_name.upper()} SDK")

    if is_using_openai_sdk():
        return _create_openai_assistant(entity_service)
    else:
        return _create_google_adk_assistant(entity_service)
