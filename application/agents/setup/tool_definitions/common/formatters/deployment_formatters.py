"""Formatters for deployment tools."""

from __future__ import annotations

import json


def format_deployment_status(state: str, status: str) -> str:
    """Format deployment status result.

    Args:
        state: Deployment state
        status: Deployment status

    Returns:
        Formatted string representation
    """
    return f"Deployment Status:\n- State: {state}\n- Status: {status}"


def format_ui_function(
    function_name: str,
    method: str,
    path: str,
    response_format: str = "json",
) -> str:
    """Format UI function call parameters.

    Args:
        function_name: Name of the UI function
        method: HTTP method
        path: API path
        response_format: Expected response format

    Returns:
        JSON string with UI function parameters
    """
    return json.dumps(
        {
            "type": "ui_function",
            "function": function_name,
            "method": method,
            "path": path,
            "response_format": response_format,
        }
    )
