"""Helper for loading workflow examples.

This module provides functionality to load example workflow JSON files.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def load_workflow_example() -> str:
    """Load the example workflow from the prompts directory.

    Returns:
        Example workflow JSON content as string, or error message if file not found
    """
    try:
        # Get the prompts directory relative to the github agent directory
        prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
        example_file = prompts_dir / "ExampleEntity.json"

        if not example_file.exists():
            return f"ERROR: Example workflow file not found at {example_file}"

        example_content = example_file.read_text(encoding="utf-8")
        logger.info(f"✅ Loaded example workflow from {example_file}")
        return example_content

    except Exception as e:
        logger.error(f"Error loading example workflow: {e}", exc_info=True)
        return f"ERROR: Failed to load example workflow: {str(e)}"
