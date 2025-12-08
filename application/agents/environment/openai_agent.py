"""OpenAI SDK implementation of Environment agent."""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Import OpenAI agents module directly to avoid namespace collision
_openai_agents = importlib.import_module("agents")
Agent = _openai_agents.Agent

from application.agents.environment.prompts import create_instruction_provider
from application.agents.shared.openai_tool_adapter import adapt_adk_tools_list
from application.agents.environment.tools import (
    check_environment_exists,
    deploy_cyoda_environment,
    deploy_user_application,
    get_deployment_status,
    get_build_logs,
    ui_function_issue_technical_user,
    show_deployment_options,
    list_environments,
    describe_environment,
    get_environment_metrics,
    get_environment_pods,
    delete_environment,
    list_user_apps,
    get_user_app_details,
    scale_user_app,
    restart_user_app,
    update_user_app_image,
    get_user_app_status,
    get_user_app_metrics,
    get_user_app_pods,
    delete_user_app,
)


def create_openai_environment_agent() -> Agent:
    """Create Environment agent for OpenAI SDK.

    Manages environment configuration and setup.
    """
    adk_instruction_provider = create_instruction_provider("environment_agent")

    def environment_instructions(context: Any, agent: Any) -> str:
        return adk_instruction_provider(context)

    # Adapt ADK tools to OpenAI SDK format
    adk_tools = [
        check_environment_exists,
        deploy_cyoda_environment,
        deploy_user_application,
        get_deployment_status,
        get_build_logs,
        ui_function_issue_technical_user,
        show_deployment_options,
        list_environments,
        describe_environment,
        get_environment_metrics,
        get_environment_pods,
        delete_environment,
        list_user_apps,
        get_user_app_details,
        scale_user_app,
        restart_user_app,
        update_user_app_image,
        get_user_app_status,
        get_user_app_metrics,
        get_user_app_pods,
        delete_user_app,
    ]
    openai_tools = adapt_adk_tools_list(adk_tools)

    environment_agent = Agent(
        name="environment_agent",
        instructions=environment_instructions,
        handoff_description="Manages environment configuration and setup.",
        tools=openai_tools,
    )

    logger.info("✓ OpenAI Environment Agent created with tools")
    return environment_agent

