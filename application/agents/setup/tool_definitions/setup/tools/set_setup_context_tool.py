"""Tool for setting setup context in session state."""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from ...common.constants.constants import (
    KEY_ENTITY_NAME,
    KEY_GIT_BRANCH,
    KEY_PROGRAMMING_LANGUAGE,
    KEY_REPOSITORY_NAME,
    VALID_LANGUAGES,
)
from ...common.formatters.setup_formatters import format_setup_context
from ...common.utils.decorators import handle_tool_errors

logger = logging.getLogger(__name__)


@handle_tool_errors
async def set_setup_context(
    programming_language: str,
    git_branch: str,
    repository_name: str,
    entity_name: Optional[str] = None,
    tool_context: ToolContext = None,
) -> str:
    """Set the setup context parameters in session state.

    This tool should be called once the agent has gathered all required information
    from the user (programming language, git branch, repository name). It stores
    these values in session state so they can be used by the instruction template.

    Args:
        programming_language: Either "PYTHON" or "JAVA"
        git_branch: The git branch the user is working on
        repository_name: Either "mcp-cyoda-quart-app" or "java-client-template"
        entity_name: Optional entity name for the application
        tool_context: Tool context containing session state

    Returns:
        Confirmation message with the stored context
    """
    # Validate programming language
    if programming_language not in VALID_LANGUAGES:
        return f"Error: programming_language must be either 'PYTHON' or 'JAVA', got '{programming_language}'"

    # Store in session state
    tool_context.state[KEY_PROGRAMMING_LANGUAGE] = programming_language
    tool_context.state[KEY_GIT_BRANCH] = git_branch
    tool_context.state[KEY_REPOSITORY_NAME] = repository_name

    # Store entity_name if provided
    if entity_name:
        tool_context.state[KEY_ENTITY_NAME] = entity_name

    logger.info(
        f"Setup context set: {programming_language}, {git_branch}, {repository_name}, entity_name={entity_name}"
    )

    return format_setup_context(
        programming_language=programming_language,
        git_branch=git_branch,
        repository_name=repository_name,
        entity_name=entity_name,
    )
