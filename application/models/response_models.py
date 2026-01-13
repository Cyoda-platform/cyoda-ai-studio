"""
Response models for AI Assistant API.

Defines all response DTOs used by the API endpoints.
Compatible with existing UI expectations.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )


class SuccessResponse(BaseModel):
    """Standard success response."""

    message: str = Field(..., description="Success message")
    technical_id: Optional[str] = Field(
        default=None,
        alias="technicalId",
        description="Technical ID of created/updated entity",
    )


class TokenResponse(BaseModel):
    """Response model for token generation."""

    access_token: str = Field(..., alias="accessToken", description="JWT access token")


class ChatListResponse(BaseModel):
    """Response model for listing chats."""

    chats: List[Dict[str, Any]] = Field(..., description="List of chat conversations")


class ChatDetailResponse(BaseModel):
    """Response model for chat details."""

    chat_body: Dict[str, Any] = Field(
        ...,
        alias="chatBody",
        description="Full chat conversation data including dialogue",
    )


class CanvasQuestionResponse(BaseModel):
    """Response model for canvas questions."""

    message: str = Field(..., description="Response message")
    hook: Optional[Dict[str, Any]] = Field(
        default=None, description="Hook data for UI preview (type, action, data)"
    )
