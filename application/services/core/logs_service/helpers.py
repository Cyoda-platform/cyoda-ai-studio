"""Helper functions for logs service."""

import base64
import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)


def get_namespace(name: str) -> str:
    """Transform name into valid Kubernetes namespace format.

    Converts to lowercase and replaces non-alphanumeric characters with hyphens.

    Args:
        name: Name to transform

    Returns:
        Valid namespace string

    Example:
        >>> ns = get_namespace("MyOrg123")
        >>> print(ns)  # "myorg123"
    """
    return re.sub(r"[^a-z0-9-]", "-", name.lower())


def build_log_index_pattern(
    org_id: str, env_name: str, app_name: str = "cyoda"
) -> str:
    """Build Elasticsearch index pattern for logs.

    Args:
        org_id: Organization ID
        env_name: Environment name
        app_name: Application name (default: "cyoda")

    Returns:
        Elasticsearch index pattern

    Example:
        >>> pattern = build_log_index_pattern("myorg", "dev", "myapp")
        >>> print(pattern)  # "logs-client-1-myorg-dev-myapp*"
    """
    org_namespace = get_namespace(org_id)
    env_namespace = get_namespace(env_name)

    if app_name == "cyoda":
        return f"logs-client-{org_namespace}-{env_namespace}*"
    else:
        app_namespace = get_namespace(app_name)
        return f"logs-client-1-{org_namespace}-{env_namespace}-{app_namespace}*"


def build_role_descriptors(org_id: str) -> Dict:
    """Build role descriptors for read-only access.

    Args:
        org_id: Organization ID

    Returns:
        Role descriptors dictionary
    """
    return {
        f"logs_reader_{org_id}": {
            "cluster": [],
            "indices": [
                {
                    "names": [
                        f"logs-client-{org_id}*",
                        f"logs-client-1-{org_id}*",
                    ],
                    "privileges": ["read", "view_index_metadata"],
                    "allow_restricted_indices": False,
                }
            ],
            "run_as": [],
        }
    }


def encode_api_key(api_id: str, api_key: str) -> str:
    """Encode API key in Elasticsearch format.

    Args:
        api_id: API key ID
        api_key: API key value

    Returns:
        Base64 encoded API key
    """
    api_key_credentials = f"{api_id}:{api_key}"
    return base64.b64encode(api_key_credentials.encode("ascii")).decode("ascii")


def create_basic_auth_header(username: str, password: str) -> str:
    """Create Basic Authentication header value.

    Args:
        username: Username
        password: Password

    Returns:
        Base64-encoded auth string
    """
    auth_string = f"{username}:{password}"
    auth_bytes = auth_string.encode("ascii")
    return base64.b64encode(auth_bytes).decode("ascii")
