"""Hook Factory - Centralized hook creation with validation.

Provides:
- Validated hook creation
- Parameter validation
- Hook versioning
- Consistent hook structure
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .hook_registry import get_hook_registry

logger = logging.getLogger(__name__)


class HookValidationError(Exception):
    """Raised when hook validation fails."""

    pass


class HookFactory:
    """Factory for creating and validating hooks."""

    def __init__(self) -> None:
        """Initialize the hook factory."""
        self.registry = get_hook_registry()

    def create_hook(
        self, hook_name: str, **parameters: Any
    ) -> Dict[str, Any]:
        """Create a hook with validation.

        Args:
            hook_name: Name of the hook to create
            **parameters: Hook parameters

        Returns:
            Hook dictionary

        Raises:
            HookValidationError: If validation fails
        """
        metadata = self.registry.get_hook(hook_name)
        if not metadata:
            raise HookValidationError(f"Unknown hook: {hook_name}")

        if metadata.deprecated:
            logger.warning(
                f"Hook '{hook_name}' is deprecated. "
                f"Use '{metadata.replacement}' instead."
            )

        # Validate required parameters
        self._validate_parameters(metadata, parameters)

        logger.info(f"✓ Creating hook: {hook_name}")
        return {
            "name": hook_name,
            "type": metadata.hook_type,
            "parameters": parameters,
        }

    def validate_parameters(
        self, hook_name: str, parameters: Dict[str, Any]
    ) -> bool:
        """Validate hook parameters without creating hook.

        Args:
            hook_name: Name of the hook
            parameters: Parameters to validate

        Returns:
            True if valid, raises HookValidationError otherwise
        """
        metadata = self.registry.get_hook(hook_name)
        if not metadata:
            raise HookValidationError(f"Unknown hook: {hook_name}")

        self._validate_parameters(metadata, parameters)
        return True

    def _validate_parameters(
        self, metadata: Any, parameters: Dict[str, Any]
    ) -> None:
        """Validate parameters against metadata.

        Args:
            metadata: Hook metadata
            parameters: Parameters to validate

        Raises:
            HookValidationError: If validation fails
        """
        # Check required parameters
        for param_spec in metadata.parameters:
            if param_spec.required and param_spec.name not in parameters:
                raise HookValidationError(
                    f"Missing required parameter: {param_spec.name} "
                    f"(type: {param_spec.type})"
                )

        # Check for unknown parameters
        valid_param_names = {p.name for p in metadata.parameters}
        for param_name in parameters:
            if param_name not in valid_param_names:
                logger.warning(
                    f"Unknown parameter '{param_name}' for hook '{metadata.name}'"
                )

    def get_hook_documentation(self, hook_name: str) -> str:
        """Get formatted documentation for a hook.

        Args:
            hook_name: Name of the hook

        Returns:
            Formatted documentation string
        """
        metadata = self.registry.get_hook(hook_name)
        if not metadata:
            return f"Hook '{hook_name}' not found"

        doc = f"# {metadata.name}\n\n"
        doc += f"**Type:** {metadata.hook_type}\n\n"
        doc += f"**Description:** {metadata.description}\n\n"

        if metadata.when_to_use:
            doc += f"**When to use:** {metadata.when_to_use}\n\n"

        if metadata.parameters:
            doc += "**Parameters:**\n"
            for param in metadata.parameters:
                required = "required" if param.required else "optional"
                doc += f"- `{param.name}` ({param.type}, {required}): {param.description}\n"
                if param.example:
                    doc += f"  Example: `{param.example}`\n"
            doc += "\n"

        if metadata.tool_names:
            doc += f"**Created by:** {', '.join(metadata.tool_names)}\n\n"

        if metadata.example:
            doc += f"**Example:**\n```python\n{metadata.example}\n```\n"

        if metadata.deprecated:
            doc += f"\n⚠️ **DEPRECATED** - Use `{metadata.replacement}` instead\n"

        return doc

    def list_hooks_for_tool(self, tool_name: str) -> list[str]:
        """List all hooks created by a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of hook names
        """
        hooks = self.registry.get_hooks_by_tool(tool_name)
        return [h.name for h in hooks]

    def list_hooks_by_type(self, hook_type: str) -> list[str]:
        """List all hooks of a specific type.

        Args:
            hook_type: Type of hook

        Returns:
            List of hook names
        """
        hooks = self.registry.get_hooks_by_type(hook_type)
        return [h.name for h in hooks]


# Global factory instance
_global_factory: Optional[HookFactory] = None


def get_hook_factory() -> HookFactory:
    """Get or create the global hook factory."""
    global _global_factory
    if _global_factory is None:
        _global_factory = HookFactory()
    return _global_factory

