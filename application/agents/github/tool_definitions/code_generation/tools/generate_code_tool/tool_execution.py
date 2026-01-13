"""Main tool execution and response formatting.

This module contains the main generate_code_with_cli function.
"""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.code_generation.helpers import (
    CODE_GENERATION_CONFIG,
    _generate_code_core,
)

logger = logging.getLogger(__name__)


async def generate_code_with_cli(
    user_request: str,
    tool_context: Optional[ToolContext] = None,
    language: Optional[str] = None,
) -> str:
    """Generate code using CLI based on user request.

    This tool uses CLI to generate code (entities, workflows, processors, etc.)
    based on the user's natural language request. Unlike the build agent which creates
    entire applications, this tool is for incremental code generation in an existing
    repository.

    The prompts used are INFORMATIONAL - they help the CLI understand the codebase
    structure and patterns, then the CLI takes action based on the user's request.

    IMPORTANT: This tool modifies files in the repository. Do not run multiple
    instances concurrently on the same repository to avoid conflicts.

    Args:
        user_request: Natural language description of what code to generate
        tool_context: Execution context
        language: "python" or "java" (auto-detected if not provided)

    Returns:
        Success message or error

    Timeout:
        1 hour (same as CLI script)

    Examples:
        >>> await generate_code_with_cli(
        ...     "Add a Customer entity with id, name, email, and phone fields",
        ...     tool_context
        ... )
        "✅ Code generated successfully. Files created: application/entity/customer/..."
    """
    return await _generate_code_core(
        user_input=user_request,
        config=CODE_GENERATION_CONFIG,
        tool_context=tool_context,
        language=language,
    )
