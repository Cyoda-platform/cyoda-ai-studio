"""Service for repository analysis and scanning.

All implementation has been moved to repository_analysis_service/ subdirectory.
This file maintains backward compatibility by re-exporting all components.
"""

# Re-export all public components for backward compatibility
from .repository_analysis_service import (
    SearchMatch,
    SearchResult,
    RepositoryAnalysisService,
)

__all__ = [
    "SearchMatch",
    "SearchResult",
    "RepositoryAnalysisService",
]
