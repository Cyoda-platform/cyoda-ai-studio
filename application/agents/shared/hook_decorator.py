"""Hook Decorator - Marks tools that create hooks.

Enables:
- Automatic hook discovery
- Tool-hook mapping
- Hook documentation generation
- Tool introspection
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, List, Optional, TypeVar

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Metadata key for storing hook information on functions
_HOOK_METADATA_KEY = "__creates_hooks__"


def creates_hook(*hook_names: str) -> Callable[[F], F]:
    """Decorator to mark a tool as creating one or more hooks.

    Can be stacked to indicate multiple hooks created by a tool.

    Args:
        *hook_names: Names of hooks created by this tool

    Returns:
        Decorated function with hook metadata

    Example:
        @creates_hook("code_changes")
        @creates_hook("background_task")
        async def deploy_user_application(tool_context, ...):
            # Tool implementation
            pass
    """

    def decorator(func: F) -> F:
        # Get existing hooks or create new list
        existing_hooks = getattr(func, _HOOK_METADATA_KEY, [])
        new_hooks = list(existing_hooks) + list(hook_names)

        # Store hooks on function
        setattr(func, _HOOK_METADATA_KEY, new_hooks)

        logger.debug(
            f"✓ Marked tool '{func.__name__}' as creating hooks: {new_hooks}"
        )

        import inspect

        # Check if the function is async by inspecting its code
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await func(*args, **kwargs)
            wrapper = async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)
            wrapper = sync_wrapper

        # Preserve hook metadata on wrapper
        setattr(wrapper, _HOOK_METADATA_KEY, new_hooks)

        return wrapper  # type: ignore

    return decorator


def get_tool_hooks(func: Callable[..., Any]) -> List[str]:
    """Get list of hooks created by a tool.

    Args:
        func: Tool function

    Returns:
        List of hook names, empty list if none
    """
    return getattr(func, _HOOK_METADATA_KEY, [])


def has_hook_metadata(func: Callable[..., Any]) -> bool:
    """Check if a tool has hook metadata.

    Args:
        func: Tool function

    Returns:
        True if tool creates hooks
    """
    return hasattr(func, _HOOK_METADATA_KEY)


def get_tools_with_hooks(tools: List[Callable[..., Any]]) -> dict[str, List[str]]:
    """Get mapping of tools to their hooks.

    Args:
        tools: List of tool functions

    Returns:
        Dictionary mapping tool names to hook names
    """
    mapping = {}
    for tool in tools:
        hooks = get_tool_hooks(tool)
        if hooks:
            tool_name = getattr(tool, "__name__", str(tool))
            mapping[tool_name] = hooks
            logger.debug(f"Tool '{tool_name}' creates hooks: {hooks}")

    return mapping


def validate_tool_hooks(tools: List[Callable[..., Any]]) -> bool:
    """Validate that all hooks referenced by tools are registered.

    Args:
        tools: List of tool functions

    Returns:
        True if all hooks are valid

    Raises:
        ValueError: If any hook is not registered
    """
    from application.agents.shared.hook_registry import get_hook_registry

    registry = get_hook_registry()
    tool_hooks = get_tools_with_hooks(tools)

    for tool_name, hooks in tool_hooks.items():
        for hook_name in hooks:
            if not registry.validate_hook_exists(hook_name):
                raise ValueError(
                    f"Tool '{tool_name}' references unknown hook: {hook_name}"
                )

    logger.info(f"✓ Validated {len(tool_hooks)} tools with hooks")
    return True


def generate_tool_hook_documentation(
    tools: List[Callable[..., Any]],
) -> str:
    """Generate documentation for tool-hook relationships.

    Args:
        tools: List of tool functions

    Returns:
        Formatted documentation
    """
    tool_hooks = get_tools_with_hooks(tools)

    if not tool_hooks:
        return "No tools with hooks found."

    doc = "# Tools and Their Hooks\n\n"

    for tool_name, hooks in sorted(tool_hooks.items()):
        doc += f"## {tool_name}\n"
        doc += f"Creates hooks: {', '.join(f'`{h}`' for h in hooks)}\n\n"

    return doc

