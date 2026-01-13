"""Environment-level CRUD and query operations.

This module contains functions for:
- Environment scaling, restarting, updating
- Environment deletion
- Environment listing and querying
- Environment metrics and pods
"""

import logging
from typing import Any, Dict, List, Optional

# Import from parent module for test mocking compatibility
# Tests patch at application.services.environment_management_service.get_cloud_manager_service
from ..cloud_manager_service import get_cloud_manager_service
from .namespace_operations import construct_namespace, normalize_for_namespace

logger = logging.getLogger(__name__)


async def scale_application(
    user_id: str,
    env_name: str,
    app_name: str,
    replicas: int,
) -> Dict[str, Any]:
    """Scale an application deployment to specified number of replicas.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name
        replicas: Target number of replicas

    Returns:
        Dictionary with scaling result from API

    Raises:
        httpx.HTTPStatusError: If the API call fails
    """
    namespace = construct_namespace(user_id, env_name)
    logger.info(
        f"Scaling application: namespace={namespace}, app={app_name}, replicas={replicas}"
    )

    client = await get_cloud_manager_service()
    payload = {"replicas": replicas}
    response = await client.patch(
        f"/k8s/namespaces/{namespace}/deployments/{app_name}/scale", json=payload
    )

    logger.info(f"Scaled {app_name} in {namespace} to {replicas} replicas")
    return response.json()


async def restart_application(
    user_id: str,
    env_name: str,
    app_name: str,
) -> Dict[str, Any]:
    """Restart an application deployment by triggering a rollout restart.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name

    Returns:
        Dictionary with restart result from API

    Raises:
        httpx.HTTPStatusError: If the API call fails
    """
    namespace = construct_namespace(user_id, env_name)
    logger.info(f"Restarting application: namespace={namespace}, app={app_name}")

    client = await get_cloud_manager_service()
    response = await client.post(
        f"/k8s/namespaces/{namespace}/deployments/{app_name}/restart"
    )

    logger.info(f"Restarted {app_name} in {namespace}")
    return response.json()


async def update_application_image(
    user_id: str,
    env_name: str,
    app_name: str,
    image: str,
    container: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an application's container image.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name
        image: New container image (e.g., "myapp:v2.0")
        container: Optional container name (if deployment has multiple containers)

    Returns:
        Dictionary with update result from API

    Raises:
        httpx.HTTPStatusError: If the API call fails
    """
    namespace = construct_namespace(user_id, env_name)
    logger.info(
        f"Updating application image: namespace={namespace}, app={app_name}, image={image}"
    )

    client = await get_cloud_manager_service()
    payload = {"image": image}
    if container:
        payload["container"] = container

    response = await client.patch(
        f"/k8s/namespaces/{namespace}/deployments/{app_name}/rollout/update",
        json=payload,
    )

    logger.info(f"Updated {app_name} image to {image}")
    return response.json()


async def delete_environment(
    user_id: str,
    env_name: str,
) -> Dict[str, Any]:
    """Delete a Cyoda environment namespace.

    Args:
        user_id: User ID
        env_name: Environment name

    Returns:
        Dictionary with deletion result from API

    Raises:
        httpx.HTTPStatusError: If the API call fails
    """
    namespace = construct_namespace(user_id, env_name)
    logger.info(f"Deleting environment: namespace={namespace}")

    client = await get_cloud_manager_service()
    response = await client.delete(f"/k8s/namespaces/{namespace}")

    logger.info(f"Deleted namespace {namespace}")
    return response.json()


async def list_environments(
    user_id: str,
) -> List[Dict[str, Any]]:
    """List all Cyoda environments for a user.

    Args:
        user_id: User ID

    Returns:
        List of environment dictionaries with name, namespace, and status
    """
    client = await get_cloud_manager_service()
    response = await client.get("/k8s/namespaces")
    data = response.json()
    all_namespaces = data.get("namespaces", [])

    # Filter namespaces for this user
    normalized_user = normalize_for_namespace(user_id)
    user_namespace_prefix = f"client-{normalized_user}-"
    user_environments = []

    for ns in all_namespaces:
        ns_name = ns.get("name", "")
        if ns_name.startswith(user_namespace_prefix):
            # Extract environment name
            env_name = ns_name.replace(user_namespace_prefix, "")
            # Skip app namespaces
            if "-app-" not in env_name and not ns_name.startswith("client-1-"):
                user_environments.append(
                    {
                        "name": env_name,
                        "namespace": ns_name,
                        "status": ns.get("status", "Unknown"),
                        "created": ns.get("creationTimestamp", ""),
                    }
                )

    logger.info(f"Found {len(user_environments)} environments for user {user_id}")
    return user_environments


async def describe_environment(
    user_id: str,
    env_name: str,
) -> Dict[str, Any]:
    """Get detailed information about a Cyoda environment.

    Args:
        user_id: User ID
        env_name: Environment name

    Returns:
        Dictionary with environment details including deployments, services, etc.
    """
    namespace = construct_namespace(user_id, env_name)
    client = await get_cloud_manager_service()
    response = await client.get(f"/k8s/namespaces/{namespace}")

    logger.info(f"Retrieved details for environment {env_name}")
    return response.json()


async def get_application_details(
    user_id: str,
    env_name: str,
    app_name: str,
) -> Dict[str, Any]:
    """Get detailed information about an application in a Cyoda environment.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name

    Returns:
        Dictionary with application deployment details
    """
    namespace = construct_namespace(user_id, env_name)
    client = await get_cloud_manager_service()
    response = await client.get(f"/k8s/namespaces/{namespace}/deployments/{app_name}")

    logger.info(f"Retrieved details for application {app_name} in {env_name}")
    return response.json()


async def get_application_status(
    user_id: str,
    env_name: str,
    app_name: str,
) -> Dict[str, Any]:
    """Get status of an application in a Cyoda environment.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name

    Returns:
        Dictionary with application status
    """
    namespace = construct_namespace(user_id, env_name)
    client = await get_cloud_manager_service()
    response = await client.get(
        f"/k8s/namespaces/{namespace}/deployments/{app_name}/status"
    )

    return response.json()


async def get_environment_metrics(
    user_id: str,
    env_name: str,
) -> Dict[str, Any]:
    """Get metrics for a Cyoda environment.

    Args:
        user_id: User ID
        env_name: Environment name

    Returns:
        Dictionary with environment metrics
    """
    namespace = construct_namespace(user_id, env_name)
    client = await get_cloud_manager_service()
    response = await client.get(f"/k8s/namespaces/{namespace}/metrics")

    return response.json()


async def get_environment_pods(
    user_id: str,
    env_name: str,
) -> Dict[str, Any]:
    """Get pods in a Cyoda environment.

    Args:
        user_id: User ID
        env_name: Environment name

    Returns:
        Dictionary with pod information
    """
    namespace = construct_namespace(user_id, env_name)
    client = await get_cloud_manager_service()
    response = await client.get(f"/k8s/namespaces/{namespace}/pods")

    return response.json()


# Re-export for test mocking compatibility
__all__ = [
    "scale_application",
    "restart_application",
    "update_application_image",
    "delete_environment",
    "list_environments",
    "describe_environment",
    "get_application_details",
    "get_application_status",
    "get_environment_metrics",
    "get_environment_pods",
    "get_cloud_manager_service",  # For test mocking
]
