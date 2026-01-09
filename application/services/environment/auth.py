"""Authentication service for Cloud Manager."""

import base64
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class CloudManagerAuthService:
    """Handles authentication with the Cloud Manager API."""

    def __init__(self, cloud_manager_host: Optional[str] = None):
        """Initialize auth service."""
        self.cloud_manager_host = cloud_manager_host or os.getenv("CLOUD_MANAGER_HOST")
        self.api_key_encoded = os.getenv("CLOUD_MANAGER_API_KEY")
        self.api_secret_encoded = os.getenv("CLOUD_MANAGER_API_SECRET")

        # Determine protocol
        self.protocol = (
            "http"
            if self.cloud_manager_host and "localhost" in self.cloud_manager_host
            else "https"
        )

    async def get_token(self) -> str:
        """Get authentication token for cloud manager API."""
        if not self.api_key_encoded or not self.api_secret_encoded:
            raise Exception(
                "Cloud manager credentials not configured "
                "(CLOUD_MANAGER_API_KEY, CLOUD_MANAGER_API_SECRET)"
            )

        try:
            # Decode base64 credentials
            api_key = base64.b64decode(self.api_key_encoded).decode("utf-8")
            api_secret = base64.b64decode(self.api_secret_encoded).decode("utf-8")
        except Exception as e:
            raise Exception(f"Failed to decode Cloud Manager credentials: {e}")

        # Authenticate
        host = self.cloud_manager_host or "cloud-manager-cyoda.kube3.cyoda.org"
        auth_url = f"{self.protocol}://{host}/api/auth/login"

        auth_payload = {
            "username": api_key,
            "password": api_secret,
        }
        auth_headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                auth_response = await client.post(
                    auth_url, json=auth_payload, headers=auth_headers
                )
                auth_response.raise_for_status()
                auth_data = auth_response.json()
                access_token = auth_data.get("token")

                if not access_token:
                    raise Exception("Auth response did not contain token")

                return access_token
            except httpx.HTTPStatusError as e:
                logger.error(f"Auth failed: {e.response.text}")
                raise Exception(f"Authentication failed: {e.response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"Auth request failed: {e}")
                raise Exception(f"Authentication request failed: {str(e)}")
