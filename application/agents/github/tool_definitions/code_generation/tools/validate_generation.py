"""Tool for validating that all entities and workflows were generated from requirements."""

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools.generation_validator import (
    GenerationValidator,
)

logger = logging.getLogger(__name__)


async def validate_generation(
    language: Optional[str] = None,
    repository_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Validate that all entities and workflows from functional requirements were generated.

    This tool compares the functional requirements against the generated code to ensure
    completeness. It reports any potentially missing entities or workflows.

    Call this tool after a build completes to verify all requirements were implemented.

    Args:
        language: Programming language (java/python). If not provided, taken from context.
        repository_path: Path to repository. If not provided, taken from context.
        tool_context: Tool execution context (auto-injected)

    Returns:
        Validation report showing expected vs generated items

    Example:
        After building an application, call this to check completeness:
        ```
        validate_generation()
        ```

        Or specify parameters explicitly:
        ```
        validate_generation(
            language="python",
            repository_path="/tmp/my-repo"
        )
        ```
    """
    try:
        # Get parameters from context if not provided
        if not language and tool_context:
            language = tool_context.state.get("language")

        if not repository_path and tool_context:
            repository_path = tool_context.state.get("repository_path")

        if not language:
            return "ERROR: language parameter required (either pass it or ensure it's in context)"

        if not repository_path:
            return "ERROR: repository_path parameter required (either pass it or ensure it's in context)"

        logger.info(
            f"🔍 Validating generation for {language} repository at {repository_path}"
        )

        # Get LLM client from tool context if available
        llm_client = None
        if tool_context and hasattr(tool_context, "llm_client"):
            llm_client = tool_context.llm_client

        # Run validation
        validation_passed, report = await GenerationValidator.validate_generation(
            language=language,
            repository_path=repository_path,
            llm_client=llm_client,
            tool_context=tool_context,
        )

        # Add header based on validation result
        if validation_passed:
            header = "✅ **Generation Validation: PASSED**\n"
        else:
            header = "⚠️ **Generation Validation: REVIEW NEEDED**\n"

        return f"{header}{report}"

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        return f"ERROR: Validation failed: {str(e)}"


__all__ = ["validate_generation"]
