"""Deployment service for orchestrating environment and application deployments."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Optional

from application.services.cloud_manager_service import get_cloud_manager_service

logger = logging.getLogger(__name__)


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""

    build_id: str
    namespace: str
    task_id: Optional[str] = None
    env_url: Optional[str] = None
    keyspace: Optional[str] = None


class DeploymentService:
    """Service for orchestrating deployment operations.

    This service encapsulates the business logic for deploying environments and applications,
    separating it from the tool layer and Cloud Manager API interactions.
    """

    def __init__(self, client_host: Optional[str] = None):
        """Initialize the deployment service.

        Args:
            client_host: Client host for constructing environment URLs (defaults to env var or cyoda.cloud)
        """
        import os

        self.client_host = client_host or os.getenv("CLIENT_HOST", "cyoda.cloud")

    @staticmethod
    def _normalize_for_keyspace(name: str) -> str:
        """Normalize a name for use in Cassandra keyspace (alphanumeric + underscores only)."""
        return re.sub(r"[^a-z0-9_]", "_", name.lower())

    @staticmethod
    def _normalize_for_namespace(name: str) -> str:
        """Normalize a name for use in Kubernetes namespace (alphanumeric + hyphens only)."""
        return re.sub(r"[^a-z0-9-]", "-", name.lower())

    async def deploy_cyoda_environment(
        self,
        user_id: str,
        conversation_id: str,
        env_name: str,
        build_id: Optional[str] = None,
    ) -> DeploymentResult:
        """Deploy a Cyoda environment with full orchestration.

        This method:
        1. Constructs namespace and keyspace
        2. Calls Cloud Manager API to deploy
        3. Returns deployment result

        Args:
            user_id: User ID requesting the deployment
            conversation_id: Conversation ID for tracking
            env_name: Environment name (will be truncated to 10 chars)
            build_id: Optional build ID to associate with deployment

        Returns:
            DeploymentResult with build_id, namespace, and env_url

        Raises:
            httpx.HTTPStatusError: If the deployment API call fails
        """
        # Truncate env_name to 10 characters for namespace constraints
        env_name = env_name[:10]

        # Construct namespace and keyspace using standard patterns
        namespace = f"client-{self._normalize_for_namespace(user_id)}-{self._normalize_for_namespace(env_name)}"
        keyspace = f"c_{self._normalize_for_keyspace(user_id)}_{self._normalize_for_keyspace(env_name)}"

        logger.info(
            f"Deploying Cyoda environment: user={user_id}, env={env_name}, namespace={namespace}"
        )

        # Prepare deployment payload
        payload = {
            "user_name": user_id,
            "chat_id": conversation_id,
            "user_defined_namespace": namespace,
            "user_defined_keyspace": keyspace,
        }

        # Add optional build_id if provided
        if build_id:
            payload["build_id"] = build_id
            logger.info(f"Including build_id in deployment: {build_id}")

        # Call Cloud Manager API
        cloud_manager = await get_cloud_manager_service()
        response = await cloud_manager.post("/deploy/cyoda-env", json=payload)
        data = response.json()

        # Extract deployment information
        deployment_build_id = data.get("build_id")
        deployment_namespace = data.get("build_namespace")

        if not deployment_build_id or not deployment_namespace:
            raise ValueError(
                "Deployment succeeded but missing build information from API response"
            )

        logger.info(
            f"Deployment started: build_id={deployment_build_id}, namespace={deployment_namespace}"
        )

        # Construct environment URL
        env_url = f"https://{deployment_namespace}.{self.client_host}"

        return DeploymentResult(
            build_id=deployment_build_id,
            namespace=deployment_namespace,
            env_url=env_url,
            keyspace=keyspace,
        )

    def _build_app_namespaces(
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
        env_name = env_name[:10]
        app_name = app_name[:10]

        cyoda_ns = f"client-{self._normalize_for_namespace(user_id)}-{self._normalize_for_namespace(env_name)}"
        user_norm = self._normalize_for_namespace(user_id)
        env_norm = self._normalize_for_namespace(env_name)
        app_norm = self._normalize_for_namespace(app_name)
        app_ns = f"client-1-{user_norm}-{env_norm}-{app_norm}"

        return cyoda_ns, app_ns

    def _build_app_deployment_payload(
        self,
        branch_name: str,
        conversation_id: str,
        cyoda_client_id: str,
        cyoda_client_secret: str,
        is_public: bool,
        repository_url: str,
        user_id: str,
        app_namespace: str,
        cyoda_namespace: str,
        installation_id: Optional[str] = None,
    ) -> dict:
        """Build app deployment payload.

        Args:
            branch_name: Git branch
            conversation_id: Conversation ID
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
            "chat_id": conversation_id,
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
            import os

            env_installation_id = os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID")
            if env_installation_id:
                payload["installation_id"] = env_installation_id

        return payload

    async def deploy_user_application(
        self,
        user_id: str,
        conversation_id: str,
        env_name: str,
        app_name: str,
        repository_url: str,
        branch_name: str,
        cyoda_client_id: str,
        cyoda_client_secret: str,
        is_public: bool = True,
        installation_id: Optional[str] = None,
    ) -> DeploymentResult:
        """Deploy a user application with full orchestration.

        This method:
        1. Constructs app_namespace and cyoda_namespace
        2. Calls Cloud Manager API to deploy application
        3. Returns deployment result

        Args:
            user_id: User ID requesting the deployment
            conversation_id: Conversation ID for tracking
            env_name: Environment name (will be truncated to 10 chars)
            app_name: Application name (will be truncated to 10 chars)
            repository_url: Git repository URL
            branch_name: Git branch to deploy
            cyoda_client_id: Cyoda OAuth client ID
            cyoda_client_secret: Cyoda OAuth client secret
            is_public: Whether the repository is public (default: True)
            installation_id: Optional GitHub installation ID (can be str or int)

        Returns:
            DeploymentResult with build_id and namespace

        Raises:
            httpx.HTTPStatusError: If the deployment API call fails
        """
        cyoda_namespace, app_namespace = self._build_app_namespaces(
            user_id, env_name, app_name
        )

        logger.info(
            f"Deploying user application: user={user_id}, env={env_name}, "
            f"app={app_name}, app_namespace={app_namespace}"
        )

        payload = self._build_app_deployment_payload(
            branch_name=branch_name,
            conversation_id=conversation_id,
            cyoda_client_id=cyoda_client_id,
            cyoda_client_secret=cyoda_client_secret,
            is_public=is_public,
            repository_url=repository_url,
            user_id=user_id,
            app_namespace=app_namespace,
            cyoda_namespace=cyoda_namespace,
            installation_id=installation_id,
        )

        cloud_manager = await get_cloud_manager_service()
        response = await cloud_manager.post("/deploy/user-app", json=payload)
        data = response.json()

        deployment_build_id = data.get("build_id")
        deployment_namespace = data.get("build_namespace") or data.get("namespace")

        if not deployment_build_id:
            raise ValueError(
                "Deployment succeeded but missing build_id from API response"
            )

        logger.info(
            f"User app deployment started: build_id={deployment_build_id}, "
            f"namespace={deployment_namespace}"
        )

        return DeploymentResult(
            build_id=deployment_build_id,
            namespace=deployment_namespace or app_namespace,
        )


def get_deployment_service() -> DeploymentService:
    """Get a DeploymentService instance.

    Returns:
        DeploymentService instance
    """
    return DeploymentService()
