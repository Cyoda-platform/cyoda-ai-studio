"""Tool for searching repository files.

This module handles flexible repository file searching using Linux tools
like find, grep, ls, and file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from .command_execution import (
    execute_find_command,
    get_matching_lines,
    get_directory_contents,
    get_file_type,
)
from .search_handlers import (
    search_content,
    search_filename,
    search_structure,
    search_filetype,
    route_search,
)

logger = logging.getLogger(__name__)


async def search_repository_files(
    search_pattern: str,
    file_pattern: str = "*",
    search_type: str = "content",
    tool_context: ToolContext = None,
) -> str:
    """Search repository files using Linux tools and regular expressions.

    This is an agentic tool that allows flexible repository exploration using:
    - find: Locate files by name/path patterns
    - grep: Search file contents with regex
    - ls: List directory contents
    - file: Identify file types

    Args:
        search_pattern: Search pattern (regex for content, glob for files)
        file_pattern: File pattern to search in (e.g., "*.json", "*.md", "**/version_*/*")
        search_type: Type of search - "content", "filename", "structure", "filetype"
        tool_context: Execution context

    Returns:
        JSON string with search results
    """
    try:
        if not tool_context:
            return json.dumps({"error": "Tool context not available"})

        repository_path = tool_context.state.get("repository_path")
        if not repository_path:
            return json.dumps({"error": "Repository path not found in context"})

        repo_path = Path(repository_path)
        if not repo_path.exists():
            return json.dumps(
                {"error": f"Repository path does not exist: {repository_path}"}
            )

        matches = await route_search(search_type, repo_path, search_pattern, file_pattern)

        results = {
            "search_type": search_type,
            "search_pattern": search_pattern,
            "file_pattern": file_pattern,
            "repository_path": str(repository_path),
            "matches": matches,
            "summary": {
                "total_matches": len(matches),
                "search_completed": True,
            },
        }

        logger.info(
            f"🔍 Search completed: {len(matches)} matches for "
            f"'{search_pattern}' ({search_type})"
        )

        return json.dumps(results, indent=2)

    except Exception as e:
        logger.error(f"Error in repository search: {e}", exc_info=True)
        return json.dumps(
            {
                "error": str(e),
                "search_type": search_type,
                "search_pattern": search_pattern,
            }
        )


__all__ = [
    # Main function
    "search_repository_files",
    # Command execution
    "execute_find_command",
    "get_matching_lines",
    "get_directory_contents",
    "get_file_type",
    # Search handlers
    "search_content",
    "search_filename",
    "search_structure",
    "search_filetype",
    "route_search",
]
