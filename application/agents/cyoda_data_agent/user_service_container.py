"""User-specific service container for multi-tenant Cyoda access."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from common.auth.cyoda_auth import CyodaAuthService
from common.interfaces.services import IAuthService
from common.repository.cyoda.cyoda_repository import CyodaRepository
from common.service.service import EntityServiceImpl
from common.utils.utils import send_cyoda_request

logger = logging.getLogger(__name__)


class UserEnvironmentRepository(CyodaRepository):
    """Repository subclass that uses user's environment API URL."""

    def __new__(cls, cyoda_auth_service: Any, api_url: str) -> "UserEnvironmentRepository":  # type: ignore[override]
        """Create new instance (not a singleton like parent)."""
        return super(CyodaRepository, cls).__new__(cls)

    def __init__(self, cyoda_auth_service: Any, api_url: str) -> None:
        """Initialize with user's API URL.

        Args:
            cyoda_auth_service: Auth service for the user's environment
            api_url: User's environment API URL (e.g., https://client-123.eu.cyoda.net/api)
        """
        self._cyoda_auth_service = cyoda_auth_service
        self._api_url = api_url

    async def find_by_id(self, meta: Dict[str, Any], entity_id: str) -> Optional[Dict[str, Any]]:
        """Find entity by ID using user's API URL."""
        path = f"entity/{entity_id}"
        resp = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service,
            method="get",
            path=path,
            base_url=self._api_url,
        )
        if resp.get("status") == 404:
            return None
        payload = resp.get("json", {})
        if not isinstance(payload, dict):
            return None
        payload_data: Dict[str, Any] = payload.get("data", {}) or {}
        meta_payload = payload.get("meta", {}) or {}
        payload_data["current_state"] = meta_payload.get("state")
        payload_data["technical_id"] = entity_id
        return payload_data

    async def find_all(self, meta: Dict[str, Any]) -> list[Any]:
        """Find all entities using user's API URL."""
        path = f"entity/{meta['entity_model']}/{meta['entity_version']}"
        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service,
            method="get",
            path=path,
            base_url=self._api_url,
        )
        result = resp.get("json", [])
        if not isinstance(result, list):
            return []
        return result

    async def find_all_by_criteria(
        self,
        meta: Dict[str, Any],
        criteria: Any,
        point_in_time: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        """Find entities by criteria using user's API URL."""
        import json
        import time

        start_time = time.time()
        search_path = f"search/{meta['entity_model']}/{meta['entity_version']}"

        query_params = []
        if point_in_time:
            pit_str = point_in_time.isoformat()
            query_params.append(f"clientPointTime={pit_str}")

        if limit is not None:
            query_params.append(f"limit={min(limit, 10000)}")

        if query_params:
            search_path = f"{search_path}?{'&'.join(query_params)}"

        search_criteria: Dict[str, Any] = self._ensure_cyoda_format(criteria)

        resp = await self._send_search_request(
            method="post",
            path=search_path,
            data=json.dumps(search_criteria),
            base_url=self._api_url,
        )

        elapsed_time = time.time() - start_time

        if resp.get("status") != 200:
            return []

        entities_any = resp.get("json", [])
        entities = self._coerce_list_of_dicts(entities_any)
        result = self._ensure_technical_id_on_entities(entities)

        return result

    async def search(
        self,
        meta: Dict[str, Any],
        criteria: Dict[str, Any],
        point_in_time: Optional[Any] = None,
        limit: Optional[int] = None,
    ) -> list[Any]:
        """Search entities using user's API URL."""
        return await self.find_all_by_criteria(meta, criteria, point_in_time, limit)

    async def save(self, meta: Dict[str, Any], entity: Any) -> Optional[str]:
        """Save entity using user's API URL."""
        import json
        from common.utils.utils import custom_serializer

        data = json.dumps(entity, default=custom_serializer)
        path = (
            f"entity/JSON/{meta['entity_model']}/{meta['entity_version']}"
            "?waitForConsistencyAfter=true"
        )
        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service,
            method="post",
            path=path,
            data=data,
            base_url=self._api_url,
        )
        result = resp.get("json", [])
        return self._extract_technical_id_from_result(result)

    async def save_all(self, meta: Dict[str, Any], entities: list[Any]) -> Optional[str]:
        """Save multiple entities using user's API URL."""
        import json
        from common.utils.utils import custom_serializer

        data = json.dumps(entities, default=custom_serializer)
        path = f"entity/JSON/{meta['entity_model']}/{meta['entity_version']}"
        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service,
            method="post",
            path=path,
            data=data,
            base_url=self._api_url,
        )
        result = resp.get("json", [])
        return self._extract_technical_id_from_result(result)

    async def update(
        self, meta: Dict[str, Any], technical_id: Any, entity: Optional[Any] = None
    ) -> Optional[str]:
        """Update entity using user's API URL."""
        import json
        from common.utils.utils import custom_serializer

        if entity is None:
            await self._launch_transition(meta=meta, technical_id=str(technical_id))
            return None

        transition: str = meta.get("update_transition")
        if transition:
            path = (
                f"entity/JSON/{technical_id}/{transition}"
                "?transactional=true&waitForConsistencyAfter=true"
            )
        else:
            path = f"entity/JSON/{technical_id}?waitForConsistencyAfter=true"

        data = json.dumps(entity, default=custom_serializer)
        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service,
            method="put",
            path=path,
            data=data,
            base_url=self._api_url,
        )
        result = resp.get("json", {})
        if not isinstance(result, dict):
            return None
        ids = result.get("entityIds", [None])
        if isinstance(ids, list) and ids and ids[0] is not None:
            return str(ids[0])
        return None

    async def delete_by_id(self, meta: Dict[str, Any], technical_id: Any) -> None:
        """Delete entity using user's API URL."""
        path = f"entity/{technical_id}"
        await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service,
            method="delete",
            path=path,
            base_url=self._api_url,
        )

    async def delete_all(self, meta: Dict[str, Any]) -> None:
        """Delete all entities using user's API URL."""
        path = f"entity/{meta['entity_model']}/{meta['entity_version']}"
        await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service,
            method="delete",
            path=path,
            base_url=self._api_url,
        )


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



