"""Tool for creating canvas refresh hooks."""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.hooks import creates_hook
from ...common.formatters.hook_formatters import format_hook_error, format_hook_success

logger = logging.getLogger(__name__)


def _extract_hook_context(
    tool_context: Optional[ToolContext],
    conversation_id: Optional[str],
    repository_name: Optional[str],
    branch_name: Optional[str],
    repository_url: Optional[str],
) -> tuple[str, str, str, str]:
    """Extract hook context from tool context state.

    Args:
        tool_context: Tool context
        conversation_id: Optional conversation ID
        repository_name: Optional repository name
        branch_name: Optional branch name
        repository_url: Optional repository URL

    Returns:
        Tuple of (conversation_id, repository_name, branch_name, repository_url)
    """
    if not tool_context:
        return (
            conversation_id or "unknown",
            repository_name or "unknown",
            branch_name or "unknown",
            repository_url or "unknown"
        )

    # Get values from tool_context if not provided
    conv_id = conversation_id or tool_context.state.get("conversation_id") or "unknown"
    repo_name = repository_name or tool_context.state.get("repository_name") or "unknown"
    branch = branch_name or tool_context.state.get("branch_name") or "unknown"

    # Build repository URL if not provided
    repo_url = repository_url
    if not repo_url:
        owner = tool_context.state.get("repository_owner")
        repo = tool_context.state.get("repository_name")
        br = tool_context.state.get("branch_name")
        if owner and repo and br:
            repo_url = f"https://github.com/{owner}/{repo}/tree/{br}"
        else:
            repo_url = "unknown"

    return conv_id, repo_name, branch, repo_url


def _create_and_store_hook(
    tool_context: ToolContext,
    conversation_id: str,
    repository_name: str,
    branch_name: str,
    repository_url: str,
) -> dict:
    """Create canvas open hook and store in context.

    Args:
        tool_context: Tool context
        conversation_id: Conversation ID
        repository_name: Repository name
        branch_name: Branch name
        repository_url: Repository URL

    Returns:
        Hook dictionary
    """
    from application.agents.shared.hooks import create_canvas_open_hook as create_hook

    hook = create_hook(
        conversation_id=conversation_id,
        repository_name=repository_name,
        branch_name=branch_name,
        repository_url=repository_url,
    )

    # Store hook in context for SSE streaming
    tool_context.state["last_tool_hook"] = hook

    logger.info(f"🎨 Created canvas refresh hook for conversation {conversation_id}")
    return hook


@creates_hook("code_changes")
async def create_canvas_refresh_hook(
    conversation_id: Optional[str] = None,
    repository_name: Optional[str] = None,
    branch_name: Optional[str] = None,
    repository_url: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Create a canvas_open hook to display resources on canvas.

    Args:
        conversation_id: Conversation ID for context
        repository_name: Repository name (owner/repo)
        branch_name: Branch name
        repository_url: Full GitHub URL to the branch
        tool_context: ADK tool context

    Returns:
        Success message with hook attached for SSE streaming
    """
    try:
        from application.agents.shared.hooks import wrap_response_with_hook

        if not tool_context:
            return format_hook_error("Tool context not available")

        # Extract context values
        conv_id, repo_name, branch, repo_url = _extract_hook_context(
            tool_context, conversation_id, repository_name,
            branch_name, repository_url
        )

        # Create and store hook
        hook = _create_and_store_hook(
            tool_context, conv_id, repo_name, branch, repo_url
        )

        message = "✅ Opening Canvas to view your artifacts..."
        return wrap_response_with_hook(format_hook_success(message), hook)

    except Exception as e:
        logger.error(f"Error creating canvas_open hook: {e}", exc_info=True)
        return format_hook_error(f"Failed to create canvas hook: {str(e)}")
