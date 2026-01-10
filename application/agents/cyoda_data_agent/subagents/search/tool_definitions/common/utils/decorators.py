"""Decorators for search tools."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Union

from google.adk.tools.tool_context import ToolContext

from ..formatters.search_formatters import format_search_error

logger = logging.getLogger(__name__)


def handle_search_errors(func: Callable) -> Callable:
    """Decorator to handle search errors.

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
            logger.exception(f"Failed to search entities: {e}")
            return format_search_error(str(e))

    return wrapper
