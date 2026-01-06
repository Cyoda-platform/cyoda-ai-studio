"""Commit and diff operations for CLI process monitoring."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.common.constants import (
    COMMIT_TIMEOUT,
    DIFF_CATEGORY_ADDED,
    DIFF_CATEGORY_DELETED,
    DIFF_CATEGORY_MODIFIED,
    DIFF_CATEGORY_UNTRACKED,
)
from application.agents.github.tool_definitions.git import _commit_and_push_changes
from application.agents.github.tool_definitions.repository import get_repository_diff

logger = logging.getLogger(__name__)


@dataclass
class AuthInfo:
    """Authentication information for git operations."""

    repository_type: Optional[str] = None
    repo_url: Optional[str] = None
    installation_id: Optional[str] = None


def _extract_auth_info(tool_context: Optional[ToolContext]) -> AuthInfo:
    """Extract authentication info from tool context.

    Args:
        tool_context: Tool context with auth information

    Returns:
        AuthInfo object with extracted credentials
    """
    if not tool_context:
        return AuthInfo()

    auth_info = AuthInfo(
        repository_type=tool_context.state.get("repository_type"),
        repo_url=tool_context.state.get("user_repository_url")
        or tool_context.state.get("repository_url"),
        installation_id=tool_context.state.get("installation_id"),
    )

    logger.info(
        f"🔐 Extracted auth info - type: {auth_info.repository_type}, "
        f"url: {auth_info.repo_url}, inst_id: {auth_info.installation_id}"
    )

    return auth_info


async def _get_diff_summary(tool_context: Optional[ToolContext]) -> tuple[list, dict]:
    """Get diff summary of changed files.

    Args:
        tool_context: Tool context for diff operation

    Returns:
        Tuple of (changed_files list, diff_summary dict)
    """
    changed_files = []
    diff_summary = {}

    if not tool_context:
        return changed_files, diff_summary

    try:
        diff_result = await get_repository_diff(tool_context)
        diff_data = json.loads(diff_result)

        for category in [
            DIFF_CATEGORY_MODIFIED,
            DIFF_CATEGORY_ADDED,
            DIFF_CATEGORY_UNTRACKED,
        ]:
            changed_files.extend(diff_data.get(category, []))

        diff_summary = {
            DIFF_CATEGORY_ADDED: diff_data.get(DIFF_CATEGORY_ADDED, []),
            DIFF_CATEGORY_MODIFIED: diff_data.get(DIFF_CATEGORY_MODIFIED, []),
            DIFF_CATEGORY_DELETED: diff_data.get(DIFF_CATEGORY_DELETED, []),
            DIFF_CATEGORY_UNTRACKED: diff_data.get(DIFF_CATEGORY_UNTRACKED, []),
        }
    except Exception as e:
        logger.warning(f"Could not get diff: {e}")

    return changed_files, diff_summary


async def _send_initial_commit(
    repository_path: str,
    branch_name: str,
    tool_context: Optional[ToolContext],
    auth_info: AuthInfo,
) -> Optional[float]:
    """Send initial commit when process starts.

    Args:
        repository_path: Path to repository
        branch_name: Branch name
        tool_context: Tool context
        auth_info: Authentication information

    Returns:
        Timestamp of successful commit, None if failed
    """
    if not tool_context:
        return None

    try:
        logger.info(f"🔍 [{branch_name}] Sending initial commit...")
        await asyncio.wait_for(
            _commit_and_push_changes(
                repository_path=repository_path,
                branch_name=branch_name,
                tool_context=tool_context,
                repo_url=auth_info.repo_url,
                installation_id=auth_info.installation_id,
                repository_type=auth_info.repository_type,
            ),
            timeout=COMMIT_TIMEOUT,
        )
        logger.info(f"✅ [{branch_name}] Initial commit completed")
        return asyncio.get_event_loop().time()
    except asyncio.TimeoutError:
        logger.warning(
            f"⚠️ [{branch_name}] Initial commit timed out after {COMMIT_TIMEOUT}s"
        )
    except Exception as e:
        logger.error(
            f"❌ [{branch_name}] Failed to send initial commit: {e}",
            exc_info=True,
        )

    return None


async def _send_final_commit(
    repository_path: str,
    branch_name: str,
    tool_context: Optional[ToolContext],
    auth_info: AuthInfo,
) -> None:
    """Push any remaining changes before marking as complete.

    Args:
        repository_path: Path to repository
        branch_name: Branch name
        tool_context: Tool context
        auth_info: Authentication information
    """
    if not tool_context:
        return

    try:
        await asyncio.wait_for(
            _commit_and_push_changes(
                repository_path=repository_path,
                branch_name=branch_name,
                tool_context=tool_context,
                repo_url=auth_info.repo_url,
                installation_id=auth_info.installation_id,
                repository_type=auth_info.repository_type,
            ),
            timeout=COMMIT_TIMEOUT,
        )
        logger.info(f"✅ [{branch_name}] Final commit pushed")
    except asyncio.TimeoutError:
        logger.warning(
            f"⚠️ [{branch_name}] Final commit timed out after {COMMIT_TIMEOUT}s"
        )
    except Exception as e:
        logger.warning(f"⚠️ [{branch_name}] Failed to push final changes: {e}")


async def _commit_progress(
    repository_path: str,
    branch_name: str,
    tool_context: Optional[ToolContext],
    auth_info: AuthInfo,
) -> Optional[dict]:
    """Commit and push progress changes.

    Args:
        repository_path: Path to repository
        branch_name: Branch name
        tool_context: Tool context
        auth_info: Authentication information

    Returns:
        Commit result dictionary or None
    """
    try:
        commit_result = await asyncio.wait_for(
            _commit_and_push_changes(
                repository_path=repository_path,
                branch_name=branch_name,
                tool_context=tool_context,
                repo_url=auth_info.repo_url,
                installation_id=auth_info.installation_id,
                repository_type=auth_info.repository_type,
            ),
            timeout=COMMIT_TIMEOUT,
        )
        logger.info(f"✅ [{branch_name}] Progress commit completed")
        return commit_result
    except asyncio.TimeoutError:
        logger.warning(
            f"⚠️ [{branch_name}] Progress commit timed out after {COMMIT_TIMEOUT}s"
        )
    except Exception as e:
        logger.warning(f"⚠️ [{branch_name}] Failed to commit/push: {e}")

    return None
