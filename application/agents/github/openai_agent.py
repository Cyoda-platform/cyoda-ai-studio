"""OpenAI SDK implementation of GitHub agent."""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Import OpenAI agents module directly to avoid namespace collision
_openai_agents = importlib.import_module("agents")
Agent = _openai_agents.Agent

from application.agents.github.prompts import create_instruction_provider
from application.agents.shared.openai_tool_adapter import adapt_adk_tools_list
from application.agents.shared.repository_tools import (
    clone_repository,
    set_repository_config,
    ask_user_to_select_option,
    generate_branch_uuid,
    check_existing_branch_configuration,
    retrieve_and_save_conversation_files,
    save_files_to_branch,
    check_user_environment_status,
)
from application.agents.environment.tools import deploy_cyoda_environment
from application.agents.github.tools import (
    analyze_repository_structure,
    analyze_repository_structure_agentic,
    commit_and_push_changes,
    execute_unix_command,
    generate_application,
    generate_code_with_cli,
    get_entity_path,
    get_repository_diff,
    get_requirements_path,
    get_workflow_path,
    open_canvas_tab,
    pull_repository_changes,
    save_file_to_repository,
)


def create_openai_github_agent() -> Agent:
    """Create GitHub agent for OpenAI SDK.

    Manages GitHub integration and operations.
    """
    adk_instruction_provider = create_instruction_provider("github_agent")

    def github_instructions(context: Any, agent: Any) -> str:
        return adk_instruction_provider(context)

    # Adapt ADK tools to OpenAI SDK format
    adk_tools = [
        ask_user_to_select_option,
        set_repository_config,
        generate_branch_uuid,
        clone_repository,
        check_existing_branch_configuration,
        execute_unix_command,
        generate_code_with_cli,
        generate_application,
        retrieve_and_save_conversation_files,
        save_files_to_branch,
        check_user_environment_status,
        deploy_cyoda_environment,
        get_entity_path,
        get_workflow_path,
        get_requirements_path,
        analyze_repository_structure,
        analyze_repository_structure_agentic,
        save_file_to_repository,
        commit_and_push_changes,
        pull_repository_changes,
        get_repository_diff,
        open_canvas_tab,
    ]
    openai_tools = adapt_adk_tools_list(adk_tools)

    github_agent = Agent(
        name="github_agent",
        instructions=github_instructions,
        handoff_description="Manages GitHub integration and operations.",
        tools=openai_tools,
    )

    logger.info("✓ OpenAI GitHub Agent created with tools")
    return github_agent

