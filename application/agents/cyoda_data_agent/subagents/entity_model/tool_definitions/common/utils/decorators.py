"""Decorators for entity model management tools."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Union

from google.adk.tools.tool_context import ToolContext

from ...common.formatters.model_formatters import format_model_error

logger = logging.getLogger(__name__)


def handle_model_errors(func: Callable) -> Callable:
    """Decorator to handle model tool errors gracefully.

    Args:
        func: The async function to wrap

    Returns:
        Wrapped function that catches and logs exceptions
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Failed to {func.__name__}: {error_msg}")
            return format_model_error(error_msg)

    return wrapper
