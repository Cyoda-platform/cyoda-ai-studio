"""GitOperations class for managing local git command operations.

This module provides the main GitOperations class that coordinates various git
operations using the underlying submodules.
"""

# Re-export all public APIs from the git_operations package
from .git_operations import (
    GitOperations,
    GitOperationState,
    DEFAULT_MERGE_STRATEGY,
    NO_CHANGES_TO_PULL_MSG,
    NOTHING_TO_COMMIT_MSG,
)

__all__ = [
    "GitOperations",
    "GitOperationState",
    "DEFAULT_MERGE_STRATEGY",
    "NO_CHANGES_TO_PULL_MSG",
    "NOTHING_TO_COMMIT_MSG",
]
