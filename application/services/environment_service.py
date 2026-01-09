"""Service for interacting with the Cloud Manager and Environment operations."""

import logging
import os
from typing import Any, Dict, List, Optional

from application.services.environment.auth import CloudManagerAuthService
from application.services.environment.deployment import EnvironmentDeploymentService
from application.services.environment.resources import EnvironmentResourceService
from application.services.environment.utils import sanitize_keyspace, sanitize_namespace
from common.exception.exceptions import InvalidTokenException
from common.utils.utils import send_get_request

logger = logging.getLogger(__name__)


class EnvironmentService:
    """Facade service for managing Cyoda environments and user applications via Cloud Manager."""

    def __init__(self):
        """Initialize the Environment Service."""
        self.auth_service = CloudManagerAuthService()
        self.deployment_service = EnvironmentDeploymentService(self.auth_service)
        self.resource_service = EnvironmentResourceService(self.auth_service)
        self.client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")

    async def _get_auth_token(self) -> str:
        """Get authentication token (delegated)."""
        return await self.auth_service.get_token()

    def _get_namespace(self, name: str) -> str:
        """Sanitize name for namespace usage (delegated)."""
        return sanitize_namespace(name)

    def _get_keyspace(self, name: str) -> str:
        """Sanitize name for keyspace usage (delegated)."""
        return sanitize_keyspace(name)

    async def check_app_status(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        auth_token: Optional[str] = None,
    ) -> str:
        """Check if an application is accessible."""
        # This logic is specific to client access, so it remains here or in a client-specific service.
        # It's checking access via the public URL, not via Cloud Manager API.
        try:
            sanitized_user = sanitize_namespace(user_id)
            sanitized_env = sanitize_namespace(env_name)
            sanitized_app = sanitize_namespace(app_name)

            namespace = f"client-1-{sanitized_user}-{sanitized_env}-{sanitized_app}"
            app_url = f"https://{namespace}.{self.client_host}/api"

            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    app_url, headers=headers, follow_redirects=False
                )
                if response.status_code == 200:
                    return "Active"
                else:
                    logger.debug(
                        f"App {app_name} returned status {response.status_code}"
                    )
                    return "Inactive"
        except Exception as e:
            logger.debug(f"Failed to check app status for {app_name}: {str(e)}")
            return "Inactive"

    async def check_environment_exists(
        self, user_id: str, env_name: str
    ) -> Dict[str, Any]:
        """Check if a Cyoda environment exists for the user."""
        if not env_name:
            raise ValueError("env_name parameter is required")

        sanitized_user = sanitize_namespace(user_id)
        sanitized_env = sanitize_namespace(env_name)

        namespace = f"client-{sanitized_user}-{sanitized_env}"
        url = f"https://{namespace}.{self.client_host}"

        try:
            await send_get_request(api_url=url, path="api/v1", token="guest_token")
            return {
                "exists": False,
                "url": url,
                "message": f"Environment status unclear for {url}",
                "status": "unknown",
            }
        except InvalidTokenException:
            return {
                "exists": True,
                "url": url,
                "message": (
                    f"Your Cyoda environment is deployed and accessible at {url}"
                ),
                "status": "deployed",
            }
        except Exception as e:
            logger.info(f"Environment not deployed for user {user_id}: {e}")
            return {
                "exists": False,
                "url": url,
                "message": f"No Cyoda environment found at {url}",
                "status": "not_deployed",
            }

    # Delegation methods

    async def deploy_environment(self, *args, **kwargs) -> Dict[str, str]:
        return await self.deployment_service.deploy_environment(*args, **kwargs)

    async def deploy_user_application(self, *args, **kwargs) -> Dict[str, str]:
        return await self.deployment_service.deploy_user_application(*args, **kwargs)

    async def get_deployment_status(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.deployment_service.get_deployment_status(*args, **kwargs)

    async def get_build_logs(self, *args, **kwargs) -> str:
        return await self.deployment_service.get_build_logs(*args, **kwargs)

    async def list_environments(self, *args, **kwargs) -> List[Dict[str, Any]]:
        return await self.resource_service.list_environments(*args, **kwargs)

    async def describe_environment(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.describe_environment(*args, **kwargs)

    async def get_application_details(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.get_application_details(*args, **kwargs)

    async def scale_application(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.scale_application(*args, **kwargs)

    async def restart_application(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.restart_application(*args, **kwargs)

    async def update_application_image(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.update_application_image(*args, **kwargs)

    async def get_application_status_rollout(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.get_application_status_rollout(
            *args, **kwargs
        )

    async def get_environment_metrics(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.get_environment_metrics(*args, **kwargs)

    async def get_environment_pods(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.get_environment_pods(*args, **kwargs)

    async def delete_environment(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.delete_environment(*args, **kwargs)

    async def get_user_app_deployments(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.get_user_app_deployments(*args, **kwargs)

    async def scale_user_app(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.scale_user_app(*args, **kwargs)

    async def restart_user_app(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.restart_user_app(*args, **kwargs)

    async def update_user_app_image(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.update_user_app_image(*args, **kwargs)

    async def get_user_app_status(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.get_user_app_status(*args, **kwargs)

    async def get_user_app_metrics(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.get_user_app_metrics(*args, **kwargs)

    async def get_user_app_pods(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.get_user_app_pods(*args, **kwargs)

    async def delete_user_app(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.resource_service.delete_user_app(*args, **kwargs)

    async def list_user_apps(
        self, user_id: str, env_name: str, auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List user applications."""
        # This combines listing namespaces (ResourceService) with status checking (EnvironmentService/Client check)
        # So it stays here as coordination logic.

        # We need to access resource service for list environments, but actually we need list namespaces (raw)
        # But resource_service.list_environments filters for "client-{user}-{env}".
        # We need "client-1-{user}-{env}-{app}".
        # Let's add list_namespaces or similar to ResourceService?
        # Actually `list_environments` in `ResourceService` gets ALL namespaces and filters.
        # It's better to duplicate the list logic or expose a raw list method?
        # Let's expose list logic or adapt `list_user_apps` to use the same logic but different filter.

        # For now, implementing logic here using auth token from service.
        token = await self.auth_service.get_token()

        # We need base_url from auth service or resource service
        base_url = f"{self.resource_service.protocol}://{self.resource_service.cloud_manager_host}"
        api_url = f"{base_url}/k8s/namespaces"

        import httpx

        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            all_namespaces = data.get("namespaces", [])

            sanitized_user = sanitize_namespace(user_id)
            sanitized_env = sanitize_namespace(env_name)
            app_namespace_prefix = f"client-1-{sanitized_user}-{sanitized_env}-"

            user_apps = []
            for ns in all_namespaces:
                ns_name = ns.get("name", "")
                if ns_name.startswith(app_namespace_prefix):
                    app_name = ns_name.replace(app_namespace_prefix, "")

                    app_status = await self.check_app_status(
                        user_id=user_id,
                        env_name=env_name,
                        app_name=app_name,
                        auth_token=auth_token,
                    )

                    user_apps.append(
                        {
                            "app_name": app_name,
                            "namespace": ns_name,
                            "status": app_status,
                            "created_at": ns.get("created_at"),
                        }
                    )

            return {
                "environment": env_name,
                "user_applications": user_apps,
                "count": len(user_apps),
            }
