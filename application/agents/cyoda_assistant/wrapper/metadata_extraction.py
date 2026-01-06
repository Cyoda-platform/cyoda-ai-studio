"""Metadata extraction operations for CyodaAssistantWrapper.

Handles extraction of UI functions, repository info, and task IDs from session state.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _extract_metadata_from_session(
    final_session_state: dict[str, Any]
) -> dict[str, Any]:
    """Extract metadata from final session state.

    Args:
        final_session_state: Final session state after agent execution

    Returns:
        Dictionary containing UI functions, repository info, and build task ID
    """
    # Extract UI functions from session state (if any tools added them)
    ui_functions = final_session_state.get("ui_functions", [])
    if ui_functions:
        logger.info(f"Found {len(ui_functions)} UI function(s) in session state")

    # Extract repository info from session state (set by build agent tools)
    repository_info = None
    if (
        final_session_state.get("repository_name")
        and final_session_state.get("repository_owner")
        and final_session_state.get("branch_name")
    ):
        repository_info = {
            "repository_name": final_session_state.get("repository_name"),
            "repository_owner": final_session_state.get("repository_owner"),
            "repository_branch": final_session_state.get("branch_name"),
        }
        logger.info(f"📦 Repository info from session state: {repository_info}")

    # Extract build task ID from session state (set by build agent)
    build_task_id = final_session_state.get("build_task_id")
    if build_task_id:
        logger.info(f"📋 Build task ID from session state: {build_task_id}")

    return {
        "ui_functions": ui_functions,
        "repository_info": repository_info,
        "build_task_id": build_task_id,
    }
