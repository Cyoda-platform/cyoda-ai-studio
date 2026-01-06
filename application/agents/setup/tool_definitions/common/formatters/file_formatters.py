"""Formatters for file operation tools."""

from __future__ import annotations

import json


def format_file_list(files: list[str], count: int) -> str:
    """Format file listing result.

    Args:
        files: List of file paths
        count: Number of files

    Returns:
        JSON string with formatted result
    """
    return json.dumps({"files": files, "count": count}, indent=2)
