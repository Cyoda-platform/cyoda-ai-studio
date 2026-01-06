"""Hook Registry - Centralized metadata for all UI hooks.

Provides a single source of truth for hook definitions, enabling:
- Automatic documentation generation
- Hook discovery and validation
- Tool-hook mapping
- Prompt integration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParameterSpec:
    """Specification for a hook parameter."""

    name: str
    type: str
    required: bool
    description: str
    example: Optional[str] = None


@dataclass
class HookMetadata:
    """Metadata for a UI hook."""

    name: str
    hook_type: str
    description: str
    parameters: List[ParameterSpec] = field(default_factory=list)
    when_to_use: str = ""
    example: str = ""
    tool_names: List[str] = field(default_factory=list)
    deprecated: bool = False
    replacement: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "hook_type": self.hook_type,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "required": p.required,
                    "description": p.description,
                    "example": p.example,
                }
                for p in self.parameters
            ],
            "when_to_use": self.when_to_use,
            "example": self.example,
            "tool_names": self.tool_names,
            "deprecated": self.deprecated,
            "replacement": self.replacement,
        }


class HookRegistry:
    """Central registry for all UI hooks."""

    def __init__(self) -> None:
        """Initialize the hook registry."""
        self._hooks: Dict[str, HookMetadata] = {}
        self._tool_to_hooks: Dict[str, List[str]] = {}
        self._type_to_hooks: Dict[str, List[str]] = {}

    def register(self, metadata: HookMetadata) -> None:
        """Register a hook with metadata."""
        if metadata.name in self._hooks:
            logger.warning(f"Hook '{metadata.name}' already registered, overwriting")

        self._hooks[metadata.name] = metadata

        # Index by tool names
        for tool_name in metadata.tool_names:
            if tool_name not in self._tool_to_hooks:
                self._tool_to_hooks[tool_name] = []
            self._tool_to_hooks[tool_name].append(metadata.name)

        # Index by hook type
        if metadata.hook_type not in self._type_to_hooks:
            self._type_to_hooks[metadata.hook_type] = []
        self._type_to_hooks[metadata.hook_type].append(metadata.name)

        logger.info(f"✓ Registered hook: {metadata.name} (type: {metadata.hook_type})")

    def get_hook(self, name: str) -> Optional[HookMetadata]:
        """Get hook metadata by name."""
        return self._hooks.get(name)

    def get_hooks_by_tool(self, tool_name: str) -> List[HookMetadata]:
        """Get all hooks created by a specific tool."""
        hook_names = self._tool_to_hooks.get(tool_name, [])
        return [self._hooks[name] for name in hook_names if name in self._hooks]

    def get_hooks_by_type(self, hook_type: str) -> List[HookMetadata]:
        """Get all hooks of a specific type."""
        hook_names = self._type_to_hooks.get(hook_type, [])
        return [self._hooks[name] for name in hook_names if name in self._hooks]

    def list_all(self) -> List[HookMetadata]:
        """List all registered hooks."""
        return list(self._hooks.values())

    def list_active(self) -> List[HookMetadata]:
        """List all non-deprecated hooks."""
        return [h for h in self._hooks.values() if not h.deprecated]

    def validate_hook_exists(self, name: str) -> bool:
        """Check if a hook is registered."""
        return name in self._hooks

    def get_hook_types(self) -> List[str]:
        """Get all unique hook types."""
        return list(self._type_to_hooks.keys())

    def get_tools_with_hooks(self) -> List[str]:
        """Get all tools that create hooks."""
        return list(self._tool_to_hooks.keys())


# Global registry instance
_global_registry: Optional[HookRegistry] = None


def get_hook_registry() -> HookRegistry:
    """Get or create the global hook registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = HookRegistry()
        _initialize_default_hooks(_global_registry)
    return _global_registry


def _initialize_default_hooks(registry: HookRegistry) -> None:
    """Initialize registry with all default hooks."""
    try:
        from .hook_definitions import register_all_hooks
        register_all_hooks(registry)
        logger.info("✓ Initialized hook registry with default hooks")
    except ImportError as e:
        logger.warning(f"Could not load hook definitions: {e}")

