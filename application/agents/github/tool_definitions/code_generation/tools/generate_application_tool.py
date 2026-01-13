"""Tool for generating complete Cyoda applications.

This module provides full application generation from requirements.
"""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.code_generation.helpers import (
    APPLICATION_BUILD_CONFIG,
    _generate_code_core,
)

logger = logging.getLogger(__name__)


async def generate_application(
    requirements: str,
    language: Optional[str] = None,
    repository_path: Optional[str] = None,
    branch_name: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Generate a complete Cyoda application using configured CLI provider.

    This tool builds a COMPLETE application from scratch (entities, workflows,
    processors, routes, etc.). Use generate_code_with_cli() for incremental changes.

    **IMPORTANT:** This tool automatically saves all conversation files to the branch
    BEFORE generating the application. This ensures the AI has access to all attached
    files (requirements, specs, etc.) when building the application.

    Uses repository_path, branch_name, and language from tool_context.state if not provided.

    Args:
        requirements: User requirements - exactly what the user asked without modifications
        language: Programming language ('java' or 'python') - optional if already in context
        repository_path: Path to cloned repository - optional if already in context
        branch_name: Branch name for the build - optional if already in context
        tool_context: Execution context (auto-injected)

    Returns:
        Status message with task ID or error
    """
    return await _generate_code_core(
        user_input=requirements,
        config=APPLICATION_BUILD_CONFIG,
        tool_context=tool_context,
        language=language,
        repository_path=repository_path,
        branch_name=branch_name,
    )
