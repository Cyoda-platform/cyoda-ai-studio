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
    from google.adk.agents import LlmAgent
    from application.agents.shared import get_model_config
    from application.agents.shared.prompts import create_instruction_provider
    from common.config.config import AI_MODEL

    # Import all sub-agents
    from application.agents.cyoda_data_agent.agent import root_agent as cyoda_data_agent
    from application.agents.environment.agent import root_agent as environment_agent
    from application.agents.github.agent import root_agent as github_agent
    from application.agents.qa.agent import root_agent as qa_agent
    from application.agents.setup.agent import root_agent as setup_agent

    # Import wrapper
    from .wrapper import CyodaAssistantWrapper

    logger.info("Initializing Google ADK Assistant")

    # Get model configuration with retry support
    model_config = get_model_config()
    logger.info(f"Using model: {AI_MODEL} with retry support")

    # Create coordinator agent with sub-agents
    coordinator = LlmAgent(
        name="cyoda_assistant",
        model=model_config,
        description="Cyoda AI Assistant - helps users build and edit event-driven applications naturally",
        instruction=create_instruction_provider("coordinator"),
        tools=[],
        sub_agents=[
            qa_agent,
            setup_agent,
            environment_agent,
            github_agent,
            cyoda_data_agent,
        ],
    )

    logger.info(
        "✓ Cyoda Assistant created with QA, Setup, Environment, "
        "GitHub, and Cyoda Data sub-agents"
    )
    logger.info("✓ Using Google ADK with sub_agents pattern")

    # Wrap in Cyoda-specific wrapper
    wrapper = CyodaAssistantWrapper(
        adk_agent=coordinator, entity_service=entity_service
    )
    return wrapper


def _create_openai_assistant(entity_service: Any) -> Any:
    """Create Cyoda Assistant using OpenAI Agents SDK.

    Args:
        entity_service: Cyoda entity service for session persistence

    Returns:
        OpenAIAssistantWrapper with OpenAI agent
    """
    from application.services.openai.assistant_wrapper import OpenAIAssistantWrapper
    from application.agents.openai_agents import create_openai_coordinator_agent

    logger.info("Initializing OpenAI Agents Assistant")

    # Create coordinator agent with handoffs to all sub-agents
    coordinator = create_openai_coordinator_agent()

    logger.info("✓ Cyoda Assistant created with OpenAI Agents SDK")
    logger.info("✓ Using OpenAI Agents with coordinator pattern and handoffs")

    # Wrap in Cyoda-specific wrapper
    wrapper = OpenAIAssistantWrapper(
        agent=coordinator, entity_service=entity_service
    )
    return wrapper


def create_cyoda_assistant(
    google_adk_service: Any, entity_service: Any
) -> Any:
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
