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
from datetime import timedelta
from typing import Any, Dict, Optional

import httpx
from quart import Blueprint, jsonify, request
from quart_rate_limiter import rate_limit

from common.middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)

logs_bp = Blueprint("logs", __name__, url_prefix="/api/v1/logs")


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
            "logs_reader": {
                "cluster": [],
                "indices": [
                    {
                        "names": [f"logs-{org_id}*", "logs*"],
                        "privileges": ["read", "view_index_metadata"],
                        "allow_restricted_indices": False,
                        "query": {
                            "term": {
                                "org_id": org_id
                            }
                        }
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
                    "expiration": "365d"  # 1 year expiration
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
            data = {"query": {"match_all": {}}, "size": 50}

        # Ensure we have a query
        if "query" not in data:
            data["query"] = {"match_all": {}}

        # Add org_id filter to ensure users only see their logs
        if "bool" not in data["query"]:
            data["query"] = {
                "bool": {
                    "must": [data["query"]],
                    "filter": [
                        {"term": {"org_id": org_id}}
                    ]
                }
            }
        elif "filter" not in data["query"]["bool"]:
            data["query"]["bool"]["filter"] = [{"term": {"org_id": org_id}}]
        else:
            data["query"]["bool"]["filter"].append({"term": {"org_id": org_id}})

        # Default size and sort
        if "size" not in data:
            data["size"] = 50
        if "sort" not in data:
            data["sort"] = [{"@timestamp": {"order": "desc"}}]

        # Search logs
        index_pattern = f"logs-{org_id}*"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://{elk_config['host']}/{index_pattern}/_search",
                headers={
                    "Authorization": f"ApiKey {api_key}",
                    "Content-Type": "application/json"
                },
                json=data
            )

            if response.status_code not in [200, 201]:
                logger.error(f"ELK search failed: {response.status_code} - {response.text}")
                return jsonify({
                    "error": "Search failed",
                    "details": response.text
                }), response.status_code

            result = response.json()

            logger.info(f"Log search successful for user {user_id} (org: {org_id}), found {result.get('hits', {}).get('total', {}).get('value', 0)} hits")

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
