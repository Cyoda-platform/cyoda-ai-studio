"""User application operations for Kubernetes resources."""

import logging
from typing import Any, Dict, Optional

import httpx

from application.services.environment.auth import CloudManagerAuthService
from application.services.environment.utils import sanitize_namespace

logger = logging.getLogger(__name__)


class UserAppOperations:
    """Operations on user application deployments."""

    def __init__(self, auth_service: CloudManagerAuthService):
        self.auth_service = auth_service
        self.cloud_manager_host = auth_service.cloud_manager_host
        self.protocol = auth_service.protocol

    def _get_base_url(self) -> str:
        if not self.cloud_manager_host:
            raise Exception("CLOUD_MANAGER_HOST not configured")
        return f"{self.protocol}://{self.cloud_manager_host}"

    async def get_user_app_deployments(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Get deployments for a user application (in its own namespace)."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        sanitized_app = sanitize_namespace(app_name)

        # User app namespace format: client-1-{user}-{env}-{app}
        namespace = f"client-1-{sanitized_user}-{sanitized_env}-{sanitized_app}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}/deployments"

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            # Handle 404 gracefully if needed, but let's raise for now or handle in caller
            response.raise_for_status()
            data = response.json()

            return {
                "environment": env_name,
                "app_name": app_name,
                "namespace": namespace,
                "deployments": data.get("deployments", []),
            }

    async def scale_user_app(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        replicas: int,
        deployment_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Scale a user application deployment."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        sanitized_app = sanitize_namespace(app_name)
        namespace = f"client-1-{sanitized_user}-{sanitized_env}-{sanitized_app}"

        # Track if deployment_name was explicitly provided
        deployment_name_provided = deployment_name is not None

        # Use provided deployment_name or default to app name
        if not deployment_name:
            deployment_name = sanitized_app

        api_url = (
            f"{base_url}/k8s/namespaces/{namespace}/deployments/{deployment_name}/scale"
        )
        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"replicas": replicas}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(api_url, json=payload, headers=headers)

            # Auto-detect deployment if 404 and deployment_name wasn't explicitly provided
            if response.status_code == 404 and not deployment_name_provided:
                list_url = f"{base_url}/k8s/namespaces/{namespace}/deployments"
                resp_list = await client.get(list_url, headers=headers)
                if resp_list.status_code == 200:
                    deps = resp_list.json().get("deployments", [])
                    if deps:
                        deployment_name = deps[0]["name"]
                        api_url = f"{base_url}/k8s/namespaces/{namespace}/deployments/{deployment_name}/scale"
                        response = await client.patch(
                            api_url, json=payload, headers=headers
                        )

            response.raise_for_status()
            return response.json()

    async def restart_user_app(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        deployment_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restart a user application deployment."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        sanitized_app = sanitize_namespace(app_name)
        namespace = f"client-1-{sanitized_user}-{sanitized_env}-{sanitized_app}"

        # Use provided deployment_name or auto-detect
        if not deployment_name:
            deployment_name = sanitized_app

        api_url = f"{base_url}/k8s/namespaces/{namespace}/deployments/{deployment_name}/restart"
        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def update_user_app_image(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        image: str,
        deployment_name: Optional[str] = None,
        container: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update the container image of a user application deployment."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        sanitized_app = sanitize_namespace(app_name)
        namespace = f"client-1-{sanitized_user}-{sanitized_env}-{sanitized_app}"

        # Use provided deployment_name or auto-detect
        if not deployment_name:
            deployment_name = sanitized_app

        api_url = f"{base_url}/k8s/namespaces/{namespace}/deployments/{deployment_name}/rollout/update"
        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"image": image}
        if container:
            payload["container"] = container

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(api_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_user_app_status(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        deployment_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get the rollout status of a user application deployment."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        sanitized_app = sanitize_namespace(app_name)
        namespace = f"client-1-{sanitized_user}-{sanitized_env}-{sanitized_app}"

        # Use provided deployment_name or auto-detect
        if not deployment_name:
            deployment_name = sanitized_app

        api_url = f"{base_url}/k8s/namespaces/{namespace}/deployments/{deployment_name}/rollout/status"
        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_user_app_metrics(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Get metrics for a user application."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        sanitized_app = sanitize_namespace(app_name)
        namespace = f"client-1-{sanitized_user}-{sanitized_env}-{sanitized_app}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}/metrics"
        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_user_app_pods(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Get pods for a user application."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        sanitized_app = sanitize_namespace(app_name)
        namespace = f"client-1-{sanitized_user}-{sanitized_env}-{sanitized_app}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}/pods"
        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def delete_user_app(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Delete a user application namespace."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        sanitized_app = sanitize_namespace(app_name)
        namespace = f"client-1-{sanitized_user}-{sanitized_env}-{sanitized_app}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}"
        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.delete(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
