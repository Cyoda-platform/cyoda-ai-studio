"""Validation functions for CLI parameters and state.

This module handles validation of CLI parameters, branch protection,
build status, and invocation limits.
"""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import STOP_ON_ERROR
from application.agents.shared.repository_tools import _is_protected_branch
from application.agents.shared.repository_tools.constants import PROTECTED_BRANCHES

from .context_extraction import CLIContext, _extract_context_values

logger = logging.getLogger(__name__)


def _validate_cli_parameters(
    language: Optional[str],
    repository_path: Optional[str],
    branch_name: Optional[str],
) -> str:
    """Validate required CLI parameters.

    Args:
        language: Programming language
        repository_path: Repository path
        branch_name: Branch name

    Returns:
        Empty string if valid, error message otherwise
    """
    if not language:
        return (
            f"ERROR: Language not specified and not found in context. "
            f"Please call clone_repository first.{STOP_ON_ERROR}"
        )
    if not repository_path:
        return (
            f"ERROR: Repository path not specified and not found in context. "
            f"Please call clone_repository first.{STOP_ON_ERROR}"
        )
    if not branch_name:
        return (
            f"ERROR: Branch name not specified and not found in context. "
            f"Please call clone_repository first.{STOP_ON_ERROR}"
        )

    return ""


def _extract_cli_context(
    requirements: str,
    language: Optional[str],
    repository_path: Optional[str],
    branch_name: Optional[str],
    tool_context: Optional[ToolContext],
) -> tuple[bool, str, Optional[CLIContext]]:
    """Extract and validate CLI context from parameters.

    Args:
        requirements: User requirements
        language: Programming language
        repository_path: Repository path
        branch_name: Branch name
        tool_context: Tool context

    Returns:
        Tuple of (success, error_message, cli_context)
    """
    if not tool_context:
        return False, f"ERROR: Tool context not available.{STOP_ON_ERROR}", None

    (
        language,
        repository_path,
        branch_name,
        repository_name,
        session_id,
        repository_type,
        conversation_id,
    ) = _extract_context_values(language, repository_path, branch_name, tool_context)

    error_msg = _validate_cli_parameters(language, repository_path, branch_name)
    if error_msg:
        return False, error_msg, None

    context = CLIContext(
        requirements=requirements,
        language=language,
        repository_path=repository_path,
        branch_name=branch_name,
        repository_name=repository_name,
        tool_context=tool_context,
        session_id=session_id,
        repository_type=repository_type,
        conversation_id=conversation_id,
    )

    return True, "", context


async def _check_build_already_started(
    tool_context: ToolContext,
) -> tuple[bool, Optional[str]]:
    """Check if build already started for this branch.

    Args:
        tool_context: Tool context

    Returns:
        Tuple of (already_started, error_message)
    """
    existing_build_pid = tool_context.state.get("build_process_pid")
    existing_branch = tool_context.state.get("branch_name")

    if existing_build_pid and existing_branch:
        logger.warning(
            f"⚠️ Build already started for branch {existing_branch} (PID: {existing_build_pid})"
        )
        error_msg = (
            f"⚠️ Build already in progress for branch {existing_branch} "
            f"(PID: {existing_build_pid}). Please wait for it to complete."
        )
        return True, error_msg

    return False, None


async def _validate_branch_not_protected(
    branch_name: str,
) -> tuple[bool, Optional[str]]:
    """Validate that branch is not protected.

    Args:
        branch_name: Branch name to check

    Returns:
        Tuple of (is_valid, error_message)
    """
    if await _is_protected_branch(branch_name):
        error_msg = (
            f"🚫 CRITICAL ERROR: Cannot build on protected branch '{branch_name}'. "
            f"Protected branches ({', '.join(sorted(PROTECTED_BRANCHES))}) must NEVER be modified. "
            f"Please use generate_branch_uuid() to create a unique branch name."
        )
        logger.error(error_msg)
        return False, f"ERROR: {error_msg}"

    return True, None


def _validate_cli_invocation_limit(session_id: str) -> tuple[bool, Optional[str], int]:
    """Validate CLI invocation limit.

    Args:
        session_id: Session ID

    Returns:
        Tuple of (is_allowed, error_message, cli_count)
    """
    # Local import for test mocking compatibility
    from application.services.streaming_service import (
        check_cli_invocation_limit,
        get_cli_invocation_count,
    )

    is_allowed, error_msg = check_cli_invocation_limit(session_id)
    if not is_allowed:
        logger.error(error_msg)
        return False, f"ERROR: {error_msg}", 0

    cli_count = get_cli_invocation_count(session_id)
    logger.info(f"🔧 CLI invocation #{cli_count} for session {session_id}")
    return True, None, cli_count
