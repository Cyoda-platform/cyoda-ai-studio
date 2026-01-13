"""Tool for pulling repository changes from remote.

This module handles fetching and merging changes from the remote repository.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import STOP_ON_ERROR
from application.agents.github.tool_definitions.common.utils import (
    ensure_repository_available,
)
from application.entity.conversation import Conversation
from services.services import get_entity_service

logger = logging.getLogger(__name__)


async def _get_branch_name(
    tool_context: ToolContext, conversation_id: str
) -> tuple[bool, str, str]:
    """Get branch name from context or conversation entity.

    Args:
        tool_context: Execution context
        conversation_id: Conversation ID

    Returns:
        Tuple of (success, error_msg, branch_name)
    """
    branch_name = tool_context.state.get("branch_name")
    if branch_name:
        return True, "", branch_name

    entity_service = get_entity_service()
    conversation_response = await entity_service.get_by_id(
        entity_id=conversation_id,
        entity_class=Conversation.ENTITY_NAME,
        entity_version=str(Conversation.ENTITY_VERSION),
    )

    if not conversation_response:
        return (
            False,
            f"ERROR: Conversation {conversation_id} not found.{STOP_ON_ERROR}",
            "",
        )

    conversation_data = conversation_response.data
    if isinstance(conversation_data, dict):
        branch_name = conversation_data.get("repository_branch")
    else:
        branch_name = getattr(conversation_data, "repository_branch", None)

    if not branch_name:
        return (
            False,
            f"ERROR: No branch configured for this conversation.{STOP_ON_ERROR}",
            "",
        )

    return True, "", branch_name


async def _execute_git_pull(
    repository_path: str, branch_name: str
) -> tuple[bool, str, str]:
    """Execute git pull command.

    Args:
        repository_path: Path to repository
        branch_name: Branch name

    Returns:
        Tuple of (success, error_msg, output)
    """
    logger.info(f"🔄 Pulling changes from origin/{branch_name} in {repository_path}")

    process = await asyncio.create_subprocess_exec(
        "git",
        "pull",
        "origin",
        branch_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=repository_path,
    )

    stdout, stderr = await process.communicate()
    stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
    stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

    if process.returncode != 0:
        logger.error(f"❌ Git pull failed: {stderr_text}")
        return False, f"ERROR: Failed to pull changes: {stderr_text}", ""

    return True, "", stdout_text


async def pull_repository_changes(tool_context: ToolContext) -> str:
    """Pull latest changes from the remote repository.

    Fetches and merges the latest changes from the remote branch into the local repository.
    This is useful for syncing with changes made by other developers or through the GitHub UI.

    Args:
        tool_context: The ADK tool context

    Returns:
        Success message with pulled changes summary, or error message
    """
    try:
        repository_path = tool_context.state.get("repository_path")
        if not repository_path:
            return f"ERROR: repository_path not found in context. Repository must be cloned first.{STOP_ON_ERROR}"

        conversation_id = tool_context.state.get("conversation_id")
        if not conversation_id:
            return f"ERROR: conversation_id not found in context.{STOP_ON_ERROR}"

        success, error_msg, branch_name = await _get_branch_name(
            tool_context, conversation_id
        )
        if not success:
            return error_msg

        success, message, repository_path = await ensure_repository_available(
            repository_path=repository_path,
            tool_context=tool_context,
            require_git=True,
        )

        if not success:
            return f"ERROR: {message}{STOP_ON_ERROR}"

        success, error_msg, stdout_text = await _execute_git_pull(
            repository_path, branch_name
        )
        if not success:
            return error_msg

        if "Already up to date" in stdout_text or "Already up-to-date" in stdout_text:
            logger.info("✅ Repository already up to date")
            return "✅ Repository is already up to date. No changes to pull."

        logger.info(f"✅ Successfully pulled changes:\n{stdout_text}")
        return (
            f"✅ Successfully pulled changes from remote repository.\n\n{stdout_text}"
        )

    except Exception as e:
        logger.error(f"Error pulling repository changes: {e}", exc_info=True)
        return f"ERROR: {str(e)}"
