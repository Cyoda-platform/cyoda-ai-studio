"""User-specific service container for multi-tenant Cyoda access."""

from __future__ import annotations

import logging
from typing import Any, Optional
from urllib.parse import urlparse

from common.auth.cyoda_auth import CyodaAuthService
from common.interfaces.services import IAuthService
from common.repository.cyoda.cyoda_repository import CyodaRepository
from common.service.service import EntityServiceImpl

logger = logging.getLogger(__name__)


class UserEnvironmentRepository(CyodaRepository):
    """Repository subclass that uses user's environment API URL."""

    def __new__(cls, cyoda_auth_service: Any, api_url: str) -> "UserEnvironmentRepository":  # type: ignore[override]
        """Create new instance (not a singleton like parent)."""
        # Bypass singleton check by using object.__new__
        return object.__new__(cls)

    def __init__(self, cyoda_auth_service: Any, api_url: str) -> None:
        """Initialize with user's API URL.

        Args:
            cyoda_auth_service: Auth service for the user's environment
            api_url: User's environment API URL (e.g., https://client-123.eu.cyoda.net/api)
        """
        super().__init__(cyoda_auth_service, api_url=api_url)


class UserServiceContainer:
    """Creates user-specific services with provided credentials."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        cyoda_host: str,
        skip_ssl: bool = False,
    ):
        """Initialize user service container with credentials.

        Args:
            client_id: User's Cyoda client ID
            client_secret: User's Cyoda client secret
            cyoda_host: User's Cyoda host (e.g., 'client-123.eu.cyoda.net' or full URL)
            skip_ssl: Skip SSL verification (default: False)
        """
        self.client_id = client_id
        self.cyoda_host = cyoda_host
        self.token_url = self._derive_token_url(cyoda_host)
        self.api_url = self._derive_api_url(cyoda_host, skip_ssl)

        # Create auth service for this user environment
        self._auth_service = CyodaAuthService(
            client_id=client_id,
            client_secret=client_secret,
            token_url=self.token_url,
            skip_ssl=skip_ssl,
            scope="read write",
        )

        # Initialize services
        self._repository: Optional[CyodaRepository] = None
        self._entity_service: Optional[EntityServiceImpl] = None

    def _derive_token_url(self, cyoda_host: str) -> str:
        """Derive token URL from user's Cyoda host.

        Handles both hostname and full URL formats.
        User authenticates against their own environment.

        Args:
            cyoda_host: User's Cyoda host (hostname or full URL)

        Returns:
            Full OAuth token URL
        """
        # Extract hostname and protocol from URL if needed
        if cyoda_host.startswith("http://") or cyoda_host.startswith("https://"):
            parsed = urlparse(cyoda_host)
            hostname = parsed.hostname or cyoda_host
            protocol = parsed.scheme
        else:
            hostname = cyoda_host
            protocol = "http" if "localhost" in hostname else "https"

        return f"{protocol}://{hostname}/api/oauth/token"

    def _derive_api_url(self, cyoda_host: str, skip_ssl: bool) -> str:
        """Derive API URL from user's Cyoda host.

        Handles both hostname and full URL formats.
        User makes API calls against their own environment.

        Args:
            cyoda_host: User's Cyoda host (hostname or full URL)
            skip_ssl: Skip SSL verification

        Returns:
            Full API base URL
        """
        # Extract hostname and protocol from URL if needed
        if cyoda_host.startswith("http://") or cyoda_host.startswith("https://"):
            parsed = urlparse(cyoda_host)
            hostname = parsed.hostname or cyoda_host
            protocol = parsed.scheme
        else:
            hostname = cyoda_host
            protocol = "http" if "localhost" in hostname else "https"

        return f"{protocol}://{hostname}/api"

    def get_auth_service(self) -> IAuthService:
        """Get auth service for this user environment."""
        return self._auth_service

    def get_repository(self) -> UserEnvironmentRepository:
        """Get or create repository for user's environment."""
        if self._repository is None:
            auth_service = self.get_auth_service()
            self._repository = UserEnvironmentRepository(
                cyoda_auth_service=auth_service,
                api_url=self.api_url,
            )
        return self._repository  # type: ignore[return-value]

    def get_entity_service(self) -> EntityServiceImpl:
        """Get or create entity service."""
        if self._entity_service is None:
            repository = self.get_repository()
            self._entity_service = EntityServiceImpl(repository=repository)
        return self._entity_service