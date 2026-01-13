"""Factory for creating Cyoda Assistants (Google ADK or OpenAI)."""

import logging
from typing import Any

from application.agents.cyoda_data_agent.agent import root_agent as cyoda_data_agent
from application.agents.environment.agent import root_agent as environment_agent
from application.agents.github.agent import root_agent as github_agent
from application.agents.qa.agent import root_agent as qa_agent
from application.agents.shared import get_model_config
from application.agents.shared.prompts import create_instruction_provider
from application.services.sdk_factory import get_sdk_name, is_using_openai_sdk
from common.config.config import AI_MODEL

logger = logging.getLogger(__name__)


class AssistantFactory:
    """Factory to create the appropriate assistant based on configuration."""

    def __init__(self, entity_service: Any):
        self.entity_service = entity_service

    def create_assistant(self) -> Any:
        """Create the assistant based on environment configuration."""
        sdk_name = get_sdk_name()
        logger.info(f"Creating Cyoda Assistant with {sdk_name.upper()} SDK")

        if is_using_openai_sdk():
            return self._create_openai_assistant()
        else:
            return self._create_google_adk_assistant()

    def _create_google_adk_assistant(self) -> Any:
        """Create Google ADK based assistant."""
        # Import coordinator agent (single source of truth)
        from application.agents.coordinator.agent import root_agent as coordinator_agent
        from application.services.assistant.wrapper import CyodaAssistantWrapper

        logger.info("Initializing Google ADK Assistant")
        logger.info(f"Using model: {AI_MODEL} with retry support")

        logger.info(
            "✓ Cyoda Assistant created with QA, Environment, "
            "GitHub, and Cyoda Data sub-agents"
        )
        logger.info("✓ Using Google ADK with sub_agents pattern")
        return CyodaAssistantWrapper(coordinator_agent, self.entity_service)

    def _create_openai_assistant(self) -> Any:
        """Create OpenAI based assistant."""
        from application.agents.openai_agents import create_openai_coordinator_agent
        from application.services.openai.assistant_wrapper import OpenAIAssistantWrapper

        logger.info("Initializing OpenAI Agents Assistant")
        coordinator = create_openai_coordinator_agent()

        logger.info("✓ Cyoda Assistant created with OpenAI Agents SDK")
        return OpenAIAssistantWrapper(coordinator, self.entity_service)
