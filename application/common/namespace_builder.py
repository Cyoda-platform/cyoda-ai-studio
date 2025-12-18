"""
Namespace Builder utility for consistent namespace construction.

Provides fluent interface for building Kubernetes namespace strings
and Elasticsearch index patterns with validation.
"""

import re
from typing import Optional


class NamespaceBuilder:
    """
    Builder for Kubernetes namespace and Elasticsearch index patterns.

    Implements Builder pattern with validation for namespace components.

    Example:
        >>> ns = (NamespaceBuilder()
        ...     .for_org("myorg")
        ...     .in_environment("dev")
        ...     .with_app("myapp")
        ...     .build())
        >>> print(ns)  # "client-1-myorg-dev-myapp"
    """

    def __init__(self):
        """Initialize empty namespace builder."""
        self._org_id: Optional[str] = None
        self._env_name: Optional[str] = None
        self._app_name: Optional[str] = None
        self._prefix: str = "client"
        self._use_version_prefix: bool = False

    @staticmethod
    def _normalize(name: str) -> str:
        """
        Normalize name to valid Kubernetes namespace format.

        Converts to lowercase and replaces invalid characters with hyphens.

        Args:
            name: Name to normalize

        Returns:
            Normalized name (lowercase, alphanumeric + hyphens)

        Example:
            >>> NamespaceBuilder._normalize("MyOrg_123")
            'myorg-123'
        """
        normalized = name.lower()
        normalized = re.sub(r"[^a-z0-9-]", "-", normalized)
        # Remove consecutive hyphens
        normalized = re.sub(r"-+", "-", normalized)
        # Remove leading/trailing hyphens
        normalized = normalized.strip("-")
        return normalized

    def for_org(self, org_id: str) -> "NamespaceBuilder":
        """
        Set organization ID.

        Args:
            org_id: Organization identifier

        Returns:
            Self for chaining

        Raises:
            ValueError: If org_id is empty

        Example:
            >>> builder.for_org("acme-corp")
        """
        if not org_id or not org_id.strip():
            raise ValueError("Organization ID cannot be empty")
        self._org_id = self._normalize(org_id.strip())
        return self

    def in_environment(self, env_name: str) -> "NamespaceBuilder":
        """
        Set environment name.

        Args:
            env_name: Environment name (e.g., "dev", "staging", "prod")

        Returns:
            Self for chaining

        Raises:
            ValueError: If env_name is empty

        Example:
            >>> builder.in_environment("production")
        """
        if not env_name or not env_name.strip():
            raise ValueError("Environment name cannot be empty")
        self._env_name = self._normalize(env_name.strip())
        return self

    def with_app(self, app_name: str) -> "NamespaceBuilder":
        """
        Set application name.

        Args:
            app_name: Application name

        Returns:
            Self for chaining

        Example:
            >>> builder.with_app("my-service")
        """
        if app_name and app_name.strip():
            self._app_name = self._normalize(app_name.strip())
            # Non-cyoda apps use version prefix
            if app_name.lower() != "cyoda":
                self._use_version_prefix = True
        return self

    def with_prefix(self, prefix: str) -> "NamespaceBuilder":
        """
        Set custom prefix (default: "client").

        Args:
            prefix: Namespace prefix

        Returns:
            Self for chaining

        Example:
            >>> builder.with_prefix("custom")
        """
        self._prefix = self._normalize(prefix)
        return self

    def build(self) -> str:
        """
        Build final namespace string.

        Returns:
            Kubernetes namespace

        Raises:
            ValueError: If required fields (org_id) not set

        Example:
            >>> ns = builder.build()
            >>> print(ns)
        """
        if not self._org_id:
            raise ValueError("Organization ID is required")

        parts = [self._prefix]

        # Add version prefix for non-cyoda apps
        if self._use_version_prefix:
            parts.append("1")

        parts.append(self._org_id)

        if self._env_name:
            parts.append(self._env_name)

        if self._app_name and self._app_name != "cyoda":
            parts.append(self._app_name)

        return "-".join(parts)

    def build_log_index(self) -> str:
        """
        Build Elasticsearch log index pattern.

        Returns:
            Elasticsearch index pattern for logs

        Raises:
            ValueError: If required fields not set

        Example:
            >>> index = builder.build_log_index()
            >>> print(index)  # "logs-client-myorg-dev*"
        """
        namespace = self.build()
        return f"logs-{namespace}*"


class NamespaceValidator:
    """
    Validator for namespace strings.

    Validates namespace format and components.
    """

    @staticmethod
    def is_valid(namespace: str) -> bool:
        """
        Check if namespace is valid Kubernetes format.

        Args:
            namespace: Namespace string to validate

        Returns:
            True if valid, False otherwise

        Example:
            >>> NamespaceValidator.is_valid("client-myorg-dev")
            True
            >>> NamespaceValidator.is_valid("Invalid_Namespace")
            False
        """
        if not namespace:
            return False

        # Kubernetes namespace requirements:
        # - lowercase alphanumeric + hyphens
        # - max 63 chars
        # - no leading/trailing hyphens
        if len(namespace) > 63:
            return False

        pattern = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"
        return bool(re.match(pattern, namespace))

    @staticmethod
    def validate(namespace: str) -> None:
        """
        Validate namespace or raise exception.

        Args:
            namespace: Namespace string to validate

        Raises:
            ValueError: If namespace is invalid

        Example:
            >>> NamespaceValidator.validate("client-myorg-dev")  # OK
            >>> NamespaceValidator.validate("Invalid")  # Raises ValueError
        """
        if not namespace:
            raise ValueError("Namespace cannot be empty")

        if len(namespace) > 63:
            raise ValueError(f"Namespace too long: {len(namespace)} chars (max 63)")

        if not NamespaceValidator.is_valid(namespace):
            raise ValueError(
                f"Invalid namespace format: '{namespace}'. "
                "Must be lowercase alphanumeric with hyphens, "
                "no leading/trailing hyphens."
            )


# Convenience functions for common patterns
def build_cyoda_namespace(org_id: str, env_name: str) -> str:
    """
    Build namespace for Cyoda core application.

    Args:
        org_id: Organization ID
        env_name: Environment name

    Returns:
        Namespace string

    Example:
        >>> ns = build_cyoda_namespace("myorg", "dev")
        >>> print(ns)  # "client-myorg-dev"
    """
    return (
        NamespaceBuilder()
        .for_org(org_id)
        .in_environment(env_name)
        .build()
    )


def build_app_namespace(org_id: str, env_name: str, app_name: str) -> str:
    """
    Build namespace for user application.

    Args:
        org_id: Organization ID
        env_name: Environment name
        app_name: Application name

    Returns:
        Namespace string

    Example:
        >>> ns = build_app_namespace("myorg", "dev", "myapp")
        >>> print(ns)  # "client-1-myorg-dev-myapp"
    """
    return (
        NamespaceBuilder()
        .for_org(org_id)
        .in_environment(env_name)
        .with_app(app_name)
        .build()
    )


def build_log_index(org_id: str, env_name: str, app_name: str = "cyoda") -> str:
    """
    Build Elasticsearch log index pattern.

    Args:
        org_id: Organization ID
        env_name: Environment name
        app_name: Application name (default: "cyoda")

    Returns:
        Elasticsearch index pattern

    Example:
        >>> index = build_log_index("myorg", "dev", "myapp")
        >>> print(index)  # "logs-client-1-myorg-dev-myapp*"
    """
    return (
        NamespaceBuilder()
        .for_org(org_id)
        .in_environment(env_name)
        .with_app(app_name)
        .build_log_index()
    )
