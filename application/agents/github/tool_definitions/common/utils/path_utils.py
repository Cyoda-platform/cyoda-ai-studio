"""Path utility functions for GitHub agent tools.

This module provides utilities for constructing resource paths
for entities, workflows, and functional requirements.
"""

from __future__ import annotations

from .project_utils import PYTHON_RESOURCES_PATH, JAVA_RESOURCES_PATH


def get_entity_path(entity_name: str, version: int, project_type: str) -> str:
    """
    Get the correct path for an entity file.

    Args:
        entity_name: Name of the entity (e.g., "order", "customer")
        version: Version number (e.g., 1)
        project_type: "python" or "java"

    Returns:
        Correct path for the entity file

    Examples:
        get_entity_path("order", 1, "python")
            -> "application/resources/entity/order/version_1/order.json"
        get_entity_path("customer", 1, "java")
            -> "src/main/resources/entity/customer/version_1/customer.json"
    """
    if project_type == "python":
        return f"{PYTHON_RESOURCES_PATH}/entity/{entity_name}/version_{version}/{entity_name}.json"
    elif project_type == "java":
        return f"{JAVA_RESOURCES_PATH}/entity/{entity_name}/version_{version}/{entity_name}.json"
    else:
        raise ValueError(f"Unsupported project type: {project_type}")


def get_workflow_path(workflow_name: str, project_type: str, version: int = 1) -> str:
    """
    Get the correct path for a workflow file in versioned folder structure.

    Args:
        workflow_name: Name of the workflow (e.g., "OrderProcessing", "CustomerOnboarding")
        project_type: "python" or "java"
        version: Version number (defaults to 1)

    Returns:
        Correct path for the workflow file in versioned folder

    Examples:
        get_workflow_path("OrderProcessing", "python", 1)
            -> "application/resources/workflow/orderprocessing/version_1/OrderProcessing.json"
        get_workflow_path("CustomerOnboarding", "java", 1)
            -> "src/main/resources/workflow/customeronboarding/version_1/CustomerOnboarding.json"
    """
    # Convert workflow name to lowercase for folder name (following entity pattern)
    folder_name = workflow_name.lower()

    if project_type == "python":
        return f"{PYTHON_RESOURCES_PATH}/workflow/{folder_name}/version_{version}/{workflow_name}.json"
    elif project_type == "java":
        return f"{JAVA_RESOURCES_PATH}/workflow/{folder_name}/version_{version}/{workflow_name}.json"
    else:
        raise ValueError(f"Unsupported project type: {project_type}")


def get_requirements_path(requirements_name: str, project_type: str) -> str:
    """
    Get the correct path for a functional requirements file.

    Args:
        requirements_name: Name of the requirements file (e.g., "order_management", "user_authentication")
        project_type: "python" or "java"

    Returns:
        Correct path for the requirements file

    Examples:
        get_requirements_path("order_management", "python")
            -> "application/resources/functional_requirements/order_management.md"
        get_requirements_path("user_auth", "java")
            -> "src/main/resources/functional_requirements/user_auth.md"
    """
    if project_type == "python":
        return f"{PYTHON_RESOURCES_PATH}/functional_requirements/{requirements_name}.md"
    elif project_type == "java":
        return f"{JAVA_RESOURCES_PATH}/functional_requirements/{requirements_name}.md"
    else:
        raise ValueError(f"Unsupported project type: {project_type}")
