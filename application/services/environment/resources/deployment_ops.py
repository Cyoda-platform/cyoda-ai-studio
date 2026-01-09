"""Deployment-level operations for Kubernetes resources."""

import logging
from typing import Any, Dict, Optional

import httpx

from application.services.environment.auth import CloudManagerAuthService
from application.services.environment.utils import sanitize_namespace

logger = logging.getLogger(__name__)


class DeploymentOperations:
    """Operations on Kubernetes deployments."""

    def __init__(self, auth_service: CloudManagerAuthService):
        self.auth_service = auth_service
        self.cloud_manager_host = auth_service.cloud_manager_host
        self.protocol = auth_service.protocol

    def _get_base_url(self) -> str:
        if not self.cloud_manager_host:
            raise Exception("CLOUD_MANAGER_HOST not configured")
        return f"{self.protocol}://{self.cloud_manager_host}"

    async def get_application_details(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Get details for a specific application deployment."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        namespace = f"client-{sanitized_user}-{sanitized_env}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}/deployments/{app_name}"

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def scale_application(
        self, user_id: str, env_name: str, app_name: str, replicas: int
    ) -> Dict[str, Any]:
        """Scale an application deployment."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        namespace = f"client-{sanitized_user}-{sanitized_env}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}/deployments/{app_name}/scale"

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"replicas": replicas}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(api_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    async def restart_application(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Restart an application deployment."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        namespace = f"client-{sanitized_user}-{sanitized_env}"

        api_url = (
            f"{base_url}/k8s/namespaces/{namespace}/deployments/{app_name}/restart"
        )

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def update_application_image(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        image: str,
        container: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update container image for an application."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        namespace = f"client-{sanitized_user}-{sanitized_env}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}/deployments/{app_name}/rollout/update"

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"image": image}
        if container:
            payload["container"] = container

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(api_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_application_status_rollout(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Get rollout status of an application."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        namespace = f"client-{sanitized_user}-{sanitized_env}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}/deployments/{app_name}/rollout/status"

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
