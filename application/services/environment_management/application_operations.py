"""Application-level CRUD and query operations (general and user apps).

This module contains functions for:
- User app scaling, restarting, updating
- User app deletion
- User app listing and querying
- User app metrics and pods
- User app status checking
"""

import httpx
import logging
import os
from typing import Any, Dict, List, Optional

from application.services.cloud_manager_service import get_cloud_manager_service
from .namespace_operations import construct_user_app_namespace, normalize_for_namespace

logger = logging.getLogger(__name__)


async def scale_user_app(
    user_id: str,
    env_name: str,
    app_name: str,
    deployment_name: str,
    replicas: int,
) -> Dict[str, Any]:
    """Scale a user application deployment.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name
        deployment_name: Deployment name
        replicas: Target number of replicas

    Returns:
        Dictionary with scaling result from API

    Raises:
        httpx.HTTPStatusError: If the API call fails
    """
    namespace = construct_user_app_namespace(user_id, env_name, app_name)
    logger.info(f"Scaling user app: namespace={namespace}, deployment={deployment_name}, replicas={replicas}")

    client = await get_cloud_manager_service()
    payload = {"replicas": replicas}
    response = await client.patch(
        f"/k8s/namespaces/{namespace}/deployments/{deployment_name}/scale",
        json=payload
    )

    logger.info(f"Scaled {deployment_name} in {namespace} to {replicas} replicas")
    return response.json()


async def restart_user_app(
    user_id: str,
    env_name: str,
    app_name: str,
    deployment_name: str,
) -> Dict[str, Any]:
    """Restart a user application deployment.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name
        deployment_name: Deployment name

    Returns:
        Dictionary with restart result from API

    Raises:
        httpx.HTTPStatusError: If the API call fails
    """
    namespace = construct_user_app_namespace(user_id, env_name, app_name)
    logger.info(f"Restarting user app: namespace={namespace}, deployment={deployment_name}")

    client = await get_cloud_manager_service()
    response = await client.post(
        f"/k8s/namespaces/{namespace}/deployments/{deployment_name}/restart"
    )

    logger.info(f"Restarted {deployment_name} in {namespace}")
    return response.json()


async def update_user_app_image(
    user_id: str,
    env_name: str,
    app_name: str,
    deployment_name: str,
    image: str,
    container: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a user application's container image.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name
        deployment_name: Deployment name
        image: New container image (e.g., "myapp:v2.0")
        container: Optional container name (if deployment has multiple containers)

    Returns:
        Dictionary with update result from API

    Raises:
        httpx.HTTPStatusError: If the API call fails
    """
    namespace = construct_user_app_namespace(user_id, env_name, app_name)
    logger.info(f"Updating user app image: namespace={namespace}, deployment={deployment_name}, image={image}")

    client = await get_cloud_manager_service()
    payload = {"image": image}
    if container:
        payload["container"] = container

    response = await client.patch(
        f"/k8s/namespaces/{namespace}/deployments/{deployment_name}/rollout/update",
        json=payload
    )

    logger.info(f"Updated {deployment_name} image to {image}")
    return response.json()


async def delete_user_app(
    user_id: str,
    env_name: str,
    app_name: str,
) -> Dict[str, Any]:
    """Delete a user application namespace.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name

    Returns:
        Dictionary with deletion result from API

    Raises:
        httpx.HTTPStatusError: If the API call fails
    """
    namespace = construct_user_app_namespace(user_id, env_name, app_name)
    logger.info(f"Deleting user app: namespace={namespace}")

    client = await get_cloud_manager_service()
    response = await client.delete(f"/k8s/namespaces/{namespace}")

    logger.info(f"Deleted namespace {namespace}")
    return response.json()


async def list_user_apps(
    user_id: str,
    env_name: str,
    auth_token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all user applications in an environment.

    Args:
        user_id: User ID
        env_name: Environment name
        auth_token: Optional Auth0 token for checking app status

    Returns:
        List of user application dictionaries
    """
    client = await get_cloud_manager_service()
    response = await client.get("/k8s/namespaces")
    data = response.json()
    all_namespaces = data.get("namespaces", [])

    # Filter for user app namespaces (format: client-1-{user}-{env}-{app})
    normalized_user = normalize_for_namespace(user_id)
    normalized_env = normalize_for_namespace(env_name)
    app_namespace_prefix = f"client-1-{normalized_user}-{normalized_env}-"

    user_apps = []
    for ns in all_namespaces:
        ns_name = ns.get("name", "")
        if ns_name.startswith(app_namespace_prefix):
            # Extract app name
            app_name = ns_name.replace(app_namespace_prefix, "")

            # Check app status if auth token provided
            app_status = "Unknown"
            if auth_token:
                app_status = await check_user_app_status(
                    user_id=user_id,
                    env_name=env_name,
                    app_name=app_name,
                    auth_token=auth_token,
                )

            user_apps.append({
                "name": app_name,
                "namespace": ns_name,
                "status": app_status,
                "created": ns.get("creationTimestamp", ""),
            })

    logger.info(f"Found {len(user_apps)} user apps in {env_name}")
    return user_apps


async def get_user_app_details(
    user_id: str,
    env_name: str,
    app_name: str,
) -> Dict[str, Any]:
    """Get detailed information about a user application.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name

    Returns:
        Dictionary with user application namespace details
    """
    namespace = construct_user_app_namespace(user_id, env_name, app_name)
    client = await get_cloud_manager_service()
    response = await client.get(f"/k8s/namespaces/{namespace}")

    logger.info(f"Retrieved details for user app {app_name}")
    return response.json()


async def get_user_app_status(
    user_id: str,
    env_name: str,
    app_name: str,
    deployment_name: str,
) -> Dict[str, Any]:
    """Get status of a user application deployment.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name
        deployment_name: Deployment name

    Returns:
        Dictionary with deployment status
    """
    namespace = construct_user_app_namespace(user_id, env_name, app_name)
    client = await get_cloud_manager_service()
    response = await client.get(f"/k8s/namespaces/{namespace}/deployments/{deployment_name}/status")

    return response.json()


async def get_user_app_metrics(
    user_id: str,
    env_name: str,
    app_name: str,
) -> Dict[str, Any]:
    """Get metrics for a user application.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name

    Returns:
        Dictionary with application metrics
    """
    namespace = construct_user_app_namespace(user_id, env_name, app_name)
    client = await get_cloud_manager_service()
    response = await client.get(f"/k8s/namespaces/{namespace}/metrics")

    return response.json()


async def get_user_app_pods(
    user_id: str,
    env_name: str,
    app_name: str,
) -> Dict[str, Any]:
    """Get pods for a user application.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name

    Returns:
        Dictionary with pod information
    """
    namespace = construct_user_app_namespace(user_id, env_name, app_name)
    client = await get_cloud_manager_service()
    response = await client.get(f"/k8s/namespaces/{namespace}/pods")

    return response.json()


async def check_user_app_status(
    user_id: str,
    env_name: str,
    app_name: str,
    auth_token: str,
) -> str:
    """Check if a user application is accessible.

    Makes a request to the app URL with the Auth0 token to check accessibility.

    Args:
        user_id: User ID
        env_name: Environment name
        app_name: Application name
        auth_token: Auth0 token for authentication

    Returns:
        "Active" if accessible, "Inactive" otherwise
    """
    try:
        # Construct app URL
        namespace = construct_user_app_namespace(user_id, env_name, app_name)
        client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
        app_url = f"https://{namespace}.{client_host}/api"

        # Make request with Auth0 token
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(app_url, headers=headers, follow_redirects=False)

            if response.status_code == 200:
                return "Active"
            else:
                logger.debug(f"App {app_name} returned status {response.status_code}")
                return "Inactive"

    except Exception as e:
        logger.debug(f"Failed to check app status for {app_name}: {str(e)}")
        return "Inactive"
