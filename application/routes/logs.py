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

from quart import Blueprint, request
from quart_rate_limiter import rate_limit

from application.routes.common.rate_limiting import user_rate_limit_key
from application.routes.common.response import APIResponse
from application.services.config_service import get_config_service
from application.services.logs_service import LogsService
from common.middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)

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


@logs_bp.route("/search", methods=["POST"])
@require_auth
@rate_limit(30, timedelta(minutes=1), key_function=user_rate_limit_key)
async def search_logs():
    """
    Search logs using Elasticsearch query DSL.

    This endpoint acts as a proxy to Elasticsearch, allowing users to search
    their organization's logs using their API key.

    Request headers:
        Authorization: Bearer <jwt_token>
        X-API-Key: <elk_api_key>

    Request body:
        {
            "env_name": "production",  # Required: environment name
            "app_name": "cyoda",  # Required: application name
            "query": {
                "match_all": {}
            },
            "size": 50,
            "from": 0,
            "sort": [
                {"@timestamp": {"order": "desc"}}
            ]
        }

    Returns:
        200: Elasticsearch search results
        400: Invalid request
        401: Unauthorized
        500: Error response
    """
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return APIResponse.error("X-API-Key header required", 400)

        # Get user info
        org_id = getattr(request, 'org_id', request.user_id.lower())

        # Get search query from request body
        data = await request.get_json()
        if not data:
            return APIResponse.error("Request body required with env_name and app_name", 400)

        # Get env_name and app_name from request
        env_name = data.get('env_name')
        app_name = data.get('app_name')

        if not env_name or not app_name:
            return APIResponse.error("env_name and app_name are required", 400)

        # Use service to search logs
        size = data.get("size", 50)
        query = data.get("query", {"match_all": {}})
        sort = data.get("sort", [{"@timestamp": {"order": "desc"}}])

        result = await logs_service.search_logs(
            api_key=api_key,
            org_id=org_id,
            env_name=env_name,
            app_name=app_name,
            query=query,
            size=size,
            sort=sort
        )

        return APIResponse.success(result)

    except ValueError as e:
        error_msg = str(e)
        # Check if it's an expired API key error
        if error_msg == "ELK_API_KEY_EXPIRED":
            logger.warning("ELK API key has expired")
            return APIResponse.error(
                "ELK API key has expired. Please regenerate the API key using /api/v1/logs/elk-token endpoint.",
                500,
                details={
                    "error_code": "ELK_API_KEY_EXPIRED",
                    "regenerate_endpoint": "/api/v1/logs/elk-token",
                    "regenerate_method": "POST"
                }
            )
        logger.error(f"Configuration error: {e}")
        return APIResponse.error(str(e), 500)
    except Exception as e:
        logger.exception(f"Error searching logs: {e}")
        return APIResponse.error("Search failed", 500)


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
