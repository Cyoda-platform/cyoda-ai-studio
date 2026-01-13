"""Helper for loading workflow prompts.

This module provides functionality to load workflow design instruction prompts.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def load_workflow_prompt() -> str:
    """Load the workflow design instructions from the prompts directory.

    Returns:
        Workflow prompt content as string, or error message if file not found
    """
    try:
        # Get the prompts directory relative to the github agent directory
        prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
        prompt_file = prompts_dir / "workflow_prompt.template"

        if not prompt_file.exists():
            return f"ERROR: Workflow prompt file not found at {prompt_file}"

        prompt_content = prompt_file.read_text(encoding="utf-8")
        logger.info(f"✅ Loaded workflow prompt from {prompt_file}")
        return prompt_content

    except Exception as e:
        logger.error(f"Error loading workflow prompt: {e}", exc_info=True)
        return f"ERROR: Failed to load workflow prompt: {str(e)}"
