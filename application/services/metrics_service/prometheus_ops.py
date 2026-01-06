"""Prometheus operations for querying metrics."""

import logging
from typing import Dict, Optional

import httpx

from application.routes.common.constants import DEFAULT_HTTP_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class PrometheusOperations:
    """Operations for querying Prometheus metrics."""

    @staticmethod
    async def query(
        prometheus_host: str,
        query: str,
        time: Optional[str] = None,
        timeout: Optional[str] = None,
    ) -> Dict:
        """Query Prometheus metrics.

        Args:
            prometheus_host: Prometheus host URL
            query: Prometheus query string
            time: Optional evaluation timestamp
            timeout: Optional query timeout

        Returns:
            Prometheus query results

        Raises:
            Exception: If query fails

        Example:
            >>> result = await PrometheusOperations.query(
            ...     'prometheus.example.com',
            ...     'up{namespace="client-myorg-dev"}'
            ... )
        """
        params = {"query": query}
        if time:
            params["time"] = time
        if timeout:
            params["timeout"] = timeout

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(
            timeout=DEFAULT_HTTP_TIMEOUT_SECONDS, verify=False
        ) as client:
            response = await client.post(
                f"https://{prometheus_host}/api/v1/query",
                headers=headers,
                data=params,
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Prometheus query failed: {response.text}")

            return response.json()

    @staticmethod
    async def query_range(
        prometheus_host: str,
        query: str,
        start: str,
        end: str,
        step: str = "15s",
    ) -> Dict:
        """Query Prometheus with a time range.

        Args:
            prometheus_host: Prometheus host URL
            query: Prometheus query string
            start: Start time (ISO 8601 or Unix timestamp)
            end: End time (ISO 8601 or Unix timestamp)
            step: Query resolution step interval

        Returns:
            Prometheus range query results

        Raises:
            Exception: If query fails

        Example:
            >>> result = await PrometheusOperations.query_range(
            ...     'prometheus.example.com',
            ...     'up{namespace=~"client-myorg-.*"}',
            ...     "2025-12-17T00:00:00Z",
            ...     "2025-12-17T12:00:00Z"
            ... )
        """
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(
            timeout=DEFAULT_HTTP_TIMEOUT_SECONDS, verify=False
        ) as client:
            response = await client.post(
                f"https://{prometheus_host}/api/v1/query_range",
                headers=headers,
                data=params,
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Prometheus range query failed: {response.text}")

            return response.json()
