"""Data models for repository analysis."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SearchMatch(BaseModel):
    """A single search match."""

    file: str
    matches: List[Dict[str, Any]] = []
    size: Optional[int] = None
    type: str = "file"


class SearchResult(BaseModel):
    """Search result container."""

    search_type: str
    search_pattern: str
    file_pattern: str
    repository_path: str
    matches: List[SearchMatch] = []
    summary: Dict[str, Any]
