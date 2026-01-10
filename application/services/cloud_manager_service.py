"""Centralized Cloud Manager API service with token caching and connection pooling."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class CloudManagerService:
    """Centralized service for Cloud Manager API with token caching and reusable HTTP client.

    This class addresses performance concerns by:
    1. Maintaining a single httpx.AsyncClient instance for connection pooling
    2. Caching authentication tokens to avoid redundant auth requests
    3. Automatically refreshing tokens when they expire
    4. Centralizing configuration (base URL, timeouts, headers)

    Thread-safe for async operations using asyncio.Lock.
    """

    def __init__(self):
        """Initialize the Cloud Manager service."""
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._auth_lock = asyncio.Lock()
        self._config_lock = asyncio.Lock()

        # Token lifetime: assume 1 hour, refresh 5 minutes before expiry
        self.token_lifetime_seconds = 3600
        self.token_refresh_buffer_seconds = 300

    async def _ensure_client_initialized(self) -> httpx.AsyncClient:
        """Ensure the HTTP client is initialized and return it.

        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._client is None:
            async with self._config_lock:
                if self._client is None:  # Double-check after acquiring lock
                    cloud_manager_host = os.getenv(
                        "CLOUD_MANAGER_HOST", "cloud-manager-cyoda.kube3.cyoda.org"
                    )
                    protocol = "http" if "localhost" in cloud_manager_host else "https"
                    base_url = f"{protocol}://{cloud_manager_host}"

                    self._client = httpx.AsyncClient(
                        base_url=base_url,
                        timeout=30.0,
                        headers={
                            "X-Requested-With": "XMLHttpRequest",
                            "Content-Type": "application/json",
                        },
                    )
                    logger.info(
                        f"Initialized Cloud Manager client with base URL: {base_url}"
                    )

        return self._client

    def _is_token_valid(self) -> bool:
        """Check if the current token is still valid.

        Returns:
            True if token exists and hasn't expired (with buffer), False otherwise
        """
        if not self._token:
            return False

        # Add buffer time to avoid using token right before expiry
        return time.time() < (self._token_expiry - self.token_refresh_buffer_seconds)

    async def _authenticate(self) -> str:
        """Authenticate with Cloud Manager and obtain access token.

        Returns:
            Access token string

        Raises:
            Exception: If authentication fails or credentials are not configured
        """
        # Get credentials from environment
        cloud_manager_api_key_encoded = os.getenv("CLOUD_MANAGER_API_KEY")
        cloud_manager_api_secret_encoded = os.getenv("CLOUD_MANAGER_API_SECRET")

        if not cloud_manager_api_key_encoded or not cloud_manager_api_secret_encoded:
            raise Exception(
                "Cloud manager credentials not configured. "
                "Set CLOUD_MANAGER_API_KEY and CLOUD_MANAGER_API_SECRET."
            )

        # Decode base64 credentials
        cloud_manager_api_key = base64.b64decode(cloud_manager_api_key_encoded).decode(
            "utf-8"
        )
        cloud_manager_api_secret = base64.b64decode(
            cloud_manager_api_secret_encoded
        ).decode("utf-8")

        # Prepare authentication request
        auth_payload = {
            "username": cloud_manager_api_key,
            "password": cloud_manager_api_secret,
        }

        # Use separate auth host (cloud-manager-cyoda) for authentication
        # Default to cloud-manager-cyoda.<CLIENT_HOST> if CLOUD_MANAGER_AUTH_HOST not set
        client_host = os.getenv("CLIENT_HOST", "kube3.cyoda.org")
        default_auth_host = f"cloud-manager-cyoda.{client_host}"
        auth_host = os.getenv("CLOUD_MANAGER_AUTH_HOST", default_auth_host)
        auth_base_url = f"https://{auth_host}"

        try:
            async with httpx.AsyncClient(
                base_url=auth_base_url,
                timeout=30.0,
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/json",
                },
            ) as auth_client:
                auth_response = await auth_client.post(
                    "/api/auth/login", json=auth_payload
                )
                auth_response.raise_for_status()
                auth_data = auth_response.json()
                access_token = auth_data.get("token")

                if not access_token:
                    raise Exception(
                        "Failed to authenticate with cloud manager: no token in response"
                    )

                logger.info("Successfully authenticated with Cloud Manager")
                return access_token

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Authentication failed with status {e.response.status_code}: {e.response.text}"
            )
            raise Exception(
                f"Cloud Manager authentication failed: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise

    async def get_token(self) -> str:
        """Get a valid authentication token, refreshing if necessary.

        This method is thread-safe and will reuse cached tokens when valid.

        Returns:
            Valid access token

        Raises:
            Exception: If authentication fails
        """
        # Fast path: token is valid, return immediately without lock
        if self._is_token_valid():
            return self._token

        # Slow path: need to refresh token, acquire lock
        async with self._auth_lock:
            # Double-check: another coroutine may have refreshed while we waited
            if self._is_token_valid():
                return self._token

            # Authenticate and cache token
            self._token = await self._authenticate()
            self._token_expiry = time.time() + self.token_lifetime_seconds

            return self._token

    async def request(
        self, method: str, path: str, *, retry_auth: bool = True, **kwargs: Any
    ) -> httpx.Response:
        """Make an authenticated request to the Cloud Manager API.

        Automatically adds authentication header and retries once on 401 errors.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API endpoint path (e.g., "/api/environments")
            retry_auth: Whether to retry with fresh token on 401 error
            **kwargs: Additional arguments passed to httpx request (json, params, etc.)

        Returns:
            HTTP response

        Raises:
            httpx.HTTPStatusError: If request fails (after potential retry)
        """
        client = await self._ensure_client_initialized()
        token = await self.get_token()

        # Add authorization header
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        try:
            response = await client.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            # If 401 Unauthorized and retry is enabled, refresh token and try once more
            if e.response.status_code == 401 and retry_auth:
                logger.warning(
                    "Received 401 Unauthorized, refreshing token and retrying..."
                )

                # Force token refresh
                async with self._auth_lock:
                    self._token = None
                    self._token_expiry = 0

                # Retry with fresh token (disable retry to avoid infinite loop)
                return await self.request(
                    method, path, retry_auth=False, headers=headers, **kwargs
                )

            # Re-raise for all other errors or if retry already attempted
            raise

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated GET request."""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated POST request."""
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated PUT request."""
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated PATCH request."""
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated DELETE request."""
        return await self.request("DELETE", path, **kwargs)

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._token = None
            self._token_expiry = 0
            logger.info("Cloud Manager client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Global singleton instance
_global_service: Optional[CloudManagerService] = None
_global_service_lock = asyncio.Lock()


async def get_cloud_manager_service() -> CloudManagerService:
    """Get or create the global Cloud Manager service instance.

    This function provides a singleton service that can be reused across
    the application to avoid creating multiple HTTP clients.

    Returns:
        Shared CloudManagerService instance
    """
    global _global_service

    if _global_service is None:
        async with _global_service_lock:
            if _global_service is None:  # Double-check after acquiring lock
                _global_service = CloudManagerService()
                logger.info("Created global Cloud Manager service")

    return _global_service


async def reset_cloud_manager_service():
    """Reset the global service (useful for testing or config changes).

    This will close the existing service and force creation of a new one
    on the next call to get_cloud_manager_service().
    """
    global _global_service

    async with _global_service_lock:
        if _global_service:
            await _global_service.close()
            _global_service = None
            logger.info("Reset global Cloud Manager service")
