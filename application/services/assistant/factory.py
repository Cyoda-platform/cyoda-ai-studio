"""Factory for creating Cyoda Assistants (Google ADK or OpenAI)."""

import logging
from typing import Any

from application.agents.cyoda_data_agent.agent import root_agent as cyoda_data_agent
from application.agents.environment.agent import root_agent as environment_agent
from application.agents.github.agent import root_agent as github_agent
from application.agents.qa.agent import root_agent as qa_agent
from application.agents.setup.agent import root_agent as setup_agent
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
        from google.adk.agents import LlmAgent
        from application.services.assistant.wrapper import CyodaAssistantWrapper

        logger.info("Initializing Google ADK Assistant")
        model_config = get_model_config()
        logger.info(f"Using model: {AI_MODEL} with retry support")

        # Import get_user_info tool if available
        tools = []
        try:
            from application.agents.setup.tools import get_user_info
            tools = [get_user_info]
            logger.info("✓ get_user_info tool loaded")
        except ImportError:
            logger.warning("⚠️ get_user_info tool not available - user context may be limited")

        coordinator = LlmAgent(
            name="cyoda_assistant",
            model=model_config,
            description=(
                "Cyoda AI Assistant - helps users build and edit event-driven applications naturally"
            ),
            instruction=create_instruction_provider("coordinator"),
            tools=tools,
            sub_agents=[
                qa_agent,
                setup_agent,
                environment_agent,
                github_agent,
                cyoda_data_agent
            ],
        )

        logger.info(
            "✓ Cyoda Assistant created with QA, Setup, Environment, "
            "GitHub, and Cyoda Data sub-agents"
        )
        logger.info("✓ Using Google ADK with sub_agents pattern")
        return CyodaAssistantWrapper(coordinator, self.entity_service)

    def _create_openai_assistant(self) -> Any:
        """Create OpenAI based assistant."""
        from application.services.openai.assistant_wrapper import OpenAIAssistantWrapper
        from application.agents.openai_agents import create_openai_coordinator_agent

        logger.info("Initializing OpenAI Agents Assistant")
        coordinator = create_openai_coordinator_agent()
        
        logger.info("✓ Cyoda Assistant created with OpenAI Agents SDK")
        return OpenAIAssistantWrapper(coordinator, self.entity_service)
