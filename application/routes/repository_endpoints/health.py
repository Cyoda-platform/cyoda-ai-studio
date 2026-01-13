"""Health check endpoint."""

from quart.typing import ResponseReturnValue

from application.routes.common.response import APIResponse


async def handle_health_check() -> ResponseReturnValue:
    """Health check endpoint for repository service."""
    return APIResponse.success({"status": "healthy", "service": "repository"})
