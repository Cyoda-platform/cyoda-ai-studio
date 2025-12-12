"""GitHub Agent for repository operations and canvas integration."""

from __future__ import annotations

import logging
import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from application.agents.github.prompts import create_instruction_provider
from application.agents.shared import get_model_config
from application.services.github.auth.installation_token_manager import (
    InstallationTokenManager,
)

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

from application.agents.environment.tools import (
    deploy_cyoda_environment,
)

from .tools import (
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
    load_workflow_example,
    load_workflow_prompt,
    load_workflow_schema,
    pull_repository_changes,
    save_file_to_repository,
    validate_workflow_against_schema,
)

from application.agents.shared.streaming_callback import accumulate_streaming_response

logger = logging.getLogger(__name__)


def _get_github_token_for_mcp() -> str:
    """Get GitHub installation token for MCP server authentication.

    This function is called synchronously during agent initialization,
    so we need to handle the async token manager carefully.

    NOTE: This uses the default installation_id from environment for MCP read-only tools.
    Write operations (commit, push) use the installation_id from Conversation entity
    via the custom tools (save_file_to_repository, commit_and_push_changes).

    Returns:
        GitHub installation access token
    """
    import asyncio

    try:
        # Get installation ID from environment (for MCP read-only tools)
        installation_id = int(os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID", "0"))
        if not installation_id:
            logger.warning(
                "GITHUB_PUBLIC_REPO_INSTALLATION_ID not configured, MCP tools may not work"
            )
            return ""

        # Create token manager
        token_manager = InstallationTokenManager()

        # Handle event loop properly
        try:
            # Check if we're already in an event loop
            loop = asyncio.get_running_loop()
            # If we get here, we're in a running loop, so we can't use run_until_complete
            # Instead, we'll return empty token and let the MCP toolset handle auth later
            logger.warning("Event loop already running, MCP token will be obtained later")
            return ""
        except RuntimeError:
            # No running loop, safe to create one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    logger.warning("Event loop is running, MCP token will be obtained later")
                    return ""
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Get token (this will cache it)
            token = loop.run_until_complete(
                token_manager.get_installation_token(installation_id)
            )

        logger.info("Successfully obtained GitHub installation token for MCP")
        return token

    except Exception as e:
        logger.error(f"Failed to get GitHub token for MCP: {e}", exc_info=True)
        return ""


# Get GitHub token for MCP server (called once during module load)
_GITHUB_TOKEN = _get_github_token_for_mcp()


def _create_github_mcp_toolset():
    """Create GitHub MCP Toolset with proper error handling."""
    if not _GITHUB_TOKEN:
        logger.warning("No GitHub token available for MCP toolset, MCP tools will be disabled")
        logger.info("GitHub agent will use custom tools only, which provide full functionality")
        return None

    try:
        toolset = MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url="https://api.githubcopilot.com/mcp/",
                headers={
                    "Authorization": f"Bearer {_GITHUB_TOKEN}",
                    "X-MCP-Toolsets": "repos,issues,pull_requests,code_security",  # Enable specific toolsets
                    "X-MCP-Readonly": "false",  # Allow write operations
                },
            ),
            tool_filter=[
                # Repository tools
                "get_file_contents",
                "search_code",
                "list_commits",
                "get_commit",
                # Issue tools (for future use)
                "list_issues",
                "get_issue",
                # PR tools (for future use)
                "list_pull_requests",
                "get_pull_request",
            ],
        )
        logger.info("GitHub MCP toolset created successfully")
        return toolset
    except Exception as e:
        logger.error(f"Failed to create GitHub MCP toolset: {e}", exc_info=True)
        logger.info("Falling back to custom tools only")
        return None


# Create GitHub MCP Toolset
# Uses Google Cloud's GitHub MCP Server: https://api.githubcopilot.com/mcp/
github_mcp_toolset = _create_github_mcp_toolset()


# Prepare tools list
tools = [
    # Interactive UI tools
    ask_user_to_select_option,
    # Repository configuration and setup
    set_repository_config,
    generate_branch_uuid,
    clone_repository,
    check_existing_branch_configuration,
    # Agentic Unix command execution
    execute_unix_command,
    # Code generation with CLI (incremental changes)
    generate_code_with_cli,
    # Application generation (complete apps from scratch)
    generate_application,
    # File management
    retrieve_and_save_conversation_files,
    save_files_to_branch,
    # Environment status and deployment
    check_user_environment_status,
    deploy_cyoda_environment,
    # Path helper functions
    get_entity_path,
    get_workflow_path,
    get_requirements_path,
    # Workflow schema, example, and prompt loading
    load_workflow_schema,
    load_workflow_example,
    load_workflow_prompt,
    # Workflow validation
    validate_workflow_against_schema,
    # Custom tools for repository operations
    analyze_repository_structure,
    analyze_repository_structure_agentic,
    save_file_to_repository,
    commit_and_push_changes,
    pull_repository_changes,
    get_repository_diff,
]

# Add MCP toolset if available
if github_mcp_toolset is not None:
    tools.append(github_mcp_toolset)
    logger.info("✓ GitHub MCP toolset added to agent")
else:
    logger.warning("⚠ GitHub MCP toolset not available, using custom tools only")

# Main GitHub agent
root_agent = LlmAgent(
    name="github_agent",
    model=get_model_config(),
    description="GitHub repository operations specialist. Handles repository analysis, file operations, commits, and canvas integration.",
    instruction=create_instruction_provider(
        "github_agent",
        repository_owner="<unknown>",
        repository_name="<unknown>",
        branch_name="<unknown>",
    ),
    tools=tools,
    after_agent_callback=accumulate_streaming_response,
)


if github_mcp_toolset is not None:
    logger.info("✓ GitHub Agent created with custom tools and GitHub MCP integration")
    logger.info("✓ MCP Toolsets enabled: repos, issues, pull_requests, code_security")
else:
    logger.info("✓ GitHub Agent created with custom tools only (MCP integration disabled)")

# Export as 'agent' for ADK evaluator compatibility
agent = root_agent
