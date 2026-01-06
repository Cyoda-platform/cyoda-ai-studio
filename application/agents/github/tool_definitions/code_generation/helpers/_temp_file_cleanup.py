"""Helper for logging temporary file preservation.

This module provides functionality to log preservation of temporary files
created during CLI operations for audit trail and debugging purposes.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def log_temp_file_preserved(prompt_file: Optional[str] = None) -> None:
    """
    Log that temporary files have been preserved for audit trail.

    Temporary files (prompt and output files) are intentionally kept in /tmp
    for debugging and audit purposes. The OS will clean up /tmp periodically.

    Args:
        prompt_file: Path to temp prompt file that was preserved
    """
    if prompt_file:
        logger.info(f"📝 Prompt file preserved for audit trail: {prompt_file}")


# Backward compatibility alias
cleanup_temp_files = log_temp_file_preserved
