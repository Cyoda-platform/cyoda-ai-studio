"""Service for deployment operations (Cyoda environments and User apps)."""

import logging
import os
from typing import Any, Dict, Optional

import httpx

from application.services.environment.auth import CloudManagerAuthService
from application.services.environment.utils import sanitize_keyspace, sanitize_namespace

logger = logging.getLogger(__name__)


class EnvironmentDeploymentService:
    """Handles deployment operations via Cloud Manager."""

    def __init__(self, auth_service: CloudManagerAuthService):
        self.auth_service = auth_service
        self.cloud_manager_host = auth_service.cloud_manager_host
        self.protocol = auth_service.protocol

    def _get_base_url(self) -> str:
        if not self.cloud_manager_host:
            raise Exception("CLOUD_MANAGER_HOST not configured")
        return f"{self.protocol}://{self.cloud_manager_host}"

    async def deploy_environment(
        self, user_id: str, chat_id: str, env_name: str, build_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Deploy a Cyoda environment."""
        base_url = self._get_base_url()
        deploy_url = os.getenv("DEPLOY_CYODA_ENV", f"{base_url}/deploy/cyoda-env")

        # Truncate env_name to 10 chars as per convention
        env_name_truncated = env_name[:10]

        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name_truncated)

        user_defined_namespace = f"client-{sanitized_user}-{sanitized_env}"

        keyspace_user = sanitize_keyspace(user_id)
        keyspace_env = sanitize_keyspace(env_name_truncated)
        user_defined_keyspace = f"c_{keyspace_user}_{keyspace_env}"

        payload = {
            "user_name": user_id,
            "chat_id": chat_id,
            "user_defined_namespace": user_defined_namespace,
            "user_defined_keyspace": user_defined_keyspace,
        }

        if build_id:
            payload["build_id"] = build_id

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(deploy_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            return {
                "build_id": data.get("build_id"),
                "namespace": data.get("build_namespace"),
            }

    def _build_namespaces(
        self, user_id: str, env_name: str, app_name: str
    ) -> tuple[str, str]:
        """Build cyoda and app namespaces.

        Args:
            user_id: User ID
            env_name: Environment name
            app_name: Application name

        Returns:
            Tuple of (cyoda_namespace, app_namespace)
        """
        env_name_truncated = env_name[:10]
        app_name_truncated = app_name[:10]

        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name_truncated)
        sanitized_app = sanitize_namespace(app_name_truncated)

        cyoda_namespace = f"client-{sanitized_user}-{sanitized_env}"
        app_namespace = f"client-1-{sanitized_user}-{sanitized_env}-{sanitized_app}"

        return cyoda_namespace, app_namespace

    def _build_deployment_payload(
        self,
        branch_name: str,
        chat_id: str,
        cyoda_client_id: str,
        cyoda_client_secret: str,
        is_public: bool,
        repository_url: str,
        user_id: str,
        app_namespace: str,
        cyoda_namespace: str,
        installation_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Build deployment payload.

        Args:
            branch_name: Git branch
            chat_id: Chat ID
            cyoda_client_id: Cyoda client ID
            cyoda_client_secret: Cyoda client secret
            is_public: Whether repository is public
            repository_url: Repository URL
            user_id: User ID
            app_namespace: App namespace
            cyoda_namespace: Cyoda namespace
            installation_id: Optional GitHub installation ID

        Returns:
            Deployment payload dictionary
        """
        payload = {
            "branch_name": branch_name,
            "chat_id": chat_id,
            "cyoda_client_id": cyoda_client_id,
            "cyoda_client_secret": cyoda_client_secret,
            "is_public": str(is_public).lower(),
            "repository_url": repository_url,
            "user_name": user_id,
            "app_namespace": app_namespace,
            "cyoda_namespace": cyoda_namespace,
        }

        if installation_id:
            payload["installation_id"] = installation_id
        elif is_public:
            env_installation_id = os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID")
            if env_installation_id:
                payload["installation_id"] = env_installation_id

        return payload

    async def deploy_user_application(
        self,
        user_id: str,
        chat_id: str,
        env_name: str,
        app_name: str,
        repository_url: str,
        branch_name: str,
        cyoda_client_id: str,
        cyoda_client_secret: str,
        is_public: bool = True,
        installation_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Deploy a user application."""
        base_url = self._get_base_url()
        deploy_url = os.getenv("DEPLOY_USER_APP", f"{base_url}/deploy/user-app")

        cyoda_namespace, app_namespace = self._build_namespaces(
            user_id, env_name, app_name
        )

        payload = self._build_deployment_payload(
            branch_name=branch_name,
            chat_id=chat_id,
            cyoda_client_id=cyoda_client_id,
            cyoda_client_secret=cyoda_client_secret,
            is_public=is_public,
            repository_url=repository_url,
            user_id=user_id,
            app_namespace=app_namespace,
            cyoda_namespace=cyoda_namespace,
            installation_id=installation_id,
        )

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(deploy_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            return {
                "build_id": data.get("build_id"),
                "namespace": data.get("build_namespace") or data.get("namespace"),
            }

    async def get_deployment_status(self, build_id: str) -> Dict[str, Any]:
        """Get status of a deployment build."""
        base_url = self._get_base_url()
        status_url = os.getenv(
            "DEPLOY_CYODA_ENV_STATUS", f"{base_url}/deploy/cyoda-env/status"
        )

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{status_url}?build_id={build_id}", headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def get_build_logs(self, build_id: str, max_lines: int = 100) -> str:
        """Get logs for a deployment build."""
        base_url = self._get_base_url()
        logs_url = os.getenv("BUILD_LOGS_URL", f"{base_url}/build/logs")

        # Note: Original code didn't use auth for logs, keeping consistent
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{logs_url}?build_id={build_id}&max_lines={max_lines}"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("logs", "")
