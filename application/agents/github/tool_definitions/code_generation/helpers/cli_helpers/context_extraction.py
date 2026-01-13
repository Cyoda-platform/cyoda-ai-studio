"""Context extraction and data structures for CLI operations.

This module handles extracting context values from tool context state
and building CLI context structures.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BackgroundTaskData(BaseModel):
    """Data structure for background task creation."""

    user_id: str
    task_type: str
    name: str
    description: str
    branch_name: str
    language: str
    user_request: str
    conversation_id: Optional[str] = None
    repository_path: str
    repository_type: Optional[str] = None
    repository_url: Optional[str] = None


@dataclass
class CLIContext:
    """Context for CLI operations."""

    requirements: str
    language: str
    repository_path: str
    branch_name: str
    repository_name: str
    tool_context: ToolContext
    session_id: str = "unknown"
    repository_type: Optional[str] = None
    conversation_id: Optional[str] = None


@dataclass
class CLIProcessInfo:
    """Information about started CLI process."""

    process: any
    pid: int
    prompt_file: str
    output_file: str
    task_id: str


def _extract_context_values(
    language: Optional[str],
    repository_path: Optional[str],
    branch_name: Optional[str],
    tool_context: ToolContext,
) -> tuple[str, str, str, str, str, str, str]:
    """Extract context values from parameters and tool context.

    Args:
        language: Programming language
        repository_path: Repository path
        branch_name: Branch name
        tool_context: Tool context

    Returns:
        Tuple of (language, repository_path, branch_name, repository_name, session_id, repository_type, conversation_id)
    """
    language = language or tool_context.state.get("language")
    repository_path = repository_path or tool_context.state.get("repository_path")
    branch_name = branch_name or tool_context.state.get("branch_name")
    repository_name = tool_context.state.get("repository_name", "mcp-cyoda-quart-app")
    session_id = tool_context.state.get("session_id", "unknown")
    repository_type = tool_context.state.get("repository_type")
    conversation_id = tool_context.state.get("conversation_id")

    logger.info(
        f"🔍 Context: language={language}, path={repository_path}, "
        f"branch={branch_name}, repo={repository_name}"
    )

    return (
        language,
        repository_path,
        branch_name,
        repository_name,
        session_id,
        repository_type,
        conversation_id,
    )
