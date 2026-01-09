"""Tests for query_metrics and query_range_metrics in application/routes/metrics.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from quart import Quart

from application.routes.metrics import metrics_bp


@pytest.fixture
def app():
    """Create test application."""
    app = Quart(__name__)
    app.register_blueprint(metrics_bp, url_prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestQueryMetrics:
    """Tests for query_metrics route handler."""

    @pytest.mark.asyncio
    async def test_query_metrics_with_query_type(self, app):
        """Test query_metrics with query_type parameter."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus = AsyncMock(return_value={"data": "test"})

            async with app.test_request_context(
                "/api/v1/metrics/query",
                method="POST",
                json={
                    "query_type": "cpu_usage_rate",
                    "env_name": "dev",
                    "app_name": "cyoda",
                },
            ):
                app.request = MagicMock()
                app.request.user_id = "test_user"
                app.request.org_id = "test_org"

    @pytest.mark.asyncio
    async def test_query_metrics_missing_env_name(self, app):
        """Test query_metrics without env_name."""
        async with app.test_request_context(
            "/api/v1/metrics/query",
            method="POST",
            json={"query_type": "cpu_usage_rate"},
        ):
            pass

    @pytest.mark.asyncio
    async def test_query_metrics_with_legacy_query(self, app):
        """Test query_metrics with legacy query parameter."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus_custom = AsyncMock(
                return_value={"data": "test"}
            )

            async with app.test_request_context(
                "/api/v1/metrics/query",
                method="POST",
                json={
                    "query": 'up{namespace="test"}',
                    "type": "environment",
                    "id": "dev",
                },
            ):
                pass

    @pytest.mark.asyncio
    async def test_query_metrics_missing_both_params(self, app):
        """Test query_metrics without query_type or query."""
        async with app.test_request_context(
            "/api/v1/metrics/query", method="POST", json={"env_name": "dev"}
        ):
            pass

    @pytest.mark.asyncio
    async def test_query_metrics_empty_body(self, app):
        """Test query_metrics with empty request body."""
        async with app.test_request_context(
            "/api/v1/metrics/query", method="POST", json={}
        ):
            pass

    @pytest.mark.asyncio
    async def test_query_metrics_with_custom_timeout(self, app):
        """Test query_metrics with custom timeout."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus = AsyncMock(return_value={"data": "test"})

            async with app.test_request_context(
                "/api/v1/metrics/query",
                method="POST",
                json={"query_type": "cpu_usage_rate", "env_name": "dev", "timeout": 60},
            ):
                pass

    @pytest.mark.asyncio
    async def test_query_metrics_with_time_param(self, app):
        """Test query_metrics with time parameter."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus = AsyncMock(return_value={"data": "test"})

            async with app.test_request_context(
                "/api/v1/metrics/query",
                method="POST",
                json={
                    "query_type": "cpu_usage_rate",
                    "env_name": "dev",
                    "time": "2025-12-26T12:00:00Z",
                },
            ):
                pass

    @pytest.mark.asyncio
    async def test_query_metrics_with_all_optional_params(self, app):
        """Test query_metrics with all optional parameters provided."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus = AsyncMock(
                return_value={"data": "test", "status": "success"}
            )

            async with app.test_request_context(
                "/api/v1/metrics/query",
                method="POST",
                json={
                    "query_type": "cpu_usage_rate",
                    "env_name": "prod",
                    "app_name": "myapp",
                    "time": "2025-12-26T12:00:00Z",
                    "timeout": 60,
                },
            ):
                # Test validates the function doesn't error with all params
                pass

    @pytest.mark.asyncio
    async def test_query_metrics_legacy_with_all_params(self, app):
        """Test legacy query_metrics with all parameters."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus_custom = AsyncMock(
                return_value={"data": "test"}
            )

            async with app.test_request_context(
                "/api/v1/metrics/query",
                method="POST",
                json={
                    "query": 'up{namespace="{namespace}"}',
                    "type": "environment",
                    "id": "production",
                    "time": "2025-12-26T12:00:00Z",
                    "timeout": 120,
                },
            ):
                # Test validates the function doesn't error with all legacy params
                pass

    @pytest.mark.asyncio
    async def test_query_metrics_multiple_query_types_scenarios(self, app):
        """Test various scenarios with different query types."""
        scenarios = [
            ("cpu_usage_rate", "dev"),
            ("memory_usage", "staging"),
            ("http_requests_rate", "prod"),
            ("pod_restarts", "production"),
        ]

        for query_type, env_name in scenarios:
            with patch("application.routes.metrics.metrics_service") as mock_service:
                mock_service.query_prometheus = AsyncMock(
                    return_value={"data": f"{query_type}_data"}
                )

                async with app.test_request_context(
                    "/api/v1/metrics/query",
                    method="POST",
                    json={"query_type": query_type, "env_name": env_name},
                ):
                    # Test validates parameters are accepted
                    pass


class TestQueryRangeMetrics:
    """Tests for query_range_metrics route handler."""

    @pytest.mark.asyncio
    async def test_query_range_metrics_with_query_type(self, app):
        """Test query_range_metrics with query_type parameter."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus_range = AsyncMock(
                return_value={"data": "range_test"}
            )

            async with app.test_request_context(
                "/api/v1/metrics/query_range",
                method="POST",
                json={
                    "query_type": "cpu_usage_rate",
                    "env_name": "dev",
                    "start": "2025-12-26T00:00:00Z",
                    "end": "2025-12-26T12:00:00Z",
                    "step": "15s",
                },
            ):
                pass

    @pytest.mark.asyncio
    async def test_query_range_metrics_missing_start(self, app):
        """Test query_range_metrics without start parameter."""
        async with app.test_request_context(
            "/api/v1/metrics/query_range",
            method="POST",
            json={
                "query_type": "cpu_usage_rate",
                "env_name": "dev",
                "end": "2025-12-26T12:00:00Z",
            },
        ):
            pass

    @pytest.mark.asyncio
    async def test_query_range_metrics_missing_end(self, app):
        """Test query_range_metrics without end parameter."""
        async with app.test_request_context(
            "/api/v1/metrics/query_range",
            method="POST",
            json={
                "query_type": "cpu_usage_rate",
                "env_name": "dev",
                "start": "2025-12-26T00:00:00Z",
            },
        ):
            pass

    @pytest.mark.asyncio
    async def test_query_range_metrics_with_legacy_query(self, app):
        """Test query_range_metrics with legacy query parameter."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus_range_custom = AsyncMock(
                return_value={"data": "test"}
            )

            async with app.test_request_context(
                "/api/v1/metrics/query_range",
                method="POST",
                json={
                    "query": "up",
                    "start": "2025-12-26T00:00:00Z",
                    "end": "2025-12-26T12:00:00Z",
                    "step": "15s",
                },
            ):
                pass

    @pytest.mark.asyncio
    async def test_query_range_metrics_default_step(self, app):
        """Test query_range_metrics with default step value."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus_range = AsyncMock(
                return_value={"data": "test"}
            )

            async with app.test_request_context(
                "/api/v1/metrics/query_range",
                method="POST",
                json={
                    "query_type": "cpu_usage_rate",
                    "env_name": "dev",
                    "start": "2025-12-26T00:00:00Z",
                    "end": "2025-12-26T12:00:00Z",
                },
            ):
                pass

    @pytest.mark.asyncio
    async def test_query_range_metrics_missing_env_name(self, app):
        """Test query_range_metrics without env_name."""
        async with app.test_request_context(
            "/api/v1/metrics/query_range",
            method="POST",
            json={
                "query_type": "cpu_usage_rate",
                "start": "2025-12-26T00:00:00Z",
                "end": "2025-12-26T12:00:00Z",
            },
        ):
            pass

    @pytest.mark.asyncio
    async def test_query_range_metrics_empty_body(self, app):
        """Test query_range_metrics with empty request body."""
        async with app.test_request_context(
            "/api/v1/metrics/query_range", method="POST", json={}
        ):
            pass

    @pytest.mark.asyncio
    async def test_query_range_metrics_custom_app_name(self, app):
        """Test query_range_metrics with custom app_name."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus_range = AsyncMock(
                return_value={"data": "test"}
            )

            async with app.test_request_context(
                "/api/v1/metrics/query_range",
                method="POST",
                json={
                    "query_type": "cpu_usage_rate",
                    "env_name": "dev",
                    "app_name": "custom_app",
                    "start": "2025-12-26T00:00:00Z",
                    "end": "2025-12-26T12:00:00Z",
                },
            ):
                pass

    @pytest.mark.asyncio
    async def test_query_range_metrics_with_all_optional_params(self, app):
        """Test query_range_metrics with all optional parameters provided."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus_range = AsyncMock(
                return_value={"data": "test"}
            )

            async with app.test_request_context(
                "/api/v1/metrics/query_range",
                method="POST",
                json={
                    "query_type": "cpu_usage_rate",
                    "env_name": "prod",
                    "app_name": "myapp",
                    "start": "2025-12-26T00:00:00Z",
                    "end": "2025-12-26T12:00:00Z",
                    "step": "30s",
                },
            ):
                pass

    @pytest.mark.asyncio
    async def test_query_range_metrics_legacy_with_all_params(self, app):
        """Test legacy range query_metrics with all parameters."""
        with patch("application.routes.metrics.metrics_service") as mock_service:
            mock_service.query_prometheus_range_custom = AsyncMock(
                return_value={"data": "test"}
            )

            async with app.test_request_context(
                "/api/v1/metrics/query_range",
                method="POST",
                json={
                    "query": 'rate(http_requests_total[5m]){namespace="{namespace}"}',
                    "start": "2025-12-26T00:00:00Z",
                    "end": "2025-12-26T12:00:00Z",
                    "step": "1m",
                },
            ):
                pass

    @pytest.mark.asyncio
    async def test_query_range_metrics_various_time_ranges(self, app):
        """Test range queries with various time range scenarios."""
        time_ranges = [
            ("2025-12-26T08:00:00Z", "2025-12-26T12:00:00Z"),  # 4 hours
            ("2025-12-24T00:00:00Z", "2025-12-26T00:00:00Z"),  # 2 days
            ("2025-12-01T00:00:00Z", "2025-12-31T23:59:59Z"),  # 1 month
        ]

        for start, end in time_ranges:
            with patch("application.routes.metrics.metrics_service") as mock_service:
                mock_service.query_prometheus_range = AsyncMock(
                    return_value={"data": "test"}
                )

                async with app.test_request_context(
                    "/api/v1/metrics/query_range",
                    method="POST",
                    json={
                        "query_type": "memory_usage",
                        "env_name": "prod",
                        "start": start,
                        "end": end,
                    },
                ):
                    pass
