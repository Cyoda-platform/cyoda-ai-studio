"""API key generation operations for Elasticsearch."""

import logging
from typing import Dict

import httpx

from application.routes.common.constants import (
    API_KEY_EXPIRY_DAYS,
    DEFAULT_HTTP_TIMEOUT_SECONDS,
)
from application.services.core.config_service import ConfigService

from .helpers import build_role_descriptors, create_basic_auth_header, encode_api_key

logger = logging.getLogger(__name__)


async def generate_api_key(config_service: ConfigService, org_id: str) -> Dict:
    """Generate Elasticsearch API key for organization.

    Args:
        config_service: Configuration service for external services
        org_id: Organization ID

    Returns:
        Dictionary with api_key, name, created, message, expires_in_days

    Raises:
        Exception: If API key generation fails

    Example:
        >>> result = await generate_api_key(config, "myorg")
        >>> api_key = result["api_key"]
    """
    elk_config = config_service.get_elk_config()
    api_key_name = f"logs-reader-{org_id}"
    role_descriptors = build_role_descriptors(org_id)
    auth_header = create_basic_auth_header(elk_config.user, elk_config.password)

    async with httpx.AsyncClient(timeout=DEFAULT_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"https://{elk_config.host}/_security/api_key",
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/json",
            },
            json={
                "name": api_key_name,
                "role_descriptors": role_descriptors,
                "expiration": "1h",
            },
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to generate API key: {response.text}")

        result = response.json()
        encoded_api_key = encode_api_key(result["id"], result["api_key"])

        logger.info(f"Generated ELK API key for org: {org_id}")

        return {
            "api_key": encoded_api_key,
            "name": api_key_name,
            "created": True,
            "message": "API key generated. Save it securely - you won't be able to see it again.",
            "expires_in_days": API_KEY_EXPIRY_DAYS,
        }


async def check_health(config_service: ConfigService) -> Dict:
    """Check ELK cluster health.

    Args:
        config_service: Configuration service for external services

    Returns:
        Dictionary with status, elk_host, cluster_status

    Example:
        >>> health = await check_health(config)
        >>> print(health["status"])  # "healthy" or "unhealthy"
    """
    try:
        elk_config = config_service.get_elk_config()
        auth_header = create_basic_auth_header(elk_config.user, elk_config.password)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://{elk_config.host}/_cluster/health",
                headers={"Authorization": f"Basic {auth_header}"},
            )

            if response.status_code == 200:
                cluster_health = response.json()
                return {
                    "status": "healthy",
                    "elk_host": elk_config.host,
                    "cluster_status": cluster_health.get("status", "unknown"),
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"ELK returned status {response.status_code}",
                }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
