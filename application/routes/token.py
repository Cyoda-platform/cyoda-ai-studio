"""
Token Routes for AI Assistant Application

Handles JWT token generation for:
- Guest users (unauthenticated, temporary sessions)
- Authenticated users (for testing purposes)

Uses real JWT signing with HS256 algorithm.
"""

import logging
from datetime import timedelta

from quart import Blueprint, jsonify, request
from quart_rate_limiter import rate_limit

from common.utils.jwt_utils import generate_guest_token, generate_user_token

logger = logging.getLogger(__name__)

token_bp = Blueprint("token", __name__, url_prefix="/api/v1")


async def _rate_limit_key() -> str:
    """Rate limit key function (IP-based)."""
    return request.remote_addr or "unknown"


@token_bp.route("/get_guest_token", methods=["GET"])
@rate_limit(10, timedelta(minutes=1), key_function=_rate_limit_key)
async def get_guest_token() -> tuple[dict, int]:
    """
    Generate a JWT token for guest users.

    Guest tokens:
    - Valid for 50 weeks
    - Include 'guest.' prefix in user_id
    - Do not have superuser privileges
    - Are signature-verified on each request

    Returns:
        200: Token response with access_token, token_type, expires_in, guest_id
        500: Error response
    """
    try:
        token_response = generate_guest_token()
        return jsonify(token_response), 200

    except Exception as e:
        logger.exception(f"Error generating guest token: {e}")
        return jsonify({"error": str(e)}), 500


@token_bp.route("/generate_test_token", methods=["POST"])
@rate_limit(10, timedelta(minutes=1), key_function=_rate_limit_key)
async def generate_test_token() -> tuple[dict, int]:
    """
    Generate a JWT token for testing purposes.

    This endpoint is for development/testing only.
    In production, tokens would come from an external auth provider.

    Request body:
        {
            "user_id": "alice",
            "is_superuser": false,
            "expiry_hours": 24
        }

    Returns:
        200: Token response with access_token
        400: Invalid request
        500: Error response
    """
    try:
        data = await request.get_json()

        if not data or "user_id" not in data:
            return jsonify({"error": "user_id is required"}), 400

        user_id = data["user_id"]
        is_superuser = data.get("is_superuser", False)
        expiry_hours = data.get("expiry_hours", 24)

        token = generate_user_token(
            user_id=user_id,
            is_superuser=is_superuser,
            expiry_hours=expiry_hours
        )

        return jsonify({
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": expiry_hours * 3600,
            "user_id": user_id,
            "is_superuser": is_superuser
        }), 200

    except Exception as e:
        logger.exception(f"Error generating test token: {e}")
        return jsonify({"error": str(e)}), 500

