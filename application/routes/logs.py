"""
Logs Routes for AI Assistant Application

Handles ELK (Elasticsearch) log access:
- Generate API keys for user log access
- Search logs with query parameters
- User-specific log filtering based on org_id

Uses Elasticsearch API for log management.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from quart import Blueprint, request
from quart_rate_limiter import rate_limit
from pydantic import BaseModel, Field

from application.routes.common.rate_limiting import user_rate_limit_key
from application.routes.common.response import APIResponse
from application.services.core.config_service import get_config_service
from application.services.core.logs_service import LogsService
from common.middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)

# Search logs constants
MISSING_API_KEY_HEADER = "X-API-Key header required"
MISSING_REQUEST_BODY = "Request body required with env_name and app_name"
MISSING_ENV_APP_NAME = "env_name and app_name are required"
MISSING_API_KEY_HEADER_CODE = 400
MISSING_BODY_CODE = 400
MISSING_ENV_CODE = 400
EXPIRED_API_KEY_ERROR = "ELK_API_KEY_EXPIRED"
EXPIRED_API_KEY_MESSAGE = (
    "ELK API key has expired. Please regenerate the API key using /api/v1/logs/elk-token endpoint."
)
EXPIRED_API_KEY_CODE = 500
SEARCH_FAILED_MESSAGE = "Search failed"
SEARCH_FAILED_CODE = 500
CONFIG_ERROR_MESSAGE = "Configuration error"
DEFAULT_SEARCH_SIZE = 50
DEFAULT_QUERY = {"match_all": {}}
DEFAULT_SORT = [{"@timestamp": {"order": "desc"}}]


class LogSearchRequest(BaseModel):
    """Log search request model."""

    env_name: str
    app_name: str
    query: Dict[str, Any] = DEFAULT_QUERY
    size: int = DEFAULT_SEARCH_SIZE
    sort: list = DEFAULT_SORT
    from_: int = Field(0, alias="from")

    class Config:
        """Pydantic config."""
        extra = "allow"
        populate_by_name = True

logs_bp = Blueprint("logs", __name__, url_prefix="/api/v1/logs")

# Initialize services
config_service = get_config_service()
logs_service = LogsService(config_service)


@logs_bp.route("/api-key", methods=["POST"])
@require_auth
@rate_limit(5, timedelta(minutes=5), key_function=user_rate_limit_key)
async def generate_api_key():
    """
    Generate an Elasticsearch API key for the authenticated user.

    The API key is scoped to read only logs for the user's organization.
    Users can only have one active API key at a time - generating a new one
    invalidates the previous one.

    Request headers:
        Authorization: Bearer <jwt_token>

    Returns:
        200: {
            "api_key": "base64_encoded_api_key",
            "name": "logs-reader-{org_id}",
            "created": true,
            "message": "API key generated. Save it securely - you won't be able to see it again."
        }
        401: Unauthorized
        500: Error response
    """
    try:
        # Get user info from auth middleware
        org_id = getattr(request, 'org_id', request.user_id.lower())

        # Use service to generate API key
        result = await logs_service.generate_api_key(org_id)

        return APIResponse.success(result)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return APIResponse.internal_error(str(e))
    except Exception as e:
        logger.exception(f"Error generating ELK API key: {e}")
        return APIResponse.internal_error("Failed to generate API key")


def _validate_api_key_header() -> Optional[tuple]:
    """Validate X-API-Key header is present.

    Returns:
        None if valid, tuple of (response, status_code) if invalid
    """
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return APIResponse.error(MISSING_API_KEY_HEADER, MISSING_API_KEY_HEADER_CODE)

    return api_key


async def _extract_search_params() -> Optional[tuple]:
    """Extract and validate search parameters from request.

    Returns:
        Tuple of (env_name, app_name, size, query, sort) if valid,
        or (error_response, status_code) if invalid
    """
    # Step 1: Get request body
    data = await request.get_json()
    if not data:
        return APIResponse.error(MISSING_REQUEST_BODY, MISSING_BODY_CODE)

    # Step 2: Extract required fields
    env_name = data.get('env_name')
    app_name = data.get('app_name')

    if not env_name or not app_name:
        return APIResponse.error(MISSING_ENV_APP_NAME, MISSING_ENV_CODE)

    # Step 3: Extract optional fields with defaults
    size = data.get("size", DEFAULT_SEARCH_SIZE)
    query = data.get("query", DEFAULT_QUERY)
    sort = data.get("sort", DEFAULT_SORT)

    return env_name, app_name, size, query, sort


def _handle_expired_api_key_error() -> tuple:
    """Handle expired API key error with details.

    Returns:
        Tuple of (response, status_code)
    """
    logger.warning("ELK API key has expired")
    return APIResponse.error(
        EXPIRED_API_KEY_MESSAGE,
        EXPIRED_API_KEY_CODE,
        details={
            "error_code": EXPIRED_API_KEY_ERROR,
            "regenerate_endpoint": "/api/v1/logs/elk-token",
            "regenerate_method": "POST"
        }
    )


@logs_bp.route("/search", methods=["POST"])
@require_auth
@rate_limit(30, timedelta(minutes=1), key_function=user_rate_limit_key)
async def search_logs():
    """Search logs using Elasticsearch query DSL.

    This endpoint acts as a proxy to Elasticsearch, allowing users to search
    their organization's logs using their API key.

    Request headers:
        Authorization: Bearer <jwt_token>
        X-API-Key: <elk_api_key>

    Request body:
        {
            "env_name": "production",
            "app_name": "cyoda",
            "query": {"match_all": {}},
            "size": 50,
            "from": 0,
            "sort": [{"@timestamp": {"order": "desc"}}]
        }

    Returns:
        200: Elasticsearch search results
        400: Invalid request
        401: Unauthorized
        500: Error response
    """
    try:
        # Step 1: Validate API key header
        api_key_result = _validate_api_key_header()
        if isinstance(api_key_result, tuple):
            return api_key_result
        api_key = api_key_result

        # Step 2: Get user organization ID
        org_id = getattr(request, 'org_id', request.user_id.lower())

        # Step 3: Extract and validate search parameters
        params_result = await _extract_search_params()
        if isinstance(params_result, tuple) and len(params_result) == 2:
            return params_result
        env_name, app_name, size, query, sort = params_result

        # Step 4: Call service to search logs
        result = await logs_service.search_logs(
            api_key=api_key,
            org_id=org_id,
            env_name=env_name,
            app_name=app_name,
            query=query,
            size=size,
            sort=sort
        )

        # Step 5: Return success response
        return APIResponse.success(result)

    except ValueError as e:
        # Step 6: Handle value errors (API key expired, config errors)
        error_msg = str(e)
        if error_msg == EXPIRED_API_KEY_ERROR:
            return _handle_expired_api_key_error()

        logger.error(f"{CONFIG_ERROR_MESSAGE}: {e}")
        return APIResponse.error(str(e), EXPIRED_API_KEY_CODE)

    except Exception as e:
        # Step 7: Handle unexpected errors
        logger.exception(f"Error searching logs: {e}")
        return APIResponse.error(SEARCH_FAILED_MESSAGE, SEARCH_FAILED_CODE)


@logs_bp.route("/health", methods=["GET"])
@require_auth
async def logs_health():
    """
    Check if ELK cluster is accessible.

    Returns:
        200: {"status": "healthy", "elk_host": "..."}
        500: {"status": "unhealthy", "error": "..."}
    """
    try:
        health = await logs_service.check_health()

        if health["status"] == "healthy":
            return APIResponse.success(health)
        else:
            return APIResponse.internal_error(health.get("error", "ELK unhealthy"))

    except ValueError as e:
        return APIResponse.internal_error(f"Configuration error: {str(e)}")
    except Exception as e:
        logger.exception(f"Error checking ELK health: {e}")
        return APIResponse.internal_error(f"Health check failed: {str(e)}")
