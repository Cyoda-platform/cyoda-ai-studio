"""Service for repository analysis and scanning."""

# Re-export all public components
from .models import SearchMatch, SearchResult
from .analysis import RepositoryAnalysisService

__all__ = [
    "SearchMatch",
    "SearchResult",
    "RepositoryAnalysisService",
]
