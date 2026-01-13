"""Response formatting utilities for environment agent tools.

This module centralizes response formatting logic to maintain DRY principles
and separate presentation concerns from business logic.
"""

from __future__ import annotations

from typing import Optional


def format_deployment_started_message(
    build_id: str,
    repository_url: str,
    branch_name: str,
    user_id: str,
    task_id: Optional[str] = None,
    namespace: Optional[str] = None,
) -> str:
    """Format message for successful deployment initiation.

    Args:
        build_id: Build ID
        repository_url: Repository URL
        branch_name: Branch name
        user_id: User ID
        task_id: Optional task ID
        namespace: Optional namespace

    Returns:
        Formatted deployment started message
    """
    message = (
        f"✓ Application deployment started successfully!\n\n"
        f"**Build ID:** {build_id}\n"
        f"**Repository:** {repository_url}\n"
        f"**Branch:** {branch_name}\n"
        f"**User:** {user_id}"
    )

    if task_id:
        message += f"\n**Task ID:** {task_id}"
    if namespace:
        message += f"\n**Namespace:** {namespace}"

    message += (
        "\n\nYour application is being built and deployed. "
        "This typically takes 3-5 minutes.\n\nI'll keep you updated on the progress!"
    )

    return message


def format_environment_deployment_message(
    build_id: str,
    namespace: str,
    env_url: str,
    user_id: str,
    task_id: Optional[str] = None,
) -> str:
    """Format message for Cyoda environment deployment.

    Args:
        build_id: Build ID
        namespace: Namespace
        env_url: Environment URL
        user_id: User ID
        task_id: Optional task ID

    Returns:
        Formatted environment deployment message
    """
    message = f"SUCCESS: Environment deployment started (Build ID: {build_id}, Namespace: {namespace}"
    if task_id:
        message += f", Task ID: {task_id}"
    message += ")\n\n"

    message += (
        f"**Build ID:** {build_id}\n"
        f"**Namespace:** {namespace}\n"
        f"**Environment URL:** {env_url}\n"
        f"**User:** {user_id}"
    )

    if task_id:
        message += f"\n**Task ID:** {task_id}"

    message += (
        "\n\nYour Cyoda environment is being provisioned. "
        "This typically takes 5-10 minutes.\n\nI'll keep you updated on the progress!"
    )

    return message


def format_validation_error(field_name: str, suggestion: str) -> str:
    """Format validation error message.

    Args:
        field_name: Name of the field that failed validation
        suggestion: Suggestion for how to fix the error

    Returns:
        Formatted error message
    """
    return (
        f"Error: {field_name} parameter is required but was not provided. "
        f"You MUST ask the user for the {field_name} before calling this function. "
        f"Ask them: '{suggestion}' DO NOT assume or infer the {field_name}."
    )


def format_env_name_prompt_suggestion() -> str:
    """Get standard prompt suggestion for environment name.

    Returns:
        Prompt suggestion text
    """
    return "What environment would you like to deploy to? For example: dev, prod, staging, etc."


def format_app_name_prompt_suggestion() -> str:
    """Get standard prompt suggestion for application name.

    Returns:
        Prompt suggestion text
    """
    return (
        "What would you like to name this application? "
        "For example: my-app, payment-api, dashboard-v2, etc."
    )
