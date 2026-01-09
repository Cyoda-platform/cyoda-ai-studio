"""
Git operations module for local repository management.

This module has been refactored into a package structure with focused modules.
All classes and functions are re-exported from the subpackage for backward compatibility.

Original file: 771 lines
After split: 3 focused modules (url_management, branch_management, local_operations)
All imports remain the same - this is a transparent refactoring.
"""

# Re-export all classes from the operations subpackage
from .operations import GitOperations, GitOperationState

__all__ = [
    "GitOperationState",
    "GitOperations",
]
