"""Helper for loading workflow schema.

This module provides functionality to load the workflow JSON schema.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def load_workflow_schema() -> str:
    """Load the workflow schema from the prompts directory.

    Returns:
        JSON schema content as string, or error message if file not found
    """
    try:
        # Get the prompts directory relative to the github agent directory
        prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
        schema_file = prompts_dir / "workflow_schema.json"

        if not schema_file.exists():
            return f"ERROR: Workflow schema file not found at {schema_file}"

        schema_content = schema_file.read_text(encoding="utf-8")
        logger.info(f"✅ Loaded workflow schema from {schema_file}")
        return schema_content

    except Exception as e:
        logger.error(f"Error loading workflow schema: {e}", exc_info=True)
        return f"ERROR: Failed to load workflow schema: {str(e)}"
