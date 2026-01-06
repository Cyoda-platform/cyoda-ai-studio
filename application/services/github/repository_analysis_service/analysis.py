"""Core analysis logic and methods for repository scanning.

This module provides a backward-compatible wrapper for the refactored analysis package.
All functionality has been split into focused modules within analysis/.
"""

# Re-export all public APIs from the package
from .analysis import (
    RepositoryAnalysisService,
    SearchMatch,
    ResourceScanner,
)

__all__ = [
    "RepositoryAnalysisService",
    "SearchMatch",
    "ResourceScanner",
]
