"""Environment Management agent for Cyoda deployment operations."""

from __future__ import annotations

import os
from typing import Union

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import transfer_to_agent

from application.agents.monitoring.agent import deployment_monitor
from application.agents.prompts import create_instruction_provider

from .tools import (
    check_environment_exists,
    deploy_cyoda_environment,
    deploy_user_application,
    get_build_logs,
    get_deployment_status,
    ui_function_issue_technical_user,
)


def _get_model_config() -> Union[str, LiteLlm]:
    """Get model configuration based on AI_MODEL environment variable.

    Returns:
        Model configuration (string for Gemini, LiteLlm instance for others)
    """
    model_name = os.getenv("AI_MODEL", "openai/gpt-4o-mini")

    # If model starts with "openai/" or "anthropic/", use LiteLLM
    if model_name.startswith(("openai/", "anthropic/")):
        return LiteLlm(model=model_name)

    # Otherwise, assume it's a Gemini model
    return model_name


root_agent = LlmAgent(
    name="environment_agent",
    model=_get_model_config(),
    description="Cyoda environment management specialist. Handles environment provisioning, application deployment, build monitoring, troubleshooting, and credential management.",
    instruction=create_instruction_provider("environment_agent"),
    tools=[
        check_environment_exists,
        deploy_cyoda_environment,
        deploy_user_application,
        get_deployment_status,
        get_build_logs,
        ui_function_issue_technical_user,
    ],
    sub_agents=[deployment_monitor],
)
