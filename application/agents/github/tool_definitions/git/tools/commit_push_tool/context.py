"""Context extraction and validation for commit and push operations."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from application.agents.github.tool_definitions.common.constants import STOP_ON_ERROR
from application.agents.github.tool_definitions.common.utils import (
    ensure_repository_available,
)
from application.agents.github.tool_definitions.repository.helpers._github_service import (
    get_entity_service,
)
from application.entity.conversation import Conversation

logger = logging.getLogger(__name__)


class GitConfiguration(BaseModel):
    """Git configuration for commit operation."""

    user_name: str = "Cyoda Agent"
    user_email: str = "agent@cyoda.ai"
    repository_path: str
    commit_message: str


async def _validate_and_extract_context(
    tool_context: ToolContext,
) -> tuple[bool, str, str, str, str]:
    """Validate context and extract repository info.

    Args:
        tool_context: Execution context

    Returns:
        Tuple of (success, error_msg, repository_path, branch_name, conversation_id)
    """
    repository_path = tool_context.state.get("repository_path")
    if not repository_path:
        return (
            False,
            f"ERROR: repository_path not found in context. Repository must be cloned first.{STOP_ON_ERROR}",
            "",
            "",
            "",
        )

    conversation_id = tool_context.state.get("conversation_id")
    if not conversation_id:
        return (
            False,
            f"ERROR: conversation_id not found in context.{STOP_ON_ERROR}",
            "",
            "",
            "",
        )

    # Try context state first (most up-to-date source)
    branch_name = tool_context.state.get("branch_name")
    repository_name = tool_context.state.get("repository_name")
    repository_owner = tool_context.state.get("repository_owner")

    # Fallback to Conversation entity if needed
    if not branch_name or not repository_name:
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
                "",
                "",
            )

        conversation_data = conversation_response.data
        if isinstance(conversation_data, dict):
            branch_name = branch_name or conversation_data.get("repository_branch")
            repository_name = repository_name or conversation_data.get(
                "repository_name"
            )
            repository_owner = repository_owner or conversation_data.get(
                "repository_owner"
            )
        else:
            branch_name = branch_name or getattr(
                conversation_data, "repository_branch", None
            )
            repository_name = repository_name or getattr(
                conversation_data, "repository_name", None
            )
            repository_owner = repository_owner or getattr(
                conversation_data, "repository_owner", None
            )

    if not branch_name:
        return (
            False,
            f"ERROR: No branch configured for this conversation.{STOP_ON_ERROR}",
            "",
            "",
            "",
        )
    if not repository_name:
        return (
            False,
            f"ERROR: No repository configured for this conversation.{STOP_ON_ERROR}",
            "",
            "",
            "",
        )

    return True, "", repository_path, branch_name, conversation_id


async def _prepare_repository_and_git(
    repository_path: str, tool_context: ToolContext
) -> tuple[bool, str, str, list]:
    """Prepare repository and get git status.

    Args:
        repository_path: Path to repository
        tool_context: Execution context

    Returns:
        Tuple of (success, error_msg, updated_repo_path, changed_files)
    """
    # Ensure repository is available locally
    success, message, repository_path = await ensure_repository_available(
        repository_path=repository_path,
        tool_context=tool_context,
        require_git=True,
    )

    if not success:
        return False, f"ERROR: {message}{STOP_ON_ERROR}", "", []

    # Get changed files list
    original_cwd = os.getcwd()
    changed_files = []

    try:
        os.chdir(repository_path)
        status_process = await asyncio.create_subprocess_exec(
            "git",
            "status",
            "--porcelain",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        status_stdout, _ = await status_process.communicate()

        if status_process.returncode == 0:
            for line in status_stdout.decode().splitlines():
                if len(line) > 3:
                    changed_files.append(line[3:].strip())
    finally:
        os.chdir(original_cwd)

    return True, "", repository_path, changed_files
