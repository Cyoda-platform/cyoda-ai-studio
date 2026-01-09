"""Service for Kubernetes resource operations."""

import logging
from typing import Any, Dict, List, Optional

from application.services.environment.auth import CloudManagerAuthService

from .deployment_ops import DeploymentOperations
from .namespace_ops import NamespaceOperations
from .user_app_ops import UserAppOperations

logger = logging.getLogger(__name__)


class EnvironmentResourceService:
    """Handles Kubernetes resource operations via Cloud Manager."""

    def __init__(self, auth_service: CloudManagerAuthService):
        self.auth_service = auth_service
        self.cloud_manager_host = auth_service.cloud_manager_host
        self.protocol = auth_service.protocol

        # Initialize operation handlers
        self.namespace_ops = NamespaceOperations(auth_service)
        self.deployment_ops = DeploymentOperations(auth_service)
        self.user_app_ops = UserAppOperations(auth_service)

    # Delegate to namespace operations
    async def list_environments(self, user_id: str) -> List[Dict[str, Any]]:
        """List environments for a user."""
        return await self.namespace_ops.list_environments(user_id)

    async def describe_environment(self, user_id: str, env_name: str) -> Dict[str, Any]:
        """Get deployments in a user's environment namespace."""
        return await self.namespace_ops.describe_environment(user_id, env_name)

    async def get_environment_metrics(
        self, user_id: str, env_name: str
    ) -> Dict[str, Any]:
        """Get metrics for an environment."""
        return await self.namespace_ops.get_environment_metrics(user_id, env_name)

    async def get_environment_pods(self, user_id: str, env_name: str) -> Dict[str, Any]:
        """Get pods in an environment."""
        return await self.namespace_ops.get_environment_pods(user_id, env_name)

    async def delete_environment(self, user_id: str, env_name: str) -> Dict[str, Any]:
        """Delete an environment."""
        return await self.namespace_ops.delete_environment(user_id, env_name)

    # Delegate to deployment operations
    async def get_application_details(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Get details for a specific application deployment."""
        return await self.deployment_ops.get_application_details(
            user_id, env_name, app_name
        )

    async def scale_application(
        self, user_id: str, env_name: str, app_name: str, replicas: int
    ) -> Dict[str, Any]:
        """Scale an application deployment."""
        return await self.deployment_ops.scale_application(
            user_id, env_name, app_name, replicas
        )

    async def restart_application(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Restart an application deployment."""
        return await self.deployment_ops.restart_application(
            user_id, env_name, app_name
        )

    async def update_application_image(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        image: str,
        container: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update container image for an application."""
        return await self.deployment_ops.update_application_image(
            user_id, env_name, app_name, image, container
        )

    async def get_application_status_rollout(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Get rollout status of an application."""
        return await self.deployment_ops.get_application_status_rollout(
            user_id, env_name, app_name
        )

    # Delegate to user app operations
    async def get_user_app_deployments(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Get deployments for a user application."""
        return await self.user_app_ops.get_user_app_deployments(
            user_id, env_name, app_name
        )

    async def scale_user_app(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        replicas: int,
        deployment_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Scale a user application deployment."""
        return await self.user_app_ops.scale_user_app(
            user_id, env_name, app_name, replicas, deployment_name
        )

    async def restart_user_app(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        deployment_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restart a user application deployment."""
        return await self.user_app_ops.restart_user_app(
            user_id, env_name, app_name, deployment_name
        )

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
        return await self.user_app_ops.update_user_app_image(
            user_id, env_name, app_name, image, deployment_name, container
        )

    async def get_user_app_status(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        deployment_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get the rollout status of a user application deployment."""
        return await self.user_app_ops.get_user_app_status(
            user_id, env_name, app_name, deployment_name
        )

    async def get_user_app_metrics(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Get metrics for a user application."""
        return await self.user_app_ops.get_user_app_metrics(user_id, env_name, app_name)

    async def get_user_app_pods(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Get pods for a user application."""
        return await self.user_app_ops.get_user_app_pods(user_id, env_name, app_name)

    async def delete_user_app(
        self, user_id: str, env_name: str, app_name: str
    ) -> Dict[str, Any]:
        """Delete a user application namespace."""
        return await self.user_app_ops.delete_user_app(user_id, env_name, app_name)
