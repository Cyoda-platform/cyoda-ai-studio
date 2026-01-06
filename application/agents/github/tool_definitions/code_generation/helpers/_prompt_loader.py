"""Prompt template loader for code generation."""

from __future__ import annotations

import logging

from application.agents.shared.prompt_loader import load_template

logger = logging.getLogger(__name__)


async def load_informational_prompt_template(language: str) -> str:
    """Load informational prompt template for CLI.

    These prompts are informational (for analysis/understanding) rather than
    action-based (for building). They help the CLI understand the codebase
    structure and patterns.

    Args:
        language: "python" or "java"

    Returns:
        Prompt template content or error message
    """
    try:
        # Try github_cli templates first for incremental changes
        template_name = f"github_cli_{language}_instructions"
        try:
            template_content = load_template(template_name)
            return template_content
        except FileNotFoundError:
            # Fallback to build agent templates
            template_name = f"build_{language}_instructions"
            template_content = load_template(template_name)
            return template_content

    except FileNotFoundError as e:
        logger.error(f"Prompt template not found: {e}")
        return f"ERROR: Prompt template not found: {str(e)}"
    except Exception as e:
        logger.error(f"Error loading prompt template: {e}", exc_info=True)
        return f"ERROR: Failed to load prompt template: {str(e)}"
