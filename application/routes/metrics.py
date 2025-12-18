"""
Metrics Routes for AI Assistant Application

Handles Grafana metrics access:
- Generate Grafana service account tokens for user metric access
- Proxy Prometheus queries with namespace filtering
- User-specific metrics isolation based on org_id/namespace

REFACTORED: Uses MetricsService, ConfigService, and common infrastructure.
"""

import logging
from datetime import timedelta

from quart import Blueprint, request
from quart_rate_limiter import rate_limit

from common.middleware.auth_middleware import require_auth

# NEW: Use common infrastructure and services
from application.routes.common.rate_limiting import default_rate_limit_key
from application.routes.common.response import APIResponse
from application.services.service_factory import get_service_factory

logger = logging.getLogger(__name__)

metrics_bp = Blueprint("metrics", __name__, url_prefix="/api/v1/metrics")

# Get services from factory
service_factory = get_service_factory()
metrics_service = service_factory.metrics_service
config_service = service_factory.config_service


# NOTE: Helper functions removed - now using MetricsService and ConfigService
# - _build_namespace() -> use NamespaceBuilder (in MetricsService)
# - _build_query() -> use QueryBuilder (in MetricsService)
# - _get_grafana_config() -> use ConfigService.get_grafana_config()
# - _get_prometheus_config() -> use ConfigService.get_prometheus_config()


@metrics_bp.route("/grafana-token", methods=["POST"])
@require_auth
@rate_limit(5, timedelta(minutes=5), key_function=default_rate_limit_key)
async def generate_grafana_token():
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

        logger.info(f"Generating Grafana token for user {user_id} (org: {org_id})")

        # Use MetricsService to generate token
        result = await metrics_service.generate_grafana_token(org_id)

        logger.info(f"Successfully generated Grafana token for user {user_id}")

        return APIResponse.success(result)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return APIResponse.error(str(e), 500)
    except Exception as e:
        logger.exception(f"Error generating Grafana token: {e}")
        return APIResponse.error("Internal server error", 500)


@metrics_bp.route("/query", methods=["POST"])
@require_auth
@rate_limit(600, timedelta(minutes=1), key_function=default_rate_limit_key)
async def query_metrics():
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

        # Get query parameters from request body
        data = await request.get_json() if await request.get_data() else {}

        if not data:
            return APIResponse.error("Request body required", 400)

        # Determine which mode to use and query Prometheus via MetricsService
        if 'query_type' in data:
            # New mode: predefined query types
            query_type = data['query_type']
            env_name = data.get('env_name')
            app_name = data.get('app_name', 'cyoda')

            if not env_name:
                return APIResponse.error("env_name parameter required when using query_type", 400)

            logger.info(f"Querying Prometheus (query_type mode) for user {user_id} (org_id: {org_id}, env_name: {env_name}, app_name: {app_name}, query_type: {query_type})")

            try:
                result = await metrics_service.query_prometheus(
                    org_id=org_id,
                    env_name=env_name,
                    app_name=app_name,
                    query_type=query_type,
                    time=data.get('time'),
                    timeout=data.get('timeout')
                )
            except ValueError as e:
                return APIResponse.error(str(e), 400)

        elif 'query' in data:
            # Legacy mode: custom query with {namespace} placeholder
            query = data['query']
            deployment_type = data.get('type', 'environment')
            deployment_id = data.get('id', 'start' if deployment_type == 'application' else 'develop')

            logger.info(f"Querying Prometheus (legacy mode) for user {user_id} (org_id: {org_id}, type: {deployment_type}, id: {deployment_id})")

            result = await metrics_service.query_prometheus_custom(
                org_id=org_id,
                query=query,
                deployment_type=deployment_type,
                deployment_id=deployment_id,
                time=data.get('time'),
                timeout=data.get('timeout')
            )

        else:
            return APIResponse.error("Either 'query_type' or 'query' parameter required", 400)

        logger.info(f"Prometheus query successful for user {user_id}")

        return APIResponse.success(result)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return APIResponse.error(str(e), 500)
    except Exception as e:
        logger.exception(f"Error querying Prometheus: {e}")
        return APIResponse.error("Internal server error", 500)


@metrics_bp.route("/query_range", methods=["POST"])
@require_auth
@rate_limit(600, timedelta(minutes=1), key_function=default_rate_limit_key)
async def query_range_metrics():
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

        # Get query parameters
        data = await request.get_json()
        if not data:
            return APIResponse.error("Request body required", 400)
        if 'start' not in data or 'end' not in data:
            return APIResponse.error("start and end parameters required", 400)

        # Determine which mode to use and query Prometheus via MetricsService
        if 'query_type' in data:
            # New mode: predefined query types
            query_type = data['query_type']
            env_name = data.get('env_name')
            app_name = data.get('app_name', 'cyoda')

            if not env_name:
                return APIResponse.error("env_name parameter required when using query_type", 400)

            logger.info(f"Range querying Prometheus (query_type mode) for user {user_id} (org_id: {org_id}, env_name: {env_name}, app_name: {app_name}, query_type: {query_type})")

            try:
                result = await metrics_service.query_prometheus_range(
                    org_id=org_id,
                    env_name=env_name,
                    app_name=app_name,
                    query_type=query_type,
                    start=data['start'],
                    end=data['end'],
                    step=data.get('step', '15s')
                )
            except ValueError as e:
                return APIResponse.error(str(e), 400)

        elif 'query' in data:
            # Legacy mode: custom query with namespace filter
            query = data['query']

            logger.info(f"Range querying Prometheus (legacy mode) for user {user_id} (org_id: {org_id})")

            result = await metrics_service.query_prometheus_range_custom(
                org_id=org_id,
                query=query,
                start=data['start'],
                end=data['end'],
                step=data.get('step', '15s')
            )

        else:
            return APIResponse.error("Either 'query_type' or 'query' parameter required", 400)

        logger.info(f"Prometheus range query successful for user {user_id}")

        return APIResponse.success(result)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return APIResponse.error(str(e), 500)
    except Exception as e:
        logger.exception(f"Error querying Prometheus: {e}")
        return APIResponse.error("Internal server error", 500)


@metrics_bp.route("/health", methods=["GET"])
@require_auth
async def metrics_health():
    """
    Check if Grafana and Prometheus are accessible.

    Returns:
        200: {"status": "healthy", "services": {...}}
        500: {"status": "unhealthy", "error": "..."}
    """
    try:
        # Use MetricsService to check health
        health_status = await metrics_service.check_health()

        overall_healthy = health_status["status"] == "healthy"
        status_code = 200 if overall_healthy else 500

        return APIResponse.success(health_status) if overall_healthy else \
               (APIResponse.error(health_status.get("error", "Services degraded"), status_code, details=health_status), status_code)

    except Exception as e:
        logger.exception(f"Error checking metrics health: {e}")
        return APIResponse.error("Health check failed", 500, details={"error": str(e)})
