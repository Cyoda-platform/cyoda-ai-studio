"""Data models for repository analysis."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SearchMatch:
    """Search match result."""

    file: str
    matches: List[Dict[str, Any]] = None
    size: Optional[int] = None
    type: Optional[str] = None

    def __post_init__(self):
        if self.matches is None:
            self.matches = []

    def model_dump(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"file": self.file}
        if self.matches:
            result["matches"] = self.matches
        if self.size is not None:
            result["size"] = self.size
        if self.type is not None:
            result["type"] = self.type
        return result
