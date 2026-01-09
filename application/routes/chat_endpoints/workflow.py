"""Workflow control and file download endpoints."""

import logging
from datetime import timedelta
from typing import Any, Dict

from quart import Blueprint, Response, jsonify, request
from quart_rate_limiter import rate_limit

from application.routes.chat_endpoints.helpers import get_chat_service
from application.routes.common.rate_limiting import default_rate_limit_key
from application.routes.common.response import APIResponse
from common.utils.jwt_utils import (
    TokenExpiredError,
    TokenValidationError,
    get_user_info_from_token,
)

logger = logging.getLogger(__name__)

workflow_bp = Blueprint("chat_workflow", __name__)


async def _get_conversation(technical_id: str):
    """Get conversation by ID."""
    service = get_chat_service()
    return await service.get_conversation(technical_id)


async def _extract_guest_token() -> str | None:
    """Extract guest token from request."""
    data = await request.get_json()
    return data.get("guest_token")


def _validate_transfer_request(
    current_user_id: str, guest_token: str | None
) -> str | None:
    """Validate transfer request. Returns error message if invalid."""
    if current_user_id.startswith("guest."):
        return "Cannot transfer chats to guest user"
    if not guest_token:
        return "guest_token is required"
    return None


def _extract_and_validate_guest_user(guest_token: str) -> tuple[str | None, str | None]:
    """Extract and validate guest user from token. Returns (user_id, error_message)."""
    try:
        guest_user_id, _ = get_user_info_from_token(guest_token)
    except (TokenValidationError, TokenExpiredError) as e:
        logger.warning(f"Invalid guest token: {e}")
        return None, "Invalid guest token"

    if not guest_user_id.startswith("guest."):
        return None, "Token is not a guest token"

    return guest_user_id, None


@workflow_bp.route("/<technical_id>/approve", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def approve(technical_id: str) -> tuple[Any, int]:
    """Approve current state and proceed (workflow control)."""
    try:
        conversation = await _get_conversation(technical_id)
        if not conversation:
            return jsonify({"error": "Chat not found"}), 404

        # TODO: Phase 4 - implement workflow transitions
        return jsonify({"message": "Approved successfully"}), 200
    except Exception as e:
        logger.exception(f"Error approving: {e}")
        return jsonify({"error": str(e)}), 500


@workflow_bp.route("/<technical_id>/rollback", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def rollback(technical_id: str) -> tuple[Any, int]:
    """Rollback to previous state (workflow control)."""
    try:
        conversation = await _get_conversation(technical_id)
        if not conversation:
            return jsonify({"error": "Chat not found"}), 404

        # TODO: Phase 4 - implement workflow transitions
        return jsonify({"message": "Rolled back successfully"}), 200
    except Exception as e:
        logger.exception(f"Error rolling back: {e}")
        return jsonify({"error": str(e)}), 500


@workflow_bp.route("/<technical_id>/files/<blob_id>", methods=["GET"])
async def download_file(
    technical_id: str, blob_id: str
) -> tuple[Response | Dict[str, Any], int]:
    """Download a file by blob ID from a chat."""
    try:
        conversation = await _get_conversation(technical_id)
        if not conversation:
            return jsonify({"error": "Chat not found"}), 404

        # TODO: Phase 2 - implement real file download from Cyoda blobs
        # Mock file download for now
        mock_content = f"Mock file content for blob {blob_id}".encode()

        response = Response(
            mock_content,
            mimetype="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="mock_file_{blob_id}.txt"',
                "Content-Length": str(len(mock_content)),
                "Cache-Control": "no-cache",
            },
        )
        return response, 200
    except Exception as e:
        logger.exception(f"Error downloading file: {e}")
        return jsonify({"error": str(e)}), 500


@workflow_bp.route("/transfer", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def transfer_chats():
    """Transfer guest chats to authenticated user."""
    from application.routes.common.auth import get_authenticated_user

    try:
        current_user_id, _ = await get_authenticated_user()
        guest_token = await _extract_guest_token()

        error_msg = _validate_transfer_request(current_user_id, guest_token)
        if error_msg:
            return APIResponse.error(error_msg, 400)

        guest_user_id, error_msg = _extract_and_validate_guest_user(guest_token)
        if error_msg:
            return APIResponse.error(error_msg, 400)

        try:
            transferred_count = await get_chat_service().transfer_guest_chats(
                guest_user_id=guest_user_id, authenticated_user_id=current_user_id
            )

            logger.info(
                f"✅ Chat transfer completed: {transferred_count} chats transferred from "
                f"{guest_user_id} to {current_user_id}"
            )

            return APIResponse.success(
                {
                    "message": "Chats transferred successfully",
                    "transferred_count": transferred_count,
                }
            )

        except ValueError as e:
            return APIResponse.error(str(e), 400)

    except Exception as e:
        logger.exception(f"Error transferring chats: {e}")
        return APIResponse.error("Internal server error", 500)
