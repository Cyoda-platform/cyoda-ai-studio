"""Formatters for context tools."""

from __future__ import annotations

import json


def format_build_context(
    success: bool,
    language: str | None = None,
    branch_name: str | None = None,
    source: str | None = None,
    error: str | None = None,
) -> str:
    """Format build context result.

    Args:
        success: Whether retrieval was successful
        language: Programming language
        branch_name: Git branch name
        source: Source of the context data
        error: Error message if any

    Returns:
        JSON string with formatted result
    """
    result = {"success": success}

    if success:
        result["language"] = language
        result["branch_name"] = branch_name
        result["source"] = source
    else:
        result["error"] = error

    return json.dumps(result, indent=2)


def format_user_info(
    user_logged_in: bool,
    user_id: str,
    cyoda_url: str,
    cyoda_status: str,
    **workflow_cache,
) -> str:
    """Format comprehensive user info.

    Args:
        user_logged_in: Whether user is logged in
        user_id: User ID
        cyoda_url: Cyoda environment URL
        cyoda_status: Cyoda environment status
        **workflow_cache: Additional workflow cache data

    Returns:
        Formatted string with user and workflow information
    """
    info = {
        "user_logged_in_most_recent_status": user_logged_in,
        "user_id": user_id,
        "cyoda_env_most_recent_url": cyoda_url,
        "cyoda_environment_most_recent_status": cyoda_status,
    }
    info.update(workflow_cache)

    info_json = json.dumps(info, indent=2)
    return (
        "Please base your answer on this comprehensive information about the "
        f"user and workflow context:\n{info_json}"
    )
