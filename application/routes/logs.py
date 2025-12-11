"""
Logs Routes for AI Assistant Application

Handles ELK (Elasticsearch) log access:
- Generate API keys for user log access
- Search logs with query parameters
- User-specific log filtering based on org_id

Uses Elasticsearch API for log management.
"""

import base64
import logging
import os
import re
from datetime import timedelta
from typing import Any, Dict, Optional

import httpx
from quart import Blueprint, jsonify, request
from quart_rate_limiter import rate_limit

from common.middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)

logs_bp = Blueprint("logs", __name__, url_prefix="/api/v1/logs")


def _get_namespace(name: str) -> str:
    """
    Transform a name into a valid Kubernetes namespace format.
    Converts to lowercase and replaces non-alphanumeric characters with hyphens.
    """
    return re.sub(r"[^a-z0-9-]", "-", name.lower())


async def _rate_limit_key() -> str:
    """Rate limit key function (IP-based)."""
    return request.remote_addr or "unknown"


def _get_elk_config() -> Dict[str, str]:
    """Get ELK configuration from environment variables."""
    elk_host = os.getenv("ELK_HOST")
    elk_user = os.getenv("ELK_USER")
    elk_password = os.getenv("ELK_PASSWORD")

    if not all([elk_host, elk_user, elk_password]):
        raise ValueError("ELK configuration incomplete. Please set ELK_HOST, ELK_USER, and ELK_PASSWORD")

    return {
        "host": elk_host,
        "user": elk_user,
        "password": elk_password
    }


@logs_bp.route("/api-key", methods=["POST"])
@require_auth
@rate_limit(5, timedelta(minutes=5), key_function=_rate_limit_key)
async def generate_api_key() -> tuple[dict, int]:
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
        user_id = request.user_id
        org_id = getattr(request, 'org_id', user_id.lower())

        elk_config = _get_elk_config()

        # Create API key name based on org_id
        api_key_name = f"logs-reader-{org_id}"

        # Define role descriptors for read-only access to org-specific logs
        role_descriptors = {
            f"logs_reader_{org_id}": {
                "cluster": [],
                "indices": [
                    {
                        "names": [f"logs-client-{org_id}*", f"logs-client-1-{org_id}*"],
                        "privileges": ["read", "view_index_metadata"],
                        "allow_restricted_indices": False
                    }
                ],
                "run_as": []
            }
        }

        # Create basic auth header for ELK
        auth_string = f"{elk_config['user']}:{elk_config['password']}"
        auth_bytes = auth_string.encode('ascii')
        auth_header = base64.b64encode(auth_bytes).decode('ascii')

        # Make request to Elasticsearch API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://{elk_config['host']}/_security/api_key",
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json"
                },
                json={
                    "name": api_key_name,
                    "role_descriptors": role_descriptors,
                    "expiration": "1h"
                }
            )

            if response.status_code not in [200, 201]:
                logger.error(f"ELK API key generation failed: {response.status_code} - {response.text}")
                return jsonify({
                    "error": "Failed to generate API key",
                    "details": response.text
                }), 500

            result = response.json()

            # Encode the API key in the format Elasticsearch expects
            api_key_credentials = f"{result['id']}:{result['api_key']}"
            encoded_api_key = base64.b64encode(api_key_credentials.encode('ascii')).decode('ascii')

            logger.info(f"Generated ELK API key for user {user_id} (org: {org_id})")

            return jsonify({
                "api_key": encoded_api_key,
                "name": api_key_name,
                "created": True,
                "message": "API key generated. Save it securely - you won't be able to see it again.",
                "expires_in_days": 365
            }), 200

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception(f"Error generating ELK API key: {e}")
        return jsonify({"error": "Internal server error"}), 500


@logs_bp.route("/search", methods=["POST"])
@require_auth
@rate_limit(30, timedelta(minutes=1), key_function=_rate_limit_key)
async def search_logs() -> tuple[dict, int]:
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
            return jsonify({"error": "X-API-Key header required"}), 400

        # Get user info
        user_id = request.user_id
        org_id = getattr(request, 'org_id', user_id.lower())

        elk_config = _get_elk_config()

        # Get search query from request body
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Request body required with env_name and app_name"}), 400

        # Get env_name and app_name from request
        env_name = data.get('env_name')
        app_name = data.get('app_name')

        if not env_name or not app_name:
            return jsonify({"error": "env_name and app_name are required"}), 400

        # Construct index pattern for application logs
        # Transform names to valid namespace format (lowercase, hyphens only)
        org_namespace = _get_namespace(org_id)
        env_namespace = _get_namespace(env_name)

        if app_name == "cyoda":
            index_pattern = f"logs-client-{org_namespace}-{env_namespace}*"
        else:
            app_namespace = _get_namespace(app_name)
            index_pattern = f"logs-client-1-{org_namespace}-{env_namespace}-{app_namespace}*"

        logger.info(
            f"Searching logs for user {user_id} (org_id: {org_id}, env: {env_name}, app: {app_name}, index: {index_pattern})")

        # Validate and cap size parameter (max 10000 for Elasticsearch)
        requested_size = data.get("size", 50)
        max_size = 10000
        size = min(int(requested_size), max_size) if isinstance(requested_size, (int, str)) else 50

        query = {
            "query": data.get("query", {"match_all": {}}),
            "size": size,
            "sort": data.get("sort", [{"@timestamp": {"order": "desc"}}])
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://{elk_config['host']}/{index_pattern}/_search",
                headers={
                    "Authorization": f"ApiKey {api_key}",
                    "Content-Type": "application/json"
                },
                json=query
            )

            if response.status_code not in [200, 201]:
                logger.error(f"ELK search failed: {response.status_code} - {response.text}")
                try:
                    error_details = response.json()
                    logger.error(f"ELK error details: {error_details}")
                except:
                    error_details = response.text

                # If ELK returns 401, it means the API key is invalid/expired
                # Return 500 so frontend knows to regenerate the API key
                if response.status_code == 401:
                    logger.warning(f"ELK API key invalid/expired for user {user_id} (org: {org_id})")
                    return jsonify({
                        "error": "API key invalid or expired",
                        "details": error_details,
                    }), 500

                return jsonify({
                    "error": "Search failed",
                    "details": error_details,
                    "query": query,
                    "index_pattern": index_pattern
                }), response.status_code

            result = response.json()

            logger.info(
                f"Log search successful for user {user_id} (org: {org_id}, env: {env_name}, app: {app_name}), found {result.get('hits', {}).get('total', {}).get('value', 0)} hits")

            return jsonify(result), 200

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception(f"Error searching logs: {e}")
        return jsonify({"error": "Internal server error"}), 500


@logs_bp.route("/health", methods=["GET"])
@require_auth
async def logs_health() -> tuple[dict, int]:
    """
    Check if ELK cluster is accessible.

    Returns:
        200: {"status": "healthy", "elk_host": "..."}
        500: {"status": "unhealthy", "error": "..."}
    """
    try:
        elk_config = _get_elk_config()

        # Create basic auth header
        auth_string = f"{elk_config['user']}:{elk_config['password']}"
        auth_bytes = auth_string.encode('ascii')
        auth_header = base64.b64encode(auth_bytes).decode('ascii')

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://{elk_config['host']}/_cluster/health",
                headers={
                    "Authorization": f"Basic {auth_header}"
                }
            )

            if response.status_code == 200:
                cluster_health = response.json()
                return jsonify({
                    "status": "healthy",
                    "elk_host": elk_config['host'],
                    "cluster_status": cluster_health.get('status', 'unknown')
                }), 200
            else:
                return jsonify({
                    "status": "unhealthy",
                    "error": f"ELK returned status {response.status_code}"
                }), 500

    except ValueError as e:
        return jsonify({"status": "unconfigured", "error": str(e)}), 500
    except Exception as e:
        logger.exception(f"Error checking ELK health: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
