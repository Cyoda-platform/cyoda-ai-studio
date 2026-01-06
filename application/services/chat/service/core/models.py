"""Data models for chat service."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class CacheResult(BaseModel):
    """Result from cache lookup operation."""

    hit: bool
    chats: List[Dict] = []
    cache_age: Optional[float] = None


class PaginationResult(BaseModel):
    """Pagination information for chat list."""

    has_more: bool
    next_cursor: Optional[str] = None
    total_returned: int = 0
