"""Environment management service for Cyoda environment operations.

This package is organized into focused modules:
- namespace_operations: Namespace normalization and construction
- environment_operations: Environment-level CRUD and query operations
- application_operations: Application-level CRUD and query operations (both general and user apps)

The main EnvironmentManagementService class is re-exported from this package for backward compatibility.
"""

from ..cloud_manager_service import get_cloud_manager_service
from .application_operations import (
    check_user_app_status,
    delete_user_app,
    get_user_app_details,
    get_user_app_metrics,
    get_user_app_pods,
    get_user_app_status,
    list_user_apps,
    restart_user_app,
    scale_user_app,
    update_user_app_image,
)
from .environment_operations import (
    delete_environment,
    describe_environment,
    get_application_details,
    get_application_status,
    get_environment_metrics,
    get_environment_pods,
    list_environments,
    restart_application,
    scale_application,
    update_application_image,
)
from .namespace_operations import (
    construct_namespace,
    construct_user_app_namespace,
    normalize_for_namespace,
)


class EnvironmentManagementService:
    """Service for managing Cyoda environments and applications.

    This service encapsulates business logic for environment management operations
    like scaling, restarting, updating images, and deleting namespaces.
    """

    # Static methods for namespace operations
    @staticmethod
    def _normalize_for_namespace(name: str) -> str:
        """Normalize a name for use in Kubernetes namespace (alphanumeric + hyphens only)."""
        return normalize_for_namespace(name)

    @staticmethod
    def _construct_namespace(user_id: str, env_name: str) -> str:
        """Construct namespace for Cyoda environment."""
        return construct_namespace(user_id, env_name)

    @staticmethod
    def _construct_user_app_namespace(
        user_id: str, env_name: str, app_name: str
    ) -> str:
        """Construct namespace for user application."""
        return construct_user_app_namespace(user_id, env_name, app_name)

    # Environment operations
    async def scale_application(
        self, user_id: str, env_name: str, app_name: str, replicas: int
    ):
        """Scale an application deployment to specified number of replicas."""
        return await scale_application(user_id, env_name, app_name, replicas)

    async def restart_application(self, user_id: str, env_name: str, app_name: str):
        """Restart an application deployment by triggering a rollout restart."""
        return await restart_application(user_id, env_name, app_name)

    async def update_application_image(
        self, user_id: str, env_name: str, app_name: str, image: str, container=None
    ):
        """Update an application's container image."""
        return await update_application_image(
            user_id, env_name, app_name, image, container
        )

    async def delete_environment(self, user_id: str, env_name: str):
        """Delete a Cyoda environment namespace."""
        return await delete_environment(user_id, env_name)

    async def list_environments(self, user_id: str):
        """List all Cyoda environments for a user."""
        return await list_environments(user_id)

    async def describe_environment(self, user_id: str, env_name: str):
        """Get detailed information about a Cyoda environment."""
        return await describe_environment(user_id, env_name)

    async def get_application_details(self, user_id: str, env_name: str, app_name: str):
        """Get detailed information about an application in a Cyoda environment."""
        return await get_application_details(user_id, env_name, app_name)

    async def get_application_status(self, user_id: str, env_name: str, app_name: str):
        """Get status of an application in a Cyoda environment."""
        return await get_application_status(user_id, env_name, app_name)

    async def get_environment_metrics(self, user_id: str, env_name: str):
        """Get metrics for a Cyoda environment."""
        return await get_environment_metrics(user_id, env_name)

    async def get_environment_pods(self, user_id: str, env_name: str):
        """Get pods in a Cyoda environment."""
        return await get_environment_pods(user_id, env_name)

    # User application operations
    async def scale_user_app(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        deployment_name: str,
        replicas: int,
    ):
        """Scale a user application deployment."""
        return await scale_user_app(
            user_id, env_name, app_name, deployment_name, replicas
        )

    async def restart_user_app(
        self, user_id: str, env_name: str, app_name: str, deployment_name: str
    ):
        """Restart a user application deployment."""
        return await restart_user_app(user_id, env_name, app_name, deployment_name)

    async def update_user_app_image(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        deployment_name: str,
        image: str,
        container=None,
    ):
        """Update a user application's container image."""
        return await update_user_app_image(
            user_id, env_name, app_name, deployment_name, image, container
        )

    async def delete_user_app(self, user_id: str, env_name: str, app_name: str):
        """Delete a user application namespace."""
        return await delete_user_app(user_id, env_name, app_name)

    async def list_user_apps(self, user_id: str, env_name: str, auth_token=None):
        """List all user applications in an environment."""
        return await list_user_apps(user_id, env_name, auth_token)

    async def get_user_app_details(self, user_id: str, env_name: str, app_name: str):
        """Get detailed information about a user application."""
        return await get_user_app_details(user_id, env_name, app_name)

    async def get_user_app_status(
        self, user_id: str, env_name: str, app_name: str, deployment_name: str
    ):
        """Get status of a user application deployment."""
        return await get_user_app_status(user_id, env_name, app_name, deployment_name)

    async def get_user_app_metrics(self, user_id: str, env_name: str, app_name: str):
        """Get metrics for a user application."""
        return await get_user_app_metrics(user_id, env_name, app_name)

    async def get_user_app_pods(self, user_id: str, env_name: str, app_name: str):
        """Get pods for a user application."""
        return await get_user_app_pods(user_id, env_name, app_name)

    async def check_user_app_status(
        self, user_id: str, env_name: str, app_name: str, auth_token: str
    ):
        """Check if a user application is accessible."""
        return await check_user_app_status(user_id, env_name, app_name, auth_token)


def get_environment_management_service() -> EnvironmentManagementService:
    """Get an EnvironmentManagementService instance.

    Returns:
        EnvironmentManagementService instance
    """
    return EnvironmentManagementService()


__all__ = [
    "EnvironmentManagementService",
    "get_environment_management_service",
    "get_cloud_manager_service",
]
