"""
Metrics Routes for AI Assistant Application

Handles Grafana metrics access:
- Generate Grafana service account tokens for user metric access
- Proxy Prometheus queries with namespace filtering
- User-specific metrics isolation based on org_id/namespace

Uses Grafana HTTP API for token management.
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

metrics_bp = Blueprint("metrics", __name__, url_prefix="/api/v1/metrics")


async def _rate_limit_key() -> str:
    """Rate limit key function (IP-based)."""
    return request.remote_addr or "unknown"


def _build_namespace(org_id: str, env_name: str, app_name: str = "cyoda") -> str:
    """
    Build namespace based on org_id, env_name, and app_name.

    Args:
        org_id: Organization ID
        env_name: Environment name (e.g., "dev", "prod")
        app_name: Application name (default: "cyoda")

    Returns:
        Namespace string in format:
        - "client-{org_id}-{env_name}" if app_name is "cyoda"
        - "client-1-{org_id}-{env_name}-{app_name}" otherwise
    """
    if app_name == "cyoda":
        return f"client-{org_id}-{env_name}"
    else:
        return f"client-1-{org_id}-{env_name}-{app_name}"


def _build_query(query_type: str, namespace: str, **params) -> str:
    """
    Build a Prometheus query based on query type and parameters.

    Args:
        query_type: Type of query (e.g., "pod_status", "cpu_usage", etc.)
        namespace: Kubernetes namespace
        **params: Additional parameters for the query

    Returns:
        Prometheus query string
    """
    queries = {
        "pod_status_up": f'count(up{{namespace="{namespace}"}} == 1)',
        "pod_status_down": f'count(up{{namespace="{namespace}"}} == 0)',
        "pod_count_up": f'count(up{{namespace="{namespace}"}} == 1)',
        "pod_count_down": f'count(up{{namespace="{namespace}"}} == 0)',
        "cpu_usage_rate": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))',
        "cpu_usage_by_pod": f'sum by (pod) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))',
        "cpu_usage_by_deployment": f'sum by (deployment) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))',
        "cpu_usage_by_node": f'sum by (node) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}", image!=""}}[5m]))',
        "memory_usage": f'sum(container_memory_usage_bytes{{namespace="{namespace}", image!=""}})',
        "memory_usage_by_deployment": f'sum by (deployment) (container_memory_usage_bytes{{namespace="{namespace}", image!=""}})',
        "memory_working_set": f'sum(container_memory_working_set_bytes{{namespace="{namespace}", image!=""}})',
        "http_requests_rate": f'sum(rate(http_requests_total{{namespace="{namespace}"}}[5m]))',
        "http_errors_rate": f'sum(rate(http_requests_total{{namespace="{namespace}", status=~"5.."}}[5m]))',
        "http_request_latency_p95": f'histogram_quantile(0.95, sum by (le, handler) (rate(http_request_duration_seconds_bucket{{namespace="{namespace}"}}[5m])))',
        "pod_restarts": f'sum(kube_pod_container_status_restarts_total{{namespace="{namespace}"}})',
        "pod_not_ready": f'count(kube_pod_container_status_ready{{namespace="{namespace}"}} == 0)',
        "pod_count": f'count(kube_pod_info{{namespace="{namespace}"}})',
        "events_rate": f'sum(rate(kube_event_total{{namespace="{namespace}"}}[5m]))',
    }

    if query_type not in queries:
        raise ValueError(f"Unknown query type: {query_type}. Available types: {', '.join(queries.keys())}")

    return queries[query_type]


def _get_grafana_config() -> Dict[str, str]:
    """Get Grafana configuration from environment variables."""
    grafana_host = os.getenv("GRAFANA_HOST")
    grafana_admin_user = os.getenv("GRAFANA_ADMIN_USER")
    grafana_admin_password = os.getenv("GRAFANA_ADMIN_PASSWORD")

    if not all([grafana_host, grafana_admin_user, grafana_admin_password]):
        raise ValueError(
            "Grafana configuration incomplete. Please set GRAFANA_HOST, "
            "GRAFANA_ADMIN_USER, and GRAFANA_ADMIN_PASSWORD"
        )

    return {
        "host": grafana_host,
        "admin_user": grafana_admin_user,
        "admin_password": grafana_admin_password
    }


def _get_prometheus_config() -> Dict[str, str]:
    """Get Prometheus configuration from environment variables."""
    prometheus_host = os.getenv("PROMETHEUS_HOST")
    prometheus_user = os.getenv("PROMETHEUS_USER")
    prometheus_password = os.getenv("PROMETHEUS_PASSWORD")

    if not prometheus_host:
        raise ValueError("PROMETHEUS_HOST environment variable not set")

    return {
        "host": prometheus_host,
        "user": prometheus_user or "",
        "password": prometheus_password or ""
    }


@metrics_bp.route("/grafana-token", methods=["POST"])
@require_auth
@rate_limit(5, timedelta(minutes=5), key_function=_rate_limit_key)
async def generate_grafana_token() -> tuple[dict, int]:
    """
    Generate a Grafana service account token for the authenticated user.

    The token provides access to Grafana dashboards with data source permissions
    scoped to the user's Kubernetes namespace (based on org_id).

    Request headers:
        Authorization: Bearer <jwt_token>

    Returns:
        200: {
            "token": "glsa_...",
            "name": "metrics-{org_id}",
            "service_account_id": 123,
            "grafana_url": "https://grafana.example.com",
            "message": "Token generated. Save it securely - you won't be able to see it again."
        }
        401: Unauthorized
        500: Error response
    """
    try:
        # Get user info from auth middleware
        user_id = request.user_id
        org_id = getattr(request, 'org_id', user_id.lower())

        grafana_config = _get_grafana_config()

        # Service account and token name based on org_id
        sa_name = f"metrics-{org_id}"
        token_name = f"{sa_name}-token"

        # Create basic auth header for Grafana admin API
        auth_string = f"{grafana_config['admin_user']}:{grafana_config['admin_password']}"
        auth_bytes = auth_string.encode('ascii')
        auth_header = base64.b64encode(auth_bytes).decode('ascii')

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            base_url = f"https://{grafana_config['host']}"

            # Step 1: Check if service account exists, create if not
            logger.info(f"Checking for existing service account: {sa_name}")

            # List all service accounts
            sa_list_response = await client.get(
                f"{base_url}/api/serviceaccounts/search",
                headers=headers
            )

            if sa_list_response.status_code != 200:
                logger.error(f"Failed to list service accounts: {sa_list_response.status_code}")
                return jsonify({
                    "error": "Failed to access Grafana API",
                    "details": sa_list_response.text
                }), 500

            service_accounts = sa_list_response.json()
            existing_sa = next(
                (sa for sa in service_accounts.get('serviceAccounts', [])
                 if sa['name'] == sa_name),
                None
            )

            if existing_sa:
                sa_id = existing_sa['id']
                logger.info(f"Found existing service account: {sa_id}")
            else:
                # Create new service account
                logger.info(f"Creating new service account: {sa_name}")
                sa_create_response = await client.post(
                    f"{base_url}/api/serviceaccounts",
                    headers=headers,
                    json={
                        "name": sa_name,
                        "role": "Viewer",  # Read-only access
                        "isDisabled": False
                    }
                )

                if sa_create_response.status_code not in [200, 201]:
                    logger.error(f"Failed to create service account: {sa_create_response.status_code}")
                    return jsonify({
                        "error": "Failed to create service account",
                        "details": sa_create_response.text
                    }), 500

                sa_data = sa_create_response.json()
                sa_id = sa_data['id']
                logger.info(f"Created service account with ID: {sa_id}")

            # Step 2: Create service account token
            logger.info(f"Creating token for service account {sa_id}")
            token_response = await client.post(
                f"{base_url}/api/serviceaccounts/{sa_id}/tokens",
                headers=headers,
                json={
                    "name": token_name,
                    "secondsToLive": 31536000  # 1 year (365 days)
                }
            )

            if token_response.status_code not in [200, 201]:
                logger.error(f"Failed to create token: {token_response.status_code}")
                return jsonify({
                    "error": "Failed to create Grafana token",
                    "details": token_response.text
                }), 500

            token_data = token_response.json()
            token = token_data['key']

            logger.info(f"Generated Grafana token for user {user_id} (org: {org_id})")

            return jsonify({
                "token": token,
                "name": sa_name,
                "service_account_id": sa_id,
                "grafana_url": f"https://{grafana_config['host']}",
                "namespace": f"client-{org_id}",
                "message": "Token generated. Save it securely - you won't be able to see it again.",
                "expires_in_days": 365
            }), 200

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception(f"Error generating Grafana token: {e}")
        return jsonify({"error": "Internal server error"}), 500


@metrics_bp.route("/query", methods=["POST"])
@require_auth
@rate_limit(600, timedelta(minutes=1), key_function=_rate_limit_key)
async def query_metrics() -> tuple[dict, int]:
    """
    Query Prometheus metrics using predefined query types.

    Request headers:
        Authorization: Bearer <jwt_token>

    Request body (Option 1 - Using query_type):
        {
            "query_type": "cpu_usage_rate",  # Required - predefined query type
            "env_name": "dev",  # Required - environment name
            "app_name": "cyoda"  # Optional - application name (default: "cyoda")
        }

    Request body (Option 2 - Legacy with custom query):
        {
            "query": "up{namespace=\"{namespace}\"}",  # Custom query with {namespace} placeholder
            "type": "environment",  # Optional: "environment" or "application"
            "id": "develop"  # Optional: environment id or application id
        }

    Available query_type values:
        - pod_status_up: up{namespace="..."}
        - pod_status_down: up{namespace="..."} == 0
        - pod_count_up: count(up{namespace="..."} == 1)
        - pod_count_down: count(up{namespace="..."} == 0)
        - cpu_usage_rate: rate(container_cpu_usage_seconds_total{...}[5m])
        - cpu_usage_by_pod: sum by (pod) (rate(...))
        - cpu_usage_by_deployment: sum by (deployment) (rate(...))
        - cpu_usage_by_node: sum by (node) (rate(...))
        - memory_usage: container_memory_usage_bytes{...}
        - memory_usage_by_deployment: sum by (deployment) (...)
        - memory_working_set: container_memory_working_set_bytes{...}
        - http_requests_rate: rate(http_requests_total{...}[5m])
        - http_errors_rate: rate(http_requests_total{..., status=~"5.."}[5m])
        - http_request_latency_p95: histogram_quantile(0.95, ...)
        - pod_restarts: kube_pod_container_status_restarts_total{...}
        - pod_not_ready: kube_pod_status_ready{..., condition="true"} == 0
        - pod_count: count(kube_pod_info{...})
        - events_rate: rate(kube_event_total{...}[5m])

    Returns:
        200: Prometheus query results
        400: Invalid request
        401: Unauthorized
        500: Error response
    """
    try:
        # Get user info
        user_id = request.user_id
        org_id = getattr(request, 'org_id', user_id.lower())
        prometheus_config = _get_prometheus_config()

        # Get query parameters from request body
        data = await request.get_json() if await request.get_data() else {}

        if not data:
            return jsonify({"error": "Request body required"}), 400

        # Determine which mode to use
        if 'query_type' in data:
            # New mode: predefined query types
            query_type = data['query_type']
            env_name = data.get('env_name')
            app_name = data.get('app_name', 'cyoda')

            if not env_name:
                return jsonify({"error": "env_name parameter required when using query_type"}), 400

            # Build namespace and query
            namespace = _build_namespace(org_id, env_name, app_name)
            try:
                query = _build_query(query_type, namespace)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

            logger.info(f"Querying Prometheus (new mode) for user {user_id} (org_id: {org_id}, env_name: {env_name}, app_name: {app_name}, query_type: {query_type}, namespace: {namespace})")

        elif 'query' in data:
            # Legacy mode: custom query with {namespace} placeholder
            query = data['query']
            deployment_type = data.get('type', 'environment')

            # Default id based on type
            if deployment_type == 'application':
                deployment_id = data.get('id', 'start')
            else:  # environment
                deployment_id = data.get('id', 'develop')

            # Construct namespace based on type and id
            if deployment_type == 'environment':
                namespace = f"client-{org_id}"
            else:  # application
                namespace = f"client-{org_id}-{deployment_id}"

            # Replace {namespace} placeholder in query
            query = query.replace("{namespace}", namespace)

            logger.info(f"Querying Prometheus (legacy mode) for user {user_id} (org_id: {org_id}, type: {deployment_type}, id: {deployment_id}, namespace: {namespace})")

        else:
            return jsonify({"error": "Either 'query_type' or 'query' parameter required"}), 400

        logger.info(f"Query: {query}")

        # Prepare query parameters
        params = {"query": query}
        if data and 'time' in data:
            params['time'] = data['time']
        if data and 'timeout' in data:
            params['timeout'] = data['timeout']

        # Query Prometheus (no auth required)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        prom_url = f"https://{prometheus_config['host']}/api/v1/query"
        logger.info(f"Sending to Prometheus: {prom_url}")

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(
                prom_url,
                headers=headers,
                data=params
            )

            logger.info(f"Prometheus response status: {response.status_code}")

            if response.status_code not in [200, 201]:
                logger.error(f"Prometheus query failed: {response.status_code} - {response.text}")
                return jsonify({
                    "error": "Query failed",
                    "details": response.text
                }), response.status_code

            result = response.json()
            result_count = len(result.get('data', {}).get('result', []))
            logger.info(f"Prometheus query successful for user {user_id}, returned {result_count} results")

            # Log warning if no results found
            if result_count == 0:
                logger.warning(f"Query returned no results. Query: {query}")

            return jsonify(result), 200

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception(f"Error querying Prometheus: {e}")
        return jsonify({"error": "Internal server error"}), 500


@metrics_bp.route("/query_range", methods=["POST"])
@require_auth
@rate_limit(600, timedelta(minutes=1), key_function=_rate_limit_key)
async def query_range_metrics() -> tuple[dict, int]:
    """
    Query Prometheus metrics over a time range with namespace filtering.

    Request headers:
        Authorization: Bearer <jwt_token>

    Request body (Option 1 - Using query_type):
        {
            "query_type": "cpu_usage_rate",
            "env_name": "dev",
            "app_name": "cyoda",
            "start": "2025-12-02T00:00:00Z",
            "end": "2025-12-02T12:00:00Z",
            "step": "15s"
        }

    Request body (Option 2 - Legacy with custom query):
        {
            "query": "up",
            "start": "2025-12-02T00:00:00Z",
            "end": "2025-12-02T12:00:00Z",
            "step": "15s"
        }

    Returns:
        200: Prometheus range query results
        400: Invalid request
        401: Unauthorized
        500: Error response
    """
    try:
        # Get user info
        user_id = request.user_id
        org_id = getattr(request, 'org_id', user_id.lower())

        prometheus_config = _get_prometheus_config()

        # Get query parameters
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        if 'start' not in data or 'end' not in data:
            return jsonify({"error": "start and end parameters required"}), 400

        # Determine which mode to use
        if 'query_type' in data:
            # New mode: predefined query types
            query_type = data['query_type']
            env_name = data.get('env_name')
            app_name = data.get('app_name', 'cyoda')

            if not env_name:
                return jsonify({"error": "env_name parameter required when using query_type"}), 400

            # Build namespace and query
            namespace = _build_namespace(org_id, env_name, app_name)
            try:
                query = _build_query(query_type, namespace)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

            logger.info(f"Range querying Prometheus (new mode) for user {user_id} (org_id: {org_id}, env_name: {env_name}, app_name: {app_name}, query_type: {query_type})")

        elif 'query' in data:
            # Legacy mode: custom query with namespace filter
            query = data['query']
            namespace = f"client-{org_id}"

            # Add namespace filter
            if 'namespace=' not in query and 'namespace!=' not in query:
                if query.strip().startswith('{'):
                    query = query.replace('{', f'{{namespace="{namespace}",', 1)
                else:
                    query = f'{query}{{namespace="{namespace}"}}'

            logger.info(f"Range querying Prometheus (legacy mode) for user {user_id} (org_id: {org_id})")

        else:
            return jsonify({"error": "Either 'query_type' or 'query' parameter required"}), 400

        logger.info(f"Range Query: {query}")

        # Prepare query parameters
        params = {
            "query": query,
            "start": data['start'],
            "end": data['end'],
            "step": data.get('step', '15s')
        }

        # Create auth header
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if prometheus_config['user'] and prometheus_config['password']:
            auth_string = f"{prometheus_config['user']}:{prometheus_config['password']}"
            auth_bytes = auth_string.encode('ascii')
            auth_header = base64.b64encode(auth_bytes).decode('ascii')
            headers["Authorization"] = f"Basic {auth_header}"

        # Query Prometheus
        async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
            response = await client.post(
                f"https://{prometheus_config['host']}/api/v1/query_range",
                headers=headers,
                data=params
            )

            if response.status_code not in [200, 201]:
                logger.error(f"Prometheus range query failed: {response.status_code}")
                return jsonify({
                    "error": "Query failed",
                    "details": response.text
                }), response.status_code

            result = response.json()
            logger.info(f"Prometheus range query successful for user {user_id}")

            return jsonify(result), 200

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception(f"Error querying Prometheus: {e}")
        return jsonify({"error": "Internal server error"}), 500


@metrics_bp.route("/health", methods=["GET"])
@require_auth
async def metrics_health() -> tuple[dict, int]:
    """
    Check if Grafana and Prometheus are accessible.

    Returns:
        200: {"status": "healthy", "services": {...}}
        500: {"status": "unhealthy", "error": "..."}
    """
    try:
        services_status = {}

        # Check Grafana
        try:
            grafana_config = _get_grafana_config()
            auth_string = f"{grafana_config['admin_user']}:{grafana_config['admin_password']}"
            auth_bytes = auth_string.encode('ascii')
            auth_header = base64.b64encode(auth_bytes).decode('ascii')

            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.get(
                    f"https://{grafana_config['host']}/api/health",
                    headers={"Authorization": f"Basic {auth_header}"}
                )
                services_status['grafana'] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "host": grafana_config['host']
                }
        except Exception as e:
            services_status['grafana'] = {"status": "unhealthy", "error": str(e)}

        # Check Prometheus
        try:
            prometheus_config = _get_prometheus_config()
            headers = {}
            if prometheus_config['user'] and prometheus_config['password']:
                auth_string = f"{prometheus_config['user']}:{prometheus_config['password']}"
                auth_bytes = auth_string.encode('ascii')
                auth_header = base64.b64encode(auth_bytes).decode('ascii')
                headers["Authorization"] = f"Basic {auth_header}"

            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.get(
                    f"https://{prometheus_config['host']}/-/healthy",
                    headers=headers
                )
                services_status['prometheus'] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "host": prometheus_config['host']
                }
        except Exception as e:
            services_status['prometheus'] = {"status": "unhealthy", "error": str(e)}

        overall_healthy = all(
            svc.get('status') == 'healthy'
            for svc in services_status.values()
        )

        return jsonify({
            "status": "healthy" if overall_healthy else "degraded",
            "services": services_status
        }), 200 if overall_healthy else 500

    except Exception as e:
        logger.exception(f"Error checking metrics health: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
