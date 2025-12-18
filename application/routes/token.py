"""
Token Routes for AI Assistant Application

Handles JWT token generation for:
- Guest users (unauthenticated, temporary sessions)
- Authenticated users (for testing purposes)

Uses real JWT signing with HS256 algorithm.
"""

import logging
from datetime import timedelta

from quart import Blueprint, request
from quart_rate_limiter import rate_limit

from application.routes.common.rate_limiting import default_rate_limit_key
from application.routes.common.response import APIResponse
from application.routes.common.validation import validate_json
from application.routes.models.token_models import GenerateTestTokenRequest
from common.utils.jwt_utils import generate_guest_token, generate_user_token

logger = logging.getLogger(__name__)

token_bp = Blueprint("token", __name__, url_prefix="/api/v1")


@token_bp.route("/get_guest_token", methods=["GET"])
@rate_limit(10, timedelta(minutes=1), key_function=default_rate_limit_key)
async def get_guest_token():
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
        return APIResponse.success(token_response)

    except Exception as e:
        logger.exception(f"Error generating guest token: {e}")
        return APIResponse.internal_error(str(e))


@token_bp.route("/generate_test_token", methods=["POST"])
@rate_limit(10, timedelta(minutes=1), key_function=default_rate_limit_key)
@validate_json(GenerateTestTokenRequest)
async def generate_test_token():
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
        400: Invalid request (automatic validation)
        500: Error response
    """
    try:
        # Get validated data from decorator
        data: GenerateTestTokenRequest = request.validated_data

        token = generate_user_token(
            user_id=data.user_id,
            is_superuser=data.is_superuser,
            expiry_hours=data.expiry_hours
        )

        return APIResponse.success({
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": data.expiry_hours * 3600,
            "user_id": data.user_id,
            "is_superuser": data.is_superuser
        })

    except Exception as e:
        logger.exception(f"Error generating test token: {e}")
        return APIResponse.internal_error(str(e))

