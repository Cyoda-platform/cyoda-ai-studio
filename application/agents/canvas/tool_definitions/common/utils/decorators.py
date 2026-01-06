"""Decorators for canvas agent tools."""

from __future__ import annotations

import functools
import logging
from typing import Callable, Optional

from google.adk.tools.tool_context import ToolContext
from pydantic import ValidationError

from ..formatters.validation_formatters import format_validation_result

logger = logging.getLogger(__name__)


def handle_validation_errors(func: Callable) -> Callable:
    """Decorator to handle Pydantic validation errors.

    Args:
        func: The async function to wrap

    Returns:
        Wrapped function that catches validation errors
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValidationError as e:
            return format_validation_result(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return format_validation_result(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"]
            )

    # Copy type hints resolution requirements to wrapper's globals
    wrapper.__globals__.update({
        'Optional': Optional,
        'ToolContext': ToolContext,
    })

    return wrapper
