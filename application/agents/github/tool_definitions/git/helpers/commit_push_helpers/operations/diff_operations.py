"""Diff parsing and categorization operations.

This module handles parsing git diff output and categorizing changes by type
(added, modified, deleted).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from application.agents.github.tool_definitions.common.constants import (
    DIFF_CATEGORY_ADDED,
    DIFF_CATEGORY_DELETED,
    DIFF_CATEGORY_MODIFIED,
)

logger = logging.getLogger(__name__)


@dataclass
class DiffResult:
    """Result of git diff operation."""

    changed_files: list
    diff_summary: dict


def _parse_diff_line(line: str) -> Optional[tuple[str, str]]:
    """Parse a single diff status line into status and file path.

    Args:
        line: Single line from git diff output (status\tpath)

    Returns:
        Tuple of (status, file_path) or None if parse fails
    """
    if not line:
        return None

    parts = line.split("\t", 1)
    if len(parts) == 2:
        return parts[0], parts[1]

    return None


def _categorize_diff_changes(diff_output: str) -> tuple[list, dict]:
    """Categorize diff output by change type (added, modified, deleted).

    Args:
        diff_output: Raw git diff output

    Returns:
        Tuple of (changed_files_list, diff_summary_dict)
    """
    changed_files = []
    added_files = []
    modified_files = []
    deleted_files = []

    for line in diff_output.strip().split("\n"):
        parsed = _parse_diff_line(line)
        if not parsed:
            continue

        status, file_path = parsed

        if status == "A":
            added_files.append(file_path)
            changed_files.append(file_path)
        elif status == "M":
            modified_files.append(file_path)
            changed_files.append(file_path)
        elif status == "D":
            deleted_files.append(file_path)
            changed_files.append(file_path)

    diff_summary = {
        DIFF_CATEGORY_ADDED: added_files,
        DIFF_CATEGORY_MODIFIED: modified_files,
        DIFF_CATEGORY_DELETED: deleted_files,
    }

    logger.info(
        f"📝 Diff summary: {len(added_files)} added, "
        f"{len(modified_files)} modified, {len(deleted_files)} deleted"
    )

    return changed_files, diff_summary


async def _get_staged_diff(repository_path: str) -> DiffResult:
    """Get diff of staged changes before committing.

    Args:
        repository_path: Path to repository

    Returns:
        DiffResult with changed files and summary
    """
    changed_files = []
    diff_summary = {}

    try:
        logger.info("📝 Getting diff of staged changes...")

        # Step 1: Execute git diff command
        diff_process = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "--cached",
            "--name-status",
            cwd=repository_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        diff_stdout, diff_stderr = await diff_process.communicate()

        # Step 2: Parse output if successful
        if diff_process.returncode == 0:
            diff_output = diff_stdout.decode("utf-8", errors="replace")
            changed_files, diff_summary = _categorize_diff_changes(diff_output)

    except Exception as e:
        logger.warning(f"⚠️ Could not get diff: {e}")

    return DiffResult(changed_files=changed_files, diff_summary=diff_summary)
