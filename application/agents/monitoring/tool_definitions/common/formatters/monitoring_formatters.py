"""Formatters for monitoring tools."""

from __future__ import annotations


def format_continue_monitoring(state: str, status: str, message: str | None = None) -> str:
    """Format continue monitoring response.

    Args:
        state: Deployment state
        status: Deployment status
        message: Optional additional message

    Returns:
        Formatted response
    """
    base = f"CONTINUE:Deployment in progress. State: {state}, Status: {status}."
    if message:
        return f"{base} {message}"
    return f"{base} Will check again in 30 seconds."


def format_escalate(state: str, status: str, is_success: bool) -> str:
    """Format escalate response for completed deployment.

    Args:
        state: Deployment state
        status: Deployment status
        is_success: Whether deployment succeeded

    Returns:
        Formatted response
    """
    if is_success:
        return f"ESCALATE:Deployment completed successfully! State: {state}, Status: {status}"
    return f"ESCALATE:Deployment failed. State: {state}, Status: {status}"


def format_wait_confirmation(seconds: int) -> str:
    """Format wait confirmation message.

    Args:
        seconds: Number of seconds waited

    Returns:
        Formatted response
    """
    return f"Waited {seconds} seconds. Ready for next status check."
