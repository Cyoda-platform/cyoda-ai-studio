"""Grafana operations for service account management."""

import base64
import logging
from typing import Dict

import httpx

from application.routes.common.constants import (
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    SERVICE_ACCOUNT_TOKEN_EXPIRY_SECONDS,
)

logger = logging.getLogger(__name__)


class GrafanaOperations:
    """Operations for Grafana service account management."""

    @staticmethod
    def create_basic_auth_header(username: str, password: str) -> str:
        """Create Basic Authentication header value.

        Args:
            username: Username
            password: Password

        Returns:
            Base64-encoded auth string
        """
        auth_string = f"{username}:{password}"
        auth_bytes = auth_string.encode("ascii")
        return base64.b64encode(auth_bytes).decode("ascii")

    @staticmethod
    async def find_or_create_service_account(
        client: httpx.AsyncClient,
        base_url: str,
        headers: Dict,
        sa_name: str,
    ) -> str:
        """Find existing service account or create new one.

        Args:
            client: HTTP client.
            base_url: Grafana base URL.
            headers: HTTP headers with auth.
            sa_name: Service account name.

        Returns:
            Service account ID.

        Raises:
            Exception: If list or create fails.
        """
        # List existing service accounts
        sa_list_response = await client.get(
            f"{base_url}/api/serviceaccounts/search", headers=headers
        )

        if sa_list_response.status_code != 200:
            raise Exception(
                f"Failed to list service accounts: {sa_list_response.text}"
            )

        service_accounts = sa_list_response.json()
        existing_sa = next(
            (
                sa
                for sa in service_accounts.get("serviceAccounts", [])
                if sa["name"] == sa_name
            ),
            None,
        )

        if existing_sa:
            logger.info(f"Found existing service account: {existing_sa['id']}")
            return existing_sa["id"]

        # Create new service account
        sa_create_response = await client.post(
            f"{base_url}/api/serviceaccounts",
            headers=headers,
            json={"name": sa_name, "role": "Viewer", "isDisabled": False},
        )

        if sa_create_response.status_code not in [200, 201]:
            raise Exception(
                f"Failed to create service account: {sa_create_response.text}"
            )

        sa_data = sa_create_response.json()
        sa_id = sa_data["id"]
        logger.info(f"Created service account with ID: {sa_id}")
        return sa_id

    @staticmethod
    async def create_service_account_token(
        client: httpx.AsyncClient,
        base_url: str,
        headers: Dict,
        sa_id: str,
        token_name: str,
    ) -> str:
        """Create service account token.

        Args:
            client: HTTP client.
            base_url: Grafana base URL.
            headers: HTTP headers with auth.
            sa_id: Service account ID.
            token_name: Token name.

        Returns:
            Generated token string.

        Raises:
            Exception: If token creation fails.
        """
        token_response = await client.post(
            f"{base_url}/api/serviceaccounts/{sa_id}/tokens",
            headers=headers,
            json={
                "name": token_name,
                "secondsToLive": SERVICE_ACCOUNT_TOKEN_EXPIRY_SECONDS,
            },
        )

        if token_response.status_code not in [200, 201]:
            raise Exception(f"Failed to create token: {token_response.text}")

        token_data = token_response.json()
        return token_data["key"]

    @staticmethod
    def format_token_response(
        token: str,
        sa_name: str,
        sa_id: str,
        grafana_host: str,
        org_id: str,
    ) -> Dict:
        """Format token response dictionary.

        Args:
            token: Generated token.
            sa_name: Service account name.
            sa_id: Service account ID.
            grafana_host: Grafana host.
            org_id: Organization ID.

        Returns:
            Formatted response dictionary.
        """
        return {
            "token": token,
            "name": sa_name,
            "service_account_id": sa_id,
            "grafana_url": f"https://{grafana_host}",
            "namespace": f"client-{org_id}",
            "message": "Token generated. Save it securely - you won't be able to see it again.",
            "expires_in_days": 365,
        }
