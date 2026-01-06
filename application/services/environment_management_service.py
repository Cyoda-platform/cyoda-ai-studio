"""Environment management service for Cyoda environment operations.

This module has been refactored into a package structure with focused modules.
All classes and functions are re-exported from the subpackage for backward compatibility.

Original file: 670 lines
After split: 3 focused modules (namespace_operations, environment_operations, application_operations)
All imports remain the same - this is a transparent refactoring.
"""

# Re-export all classes from the environment_management subpackage
from .environment_management import (
    EnvironmentManagementService,
    get_environment_management_service,
    get_cloud_manager_service,
)

__all__ = [
    "EnvironmentManagementService",
    "get_environment_management_service",
    "get_cloud_manager_service",
]
