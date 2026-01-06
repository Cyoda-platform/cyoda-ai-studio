"""List and Create chat endpoints."""

import logging
from datetime import timedelta
from typing import Any, Dict

from quart import Blueprint, request
from quart_rate_limiter import rate_limit

from application.routes.chat_endpoints.helpers import get_chat_service
from application.routes.common.auth import get_authenticated_user
from application.routes.common.rate_limiting import default_rate_limit_key
from application.routes.common.response import APIResponse
from common.utils.jwt_utils import TokenExpiredError, TokenValidationError

logger = logging.getLogger(__name__)

list_create_bp = Blueprint("chat_list_create", __name__)


def _parse_list_chats_params(is_superuser: bool) -> tuple[str | None, int, str | None]:
    """Parse and validate list chats query parameters."""
    is_super_request = request.args.get("super", "false").lower() == "true"
    target_user_id = request.args.get("target_user_id")

    try:
        limit = min(int(request.args.get("limit", "100")), 1000)
    except (ValueError, TypeError):
        limit = 100

    point_in_time = request.args.get("point_in_time")

    query_user_id = target_user_id if (is_super_request and is_superuser) else None
    return query_user_id, limit, point_in_time


def _build_list_chats_response(result: Dict[str, Any], point_in_time: str | None) -> Dict[str, Any]:
    """Build the list chats response."""
    return {
        "chats": result["chats"],
        "limit": result["limit"],
        "point_in_time": point_in_time,
        "next_point_in_time": result["next_cursor"],
        "has_more": result["has_more"],
        "cached": result["cached"],
    }


async def _check_guest_chat_limit(user_id: str) -> str | None:
    """Check guest user chat limit. Returns error message if limit exceeded."""
    if not user_id.startswith("guest."):
        return None

    chat_count = await get_chat_service().count_user_chats(user_id)
    if chat_count >= 2:
        return "Guest users can create a maximum of 2 chats."
    return None


async def _parse_create_chat_request() -> tuple[str | None, str | None]:
    """Parse chat name and description from request."""
    if request.is_json:
        data = await request.get_json()
        return data.get("name"), data.get("description")

    form = await request.form
    return form.get("name"), form.get("description")


@list_create_bp.route("", methods=["GET"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def list_chats():
    """List all chats for the current user with keyset pagination."""
    try:
        user_id, is_superuser = await get_authenticated_user()
        query_user_id, limit, point_in_time = _parse_list_chats_params(is_superuser)

        if query_user_id is None:
            query_user_id = user_id

        result = await get_chat_service().list_conversations(
            user_id=query_user_id,
            limit=limit,
            before=point_in_time,
            use_cache=(not point_in_time and limit == 100 and query_user_id is not None),
        )

        return APIResponse.success(_build_list_chats_response(result, point_in_time))

    except TokenExpiredError:
        logger.warning("Token expired in list_chats")
        return APIResponse.error("Token has expired", 401)
    except TokenValidationError as e:
        logger.warning(f"Token validation failed in list_chats: {e}")
        return APIResponse.error("Invalid token", 401)
    except Exception as e:
        logger.exception(f"Error listing chats: {e}")
        return APIResponse.error("Internal server error", 500)


@list_create_bp.route("", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def create_chat():
    """Create a new chat."""
    try:
        user_id, _ = await get_authenticated_user()

        error_message = await _check_guest_chat_limit(user_id)
        if error_message:
            return APIResponse.error(error_message, 403)

        chat_name, chat_description = await _parse_create_chat_request()

        if not chat_name or not chat_name.strip():
            return APIResponse.error("Chat name is required", 400)

        conversation = await get_chat_service().create_conversation(
            user_id=user_id,
            name=chat_name,
            description=chat_description,
        )

        return APIResponse.success({"chat_id": conversation.technical_id}, 201)

    except TokenExpiredError:
        logger.warning("Token expired in create_chat")
        return APIResponse.error("Token has expired", 401)
    except TokenValidationError as e:
        logger.warning(f"Token validation failed in create_chat: {e}")
        return APIResponse.error("Invalid token", 401)
    except Exception as e:
        logger.exception(f"Error creating chat: {e}")
        return APIResponse.error("Internal server error", 500)
