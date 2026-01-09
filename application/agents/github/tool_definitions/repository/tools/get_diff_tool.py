"""Tool for getting repository diff information.

This module handles retrieving uncommitted changes from the repository.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from application.agents.github.tool_definitions.common.constants import (
    DIFF_CATEGORY_ADDED,
    DIFF_CATEGORY_DELETED,
    DIFF_CATEGORY_MODIFIED,
    DIFF_CATEGORY_UNTRACKED,
    GIT_CMD,
    GIT_PORCELAIN_FLAG,
    GIT_STATUS,
    GIT_STATUS_ADDED,
    GIT_STATUS_DELETED,
    GIT_STATUS_MODIFIED,
    GIT_STATUS_UNTRACKED,
)
from application.agents.github.tool_definitions.common.utils import (
    ensure_repository_available,
)

logger = logging.getLogger(__name__)

# Diff constants
REPO_PATH_NOT_FOUND = (
    "ERROR: repository_path not found in context. Repository must be cloned first."
)
REPO_UNAVAILABLE = "ERROR: {message}"
DIFF_ERROR = "ERROR: {error}"
REPO_CHANGES_LOG = "Repository has {total} uncommitted changes"


class RepositoryChanges(BaseModel):
    """Repository changes structure."""

    modified: List[str] = []
    added: List[str] = []
    deleted: List[str] = []
    untracked: List[str] = []

    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary format.

        Returns:
            Dictionary with changes organized by category
        """
        return {
            DIFF_CATEGORY_MODIFIED: self.modified,
            DIFF_CATEGORY_ADDED: self.added,
            DIFF_CATEGORY_DELETED: self.deleted,
            DIFF_CATEGORY_UNTRACKED: self.untracked,
        }

    @property
    def total(self) -> int:
        """Get total number of changes.

        Returns:
            Total count of all changes
        """
        return (
            len(self.modified)
            + len(self.added)
            + len(self.deleted)
            + len(self.untracked)
        )


async def _extract_repository_path(
    tool_context: ToolContext,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Extract and validate repository path from context.

    Args:
        tool_context: The ADK tool context

    Returns:
        Tuple of (is_valid, error_message, repository_path)
    """
    repository_path = tool_context.state.get("repository_path")
    if not repository_path:
        return False, REPO_PATH_NOT_FOUND, None

    return True, None, repository_path


async def _ensure_repo_available(
    repository_path: str, tool_context: ToolContext
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Ensure repository is available locally.

    Args:
        repository_path: Repository path
        tool_context: The ADK tool context

    Returns:
        Tuple of (is_valid, error_message, repository_path)
    """
    success, message, repository_path = await ensure_repository_available(
        repository_path=repository_path,
        tool_context=tool_context,
        require_git=True,
    )

    if not success:
        return False, REPO_UNAVAILABLE.format(message=message), None

    return True, None, repository_path


def _parse_git_status_output(output: str) -> RepositoryChanges:
    """Parse git status porcelain output into RepositoryChanges.

    Args:
        output: Git status output (porcelain format)

    Returns:
        RepositoryChanges object with parsed changes
    """
    changes = RepositoryChanges()

    for line in output.strip().split("\n"):
        if not line:
            continue

        status = line[:2]
        file_path = line[3:]

        if status.strip() == GIT_STATUS_MODIFIED:
            changes.modified.append(file_path)
        elif status.strip() == GIT_STATUS_ADDED:
            changes.added.append(file_path)
        elif status.strip() == GIT_STATUS_DELETED:
            changes.deleted.append(file_path)
        elif status.strip() == GIT_STATUS_UNTRACKED:
            changes.untracked.append(file_path)

    return changes


async def get_repository_diff(tool_context: ToolContext) -> str:
    """Get diff of uncommitted changes in the repository.

    Returns a summary of what files have been modified, added, or deleted
    since the last commit.

    Args:
        tool_context: The ADK tool context

    Returns:
        JSON string with diff information

    Example:
        >>> diff = await get_repository_diff(tool_context=context)
        >>> print(diff)
    """
    try:
        # Step 1: Extract and validate repository path
        is_valid, error_msg, repository_path = await _extract_repository_path(
            tool_context
        )
        if not is_valid:
            return error_msg

        # Step 2: Ensure repository is available
        is_ready, error_msg, repository_path = await _ensure_repo_available(
            repository_path, tool_context
        )
        if not is_ready:
            return error_msg

        # Step 3: Get git status
        result = subprocess.run(
            [GIT_CMD, GIT_STATUS, GIT_PORCELAIN_FLAG],
            cwd=repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

        # Step 4: Parse git status output
        changes = _parse_git_status_output(result.stdout)
        logger.info(REPO_CHANGES_LOG.format(total=changes.total))

        # Step 5: Return as JSON
        return json.dumps(changes.to_dict(), indent=2)

    except Exception as e:
        logger.error(f"Error getting repository diff: {e}", exc_info=True)
        return DIFF_ERROR.format(error=str(e))
