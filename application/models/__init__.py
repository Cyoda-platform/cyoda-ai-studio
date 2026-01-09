"""
Application models package.

Contains all request and response DTOs for the AI Assistant API.
"""

from application.models.request_models import (
    CanvasQuestionRequest,
    CreateChatRequest,
    SubmitAnswerRequest,
    TransferChatsRequest,
    UpdateChatRequest,
)
from application.models.response_models import (
    CanvasQuestionResponse,
    ChatDetailResponse,
    ChatListResponse,
    ErrorResponse,
    SuccessResponse,
    TokenResponse,
)

__all__ = [
    # Request models
    "CanvasQuestionRequest",
    "CreateChatRequest",
    "SubmitAnswerRequest",
    "TransferChatsRequest",
    "UpdateChatRequest",
    # Response models
    "CanvasQuestionResponse",
    "ChatDetailResponse",
    "ChatListResponse",
    "ErrorResponse",
    "SuccessResponse",
    "TokenResponse",
]
