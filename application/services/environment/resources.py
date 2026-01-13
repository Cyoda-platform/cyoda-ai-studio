"""Service for Kubernetes resource operations.

This module provides a backward-compatible wrapper for the refactored resources package.
All functionality has been split into focused modules within resources/.
"""

# Re-export all public APIs from the package
from .resources import (
    DeploymentOperations,
    EnvironmentResourceService,
    NamespaceOperations,
    UserAppOperations,
)

__all__ = [
    "EnvironmentResourceService",
    "NamespaceOperations",
    "DeploymentOperations",
    "UserAppOperations",
]
