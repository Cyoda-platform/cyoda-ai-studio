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
    show_setup_options,
    validate_environment,
    check_project_structure,
    validate_workflow_file,
    get_build_id_from_context,
    get_build_context,
    get_user_info,
    get_env_deploy_status,
    list_directory_files,
    read_file,
    add_application_resource,
    set_setup_context,
    finish_discussion,
)


def create_openai_setup_agent() -> Agent:
    """Create Setup agent for OpenAI SDK.

    Helps users understand the setup process and connects them with specialized agents.
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
        show_setup_options,
        validate_environment,
        check_project_structure,
        validate_workflow_file,
        get_build_id_from_context,
        get_build_context,
        get_user_info,
        get_env_deploy_status,
        list_directory_files,
        read_file,
        add_application_resource,
        set_setup_context,
        finish_discussion,
    ]
    openai_tools = adapt_adk_tools_list(adk_tools)

    setup_agent = Agent(
        name="setup_agent",
        instructions=setup_instructions,
        handoff_description=(
            "Helps users understand the setup process and connects them with specialized agents for "
            "code analysis, deployment, and credentials."
        ),
        tools=openai_tools,
    )

    logger.info("✓ OpenAI Setup Agent created with tools")
    return setup_agent

