"""Service for repository analysis and scanning."""

# Re-export all public components
from .analysis import RepositoryAnalysisService
from .models import SearchMatch, SearchResult

__all__ = [
    "SearchMatch",
    "SearchResult",
    "RepositoryAnalysisService",
]
