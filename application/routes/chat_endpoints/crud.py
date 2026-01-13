"""Get, Update, Delete chat endpoints."""

import logging
from datetime import timedelta
from typing import Any, Dict

from quart import Blueprint, request
from quart_rate_limiter import rate_limit

from application.entity.conversation import Conversation
from application.routes.chat_endpoints.helpers import get_chat_service
from application.routes.common.auth import get_authenticated_user
from application.routes.common.rate_limiting import default_rate_limit_key
from application.routes.common.response import APIResponse
from common.utils.jwt_utils import TokenExpiredError, TokenValidationError
from services.services import get_repository

logger = logging.getLogger(__name__)

crud_bp = Blueprint("chat_crud", __name__)


def _build_entities_data(conversation: Conversation) -> Dict[str, Any]:
    """Build entities data with workflow information."""
    entities_data = {}
    if hasattr(conversation, "entities") and conversation.entities:
        for entity in conversation.entities:
            entity_data = {
                "name": entity.get("name", ""),
                "type": entity.get("type", ""),
            }
            if "workflows" in entity:
                entity_data["workflows"] = entity["workflows"]
            entities_data[entity.get("id", "")] = entity_data
    return entities_data


def _build_chat_body(
    conversation: Conversation, dialogue: list[Dict[str, Any]]
) -> Dict[str, Any]:
    """Build the chat response body."""
    body = {
        "id": conversation.technical_id,
        "name": conversation.name,
        "description": conversation.description,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "entities": _build_entities_data(conversation),
        "dialogue": dialogue,
    }

    # Add repository information if available
    if conversation.repository_name:
        body["repository_name"] = conversation.repository_name
    if conversation.repository_owner:
        body["repository_owner"] = conversation.repository_owner
    if conversation.repository_branch:
        body["repository_branch"] = conversation.repository_branch
    if conversation.repository_url:
        body["repository_url"] = conversation.repository_url
    if conversation.installation_id:
        body["installation_id"] = conversation.installation_id

    return body


async def _prepare_chat_body(
    technical_id: str, conversation: Conversation
) -> Dict[str, Any]:
    """Prepare chat body with messages and dialogue."""
    repo = get_repository()
    await conversation.populate_messages_from_edge_messages(repo)
    dialogue = conversation.get_dialogue()
    return _build_chat_body(conversation, dialogue)


async def _apply_chat_updates(conversation: Conversation, data: Dict[str, Any]) -> None:
    """Apply updates to conversation from request data."""
    if "chat_name" in data:
        conversation.name = data["chat_name"]
    if "chat_description" in data:
        conversation.description = data["chat_description"]


@crud_bp.route("/<technical_id>", methods=["GET"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def get_chat(technical_id: str):
    """Get specific chat by ID."""
    try:
        user_id, is_superuser = await get_authenticated_user()
        is_super_request = request.args.get("super", "false").lower() == "true"
        effective_super = is_super_request and is_superuser

        service = get_chat_service()
        conversation = await service.get_conversation(technical_id)

        if not conversation:
            return APIResponse.error("Chat not found", 404)

        try:
            service.validate_ownership(conversation, user_id, effective_super)
        except PermissionError:
            return APIResponse.error("Access denied", 403)

        chat_body = await _prepare_chat_body(technical_id, conversation)
        return APIResponse.success({"chat_body": chat_body})

    except TokenExpiredError:
        logger.warning("Token expired in get_chat")
        return APIResponse.error("Token has expired", 401)
    except TokenValidationError as e:
        logger.warning(f"Token validation failed in get_chat: {e}")
        return APIResponse.error("Invalid token", 401)
    except Exception as e:
        logger.exception(f"Error getting chat: {e}")
        return APIResponse.error("Internal server error", 500)


@crud_bp.route("/<technical_id>", methods=["PUT"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def update_chat(technical_id: str):
    """Update chat name/description."""
    try:
        user_id, is_superuser = await get_authenticated_user()
        service = get_chat_service()

        conversation = await service.get_conversation(technical_id)
        if not conversation:
            return APIResponse.error("Chat not found", 404)

        try:
            service.validate_ownership(conversation, user_id, is_superuser)
        except PermissionError:
            return APIResponse.error("Access denied", 403)

        data = await request.get_json()
        await _apply_chat_updates(conversation, data)
        await service.update_conversation(conversation)
        return APIResponse.success({"message": "Chat updated successfully"})

    except TokenExpiredError:
        logger.warning("Token expired")
        return APIResponse.error("Token has expired", 401)
    except TokenValidationError as e:
        logger.warning(f"Token validation failed: {e}")
        return APIResponse.error("Invalid token", 401)
    except Exception as e:
        logger.exception(f"Error updating chat: {e}")
        return APIResponse.error("Internal server error", 500)


@crud_bp.route("/<technical_id>", methods=["DELETE"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def delete_chat(technical_id: str):
    """Delete a chat."""
    try:
        user_id, is_superuser = await get_authenticated_user()
        service = get_chat_service()

        conversation = await service.get_conversation(technical_id)
        if not conversation:
            return APIResponse.error("Chat not found", 404)

        try:
            service.validate_ownership(conversation, user_id, is_superuser)
        except PermissionError:
            return APIResponse.error("Access denied", 403)

        await service.delete_conversation(technical_id, user_id)
        return APIResponse.success({"message": "Chat deleted successfully"})

    except TokenExpiredError:
        logger.warning("Token expired")
        return APIResponse.error("Token has expired", 401)
    except TokenValidationError as e:
        logger.warning(f"Token validation failed: {e}")
        return APIResponse.error("Invalid token", 401)
    except Exception as e:
        logger.exception(f"Error deleting chat: {e}")
        return APIResponse.error("Internal server error", 500)
