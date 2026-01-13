"""
Request models for AI Assistant API.

Defines all request DTOs used by the API endpoints.
Compatible with existing UI expectations.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class CreateChatRequest(BaseModel):
    """Request model for creating a new chat conversation."""

    name: Optional[str] = Field(
        default=None, description="Display name for the conversation"
    )
    description: Optional[str] = Field(
        default=None, description="Optional description of the conversation"
    )
    message: Optional[str] = Field(
        default=None, description="Optional initial message to send with chat creation"
    )


class UpdateChatRequest(BaseModel):
    """Request model for updating chat metadata."""

    chat_name: Optional[str] = Field(
        default=None, alias="chatName", description="New name for the conversation"
    )
    chat_description: Optional[str] = Field(
        default=None,
        alias="chatDescription",
        description="New description for the conversation",
    )


class SubmitAnswerRequest(BaseModel):
    """Request model for submitting an answer/message to a chat."""

    answer: str = Field(..., description="The message/answer content")


class CanvasQuestionRequest(BaseModel):
    """
    Request model for canvas questions (stateless AI generation).

    Used to generate entity configs, workflow configs, etc. without
    creating a persistent conversation.
    """

    chat_id: Optional[str] = Field(
        default=None, alias="chatId", description="Optional chat ID to associate with"
    )
    question: str = Field(..., description="The question/prompt for generation")
    response_type: str = Field(
        ...,
        alias="responseType",
        description=(
            "Type of response: entity_json, workflow_json, app_config_json, "
            "environment_json, requirement_json, text"
        ),
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for generation (app_name, existing_entities, etc.)",
    )


class TransferChatsRequest(BaseModel):
    """Request model for transferring guest chats to authenticated user."""

    guest_token: str = Field(
        ..., alias="guestToken", description="JWT token of the guest user"
    )
