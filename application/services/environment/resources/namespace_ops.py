"""Namespace-level operations for Kubernetes resources."""

import logging
from typing import Any, Dict, List

import httpx

from application.services.environment.auth import CloudManagerAuthService
from application.services.environment.utils import sanitize_namespace

logger = logging.getLogger(__name__)


class NamespaceOperations:
    """Operations on Kubernetes namespaces."""

    def __init__(self, auth_service: CloudManagerAuthService):
        self.auth_service = auth_service
        self.cloud_manager_host = auth_service.cloud_manager_host
        self.protocol = auth_service.protocol

    def _get_base_url(self) -> str:
        if not self.cloud_manager_host:
            raise Exception("CLOUD_MANAGER_HOST not configured")
        return f"{self.protocol}://{self.cloud_manager_host}"

    async def list_environments(self, user_id: str) -> List[Dict[str, Any]]:
        """List environments for a user."""
        base_url = self._get_base_url()
        api_url = f"{base_url}/k8s/namespaces"

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            all_namespaces = data.get("namespaces", [])
            sanitized_user = sanitize_namespace(user_id)
            user_namespace_prefix = f"client-{sanitized_user}-"

            user_environments = []
            for ns in all_namespaces:
                ns_name = ns.get("name", "")
                if ns_name.startswith(user_namespace_prefix):
                    env_name = ns_name.replace(user_namespace_prefix, "")
                    if "-app-" not in env_name:
                        user_environments.append(
                            {
                                "name": env_name,
                                "namespace": ns_name,
                                "status": ns.get("status", "Unknown"),
                                "created_at": ns.get("created_at"),
                            }
                        )
            return user_environments

    async def describe_environment(self, user_id: str, env_name: str) -> Dict[str, Any]:
        """Get deployments in a user's environment namespace."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        namespace = f"client-{sanitized_user}-{sanitized_env}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}/deployments"

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            return {
                "environment": env_name,
                "namespace": namespace,
                "applications": data.get("deployments", []),
                "count": len(data.get("deployments", [])),
            }

    async def get_environment_metrics(
        self, user_id: str, env_name: str
    ) -> Dict[str, Any]:
        """Get metrics for an environment."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        namespace = f"client-{sanitized_user}-{sanitized_env}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}/metrics"

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_environment_pods(self, user_id: str, env_name: str) -> Dict[str, Any]:
        """Get pods in an environment."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        namespace = f"client-{sanitized_user}-{sanitized_env}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}/pods"

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def delete_environment(self, user_id: str, env_name: str) -> Dict[str, Any]:
        """Delete an environment."""
        base_url = self._get_base_url()
        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)
        namespace = f"client-{sanitized_user}-{sanitized_env}"

        api_url = f"{base_url}/k8s/namespaces/{namespace}"

        token = await self.auth_service.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.delete(api_url, headers=headers)
            response.raise_for_status()
            return response.json()
