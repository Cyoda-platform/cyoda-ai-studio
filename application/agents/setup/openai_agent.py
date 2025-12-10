"""OpenAI SDK implementation of Setup agent."""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Import OpenAI agents module directly to avoid namespace collision
_openai_agents = importlib.import_module("agents")
Agent = _openai_agents.Agent

from application.agents.setup.prompts import create_instruction_provider
from application.agents.shared.openai_tool_adapter import adapt_adk_tools_list
from application.agents.setup.tools import (
    set_setup_context,
    get_build_context,
    validate_environment,
    check_project_structure,
    validate_workflow_file,
    get_build_id_from_context,
    get_env_deploy_status,
    get_user_info,
    issue_technical_user,
    list_directory_files,
    read_file,
    add_application_resource,
    finish_discussion,
)


def create_openai_setup_agent() -> Agent:
    """Create Setup agent for OpenAI SDK.

    Helps users set up and configure their environment.
    """
    adk_instruction_provider = create_instruction_provider(
        "setup_agent",
        git_branch="<unknown>",
        programming_language="<unknown>",
        repository_name="<unknown>",
        entity_name="<unknown>",
        language="<unknown>",
    )

    def setup_instructions(context: Any, agent: Any) -> str:
        return adk_instruction_provider(context)

    # Adapt ADK tools to OpenAI SDK format
    adk_tools = [
        set_setup_context,
        get_build_context,
        validate_environment,
        check_project_structure,
        validate_workflow_file,
        get_build_id_from_context,
        get_env_deploy_status,
        get_user_info,
        issue_technical_user,
        list_directory_files,
        read_file,
        add_application_resource,
        finish_discussion,
    ]
    openai_tools = adapt_adk_tools_list(adk_tools)

    setup_agent = Agent(
        name="setup_agent",
        instructions=setup_instructions,
        handoff_description="Helps users set up and configure their environment.",
        tools=openai_tools,
    )

    logger.info("✓ OpenAI Setup Agent created with tools")
    return setup_agent

