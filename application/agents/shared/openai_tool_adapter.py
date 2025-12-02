"""Adapter to convert Google ADK tools to OpenAI SDK function_tool format.

This module provides utilities to wrap Google ADK tools (which use ToolContext)
so they can be used with OpenAI SDK (which uses RunContextWrapper).
"""

import inspect
import json
import logging
from typing import Any, Callable, get_type_hints

from agents import function_tool, RunContextWrapper

logger = logging.getLogger(__name__)


def adapt_adk_tool_to_openai(adk_tool_func: Callable) -> Callable:
    """Adapt a Google ADK tool function to OpenAI SDK format.

    Converts a function that takes ToolContext to one that takes RunContextWrapper.
    Preserves the function's docstring and signature for proper tool registration.

    Args:
        adk_tool_func: Google ADK tool function (async or sync)

    Returns:
        Adapted function decorated with @function_tool for OpenAI SDK
    """
    # Get function signature and docstring
    sig = inspect.signature(adk_tool_func)
    doc = adk_tool_func.__doc__ or ""

    # Check if function is async
    is_async = inspect.iscoroutinefunction(adk_tool_func)

    # Get function parameters (excluding tool_context)
    params = list(sig.parameters.keys())
    has_tool_context = 'tool_context' in params
    other_params = [p for p in params if p != 'tool_context']

    # Create wrapper function with same signature (minus tool_context)
    if is_async:
        async def openai_wrapper(**kwargs: Any) -> str:
            """Wrapper that adapts OpenAI context to ADK tool."""
            # Call function with appropriate parameters
            if has_tool_context:
                # Create a mock ToolContext for functions that expect it
                class MockToolContext:
                    def __init__(self):
                        self.state = {}

                result = await adk_tool_func(MockToolContext(), **kwargs)
            else:
                # Function has no tool_context parameter, call with just kwargs
                result = await adk_tool_func(**kwargs)

            if isinstance(result, str):
                return result
            elif isinstance(result, dict):
                return json.dumps(result)
            else:
                return str(result)
    else:
        def openai_wrapper(**kwargs: Any) -> str:
            """Wrapper that adapts OpenAI context to ADK tool."""
            # Call function with appropriate parameters
            if has_tool_context:
                # Create a mock ToolContext for functions that expect it
                class MockToolContext:
                    def __init__(self):
                        self.state = {}

                result = adk_tool_func(MockToolContext(), **kwargs)
            else:
                # Function has no tool_context parameter, call with just kwargs
                result = adk_tool_func(**kwargs)

            if isinstance(result, str):
                return result
            elif isinstance(result, dict):
                return json.dumps(result)
            else:
                return str(result)

    # Preserve original function name and docstring
    openai_wrapper.__name__ = adk_tool_func.__name__
    openai_wrapper.__doc__ = doc

    # Decorate with @function_tool, disabling strict mode for compatibility
    return function_tool(openai_wrapper, strict_mode=False)


def adapt_adk_tools_list(adk_tools: list[Callable]) -> list[Callable]:
    """Adapt a list of Google ADK tools to OpenAI SDK format.
    
    Args:
        adk_tools: List of Google ADK tool functions
        
    Returns:
        List of adapted functions ready for OpenAI SDK
    """
    adapted = []
    for tool in adk_tools:
        try:
            adapted_tool = adapt_adk_tool_to_openai(tool)
            adapted.append(adapted_tool)
            logger.debug(f"✓ Adapted tool: {tool.__name__}")
        except Exception as e:
            logger.warning(f"Failed to adapt tool {tool.__name__}: {e}")
    
    return adapted

