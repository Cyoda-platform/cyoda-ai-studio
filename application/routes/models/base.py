"""
Base models for API requests and responses.

Provides common patterns and base classes for all endpoint models.
"""

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """
    Standard success response wrapper.

    Generic response that wraps successful data returns.
    """

    model_config = ConfigDict(populate_by_name=True)

    data: T = Field(..., description="Response data")
    status: str = Field(default="success", description="Response status")


class ErrorResponse(BaseModel):
    """
    Standard error response.

    Consistent error format across all endpoints.
    """

    model_config = ConfigDict(populate_by_name=True)

    error: str = Field(..., description="Error message")
    details: Optional[Any] = Field(None, description="Additional error details")
    status: str = Field(default="error", description="Response status")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response wrapper.

    Generic response for paginated list endpoints.
    """

    model_config = ConfigDict(populate_by_name=True)

    items: List[T] = Field(..., description="List of items")
    limit: int = Field(..., description="Page size limit")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")
    has_more: bool = Field(..., description="Whether more items exist")
    total: Optional[int] = Field(None, description="Total count (if available)")
    cached: bool = Field(default=False, description="Whether response is from cache")
