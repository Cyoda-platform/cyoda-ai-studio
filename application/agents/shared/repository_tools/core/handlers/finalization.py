"""Finalization operations for repository setup.

This module handles context updates, entity updates, and success message
formatting after successful repository clone operations.
"""

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from ..context import _store_in_tool_context, _update_conversation_entity, _update_conversation_build_context_wrapper

logger = logging.getLogger(__name__)


async def _finalize_clone(
    tool_context: Optional[ToolContext],
    conversation_id: Optional[str],
    target_directory: str,
    branch_name: str,
    language: str,
    repository_name: str,
    repository_owner: str,
    user_repo_url: Optional[str],
    installation_id: Optional[str],
    repo_type: Optional[str],
) -> None:
    """Finalize clone operation by updating context and entities.

    Args:
        tool_context: Tool context
        conversation_id: Conversation ID
        target_directory: Repository path
        branch_name: Branch name
        language: Programming language
        repository_name: Repository name
        repository_owner: Repository owner
        user_repo_url: User repository URL
        installation_id: Installation ID
        repo_type: Repository type
    """
    if tool_context:
        _store_in_tool_context(
            tool_context, target_directory, branch_name, language,
            repository_name, repository_owner, user_repo_url,
            installation_id, repo_type
        )

    if conversation_id:
        await _update_conversation_entity(
            conversation_id, repository_name, repository_owner,
            branch_name, user_repo_url, installation_id
        )
        await _update_conversation_build_context_wrapper(
            conversation_id, language, branch_name, repository_name, repository_owner
        )


def _format_clone_success_message(
    use_existing_branch: bool,
    repository_owner: str,
    repository_name: str,
    branch_name: str,
    target_directory: str,
) -> str:
    """Format success message for clone operation.

    Args:
        use_existing_branch: Whether existing branch was used
        repository_owner: Repository owner
        repository_name: Repository name
        branch_name: Branch name
        target_directory: Repository path

    Returns:
        Formatted success message
    """
    if not use_existing_branch:
        github_url = f"https://github.com/{repository_owner}/{repository_name}/tree/{branch_name}"
        full_repo_name = f"{repository_owner}/{repository_name}"
        return (
            f"✅ Repository configured successfully!\n\n"
            f"📦 Repository: {full_repo_name}\n"
            f"🌿 Branch: {branch_name}\n"
            f"🔗 GitHub URL: {github_url}"
        )

    return (
        f"SUCCESS: Repository cloned to {target_directory} "
        f"and checked out existing branch {branch_name}"
    )
