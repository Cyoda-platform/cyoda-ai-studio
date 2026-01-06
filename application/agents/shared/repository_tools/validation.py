"""Validation module."""

import logging

from .constants import PROTECTED_BRANCHES

logger = logging.getLogger(__name__)


def _validate_clone_parameters(language: str, branch_name: str) -> None:
    """
    Validate clone repository parameters.

    Raises:
        ValueError: If validation fails
    """
    if not language:
        raise ValueError("language parameter is required and cannot be empty")
    if not branch_name:
        raise ValueError("branch_name parameter is required and cannot be empty")




async def _is_protected_branch(branch_name: str) -> bool:
    """
    Check if a branch name is protected.

    Protected branches (main, master, develop, etc.) should NEVER be used for builds.

    Args:
        branch_name: Branch name to check

    Returns:
        True if branch is protected, False otherwise
    """
    return branch_name.lower().strip() in PROTECTED_BRANCHES




