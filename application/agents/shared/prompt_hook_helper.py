"""Prompt Hook Helper - Integrates hooks into agent prompts.

Provides:
- Hook documentation for prompts
- Tool-hook mapping for prompts
- Auto-generated hook reference sections
- Hook usage examples
"""

from __future__ import annotations

import logging
from typing import List, Optional

from application.agents.shared.hook_factory import get_hook_factory
from application.agents.shared.hook_registry import get_hook_registry

logger = logging.getLogger(__name__)


class PromptHookHelper:
    """Helper for integrating hooks into agent prompts."""

    def __init__(self) -> None:
        """Initialize the prompt hook helper."""
        self.registry = get_hook_registry()
        self.factory = get_hook_factory()

    def get_available_hooks(self) -> List[str]:
        """Get list of all available hooks.

        Returns:
            List of hook names
        """
        hooks = self.registry.list_active()
        return [h.name for h in hooks]

    def get_hook_instructions(self, hook_name: str) -> str:
        """Get formatted instructions for using a hook.

        Args:
            hook_name: Name of the hook

        Returns:
            Formatted instructions
        """
        metadata = self.registry.get_hook(hook_name)
        if not metadata:
            return f"Hook '{hook_name}' not found"

        instructions = f"### {metadata.name}\n\n"
        instructions += f"{metadata.description}\n\n"

        if metadata.when_to_use:
            instructions += f"**When to use:** {metadata.when_to_use}\n\n"

        if metadata.tool_names:
            instructions += f"**Created by:** {', '.join(f'`{t}`' for t in metadata.tool_names)}\n\n"

        if metadata.example:
            instructions += f"**Example:**\n```python\n{metadata.example}\n```\n"

        return instructions

    def get_tool_for_hook(self, hook_name: str) -> Optional[str]:
        """Get the primary tool that creates a hook.

        Args:
            hook_name: Name of the hook

        Returns:
            Tool name or None if not found
        """
        metadata = self.registry.get_hook(hook_name)
        if metadata and metadata.tool_names:
            return metadata.tool_names[0]
        return None

    def get_hooks_for_tool(self, tool_name: str) -> List[str]:
        """Get all hooks created by a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of hook names
        """
        hooks = self.registry.get_hooks_by_tool(tool_name)
        return [h.name for h in hooks]

    def generate_hook_reference_section(self) -> str:
        """Generate a reference section for all hooks.

        Returns:
            Formatted reference section for use in prompts
        """
        hooks = self.registry.list_active()

        if not hooks:
            return "No hooks available."

        section = "## 🎣 Available Hooks\n\n"
        section += "The following hooks are available for use in your responses:\n\n"

        # Group by type
        by_type = {}
        for hook in hooks:
            if hook.hook_type not in by_type:
                by_type[hook.hook_type] = []
            by_type[hook.hook_type].append(hook)

        for hook_type, type_hooks in sorted(by_type.items()):
            section += f"### {hook_type.replace('_', ' ').title()}\n\n"
            for hook in type_hooks:
                section += f"- **{hook.name}**: {hook.description}\n"
                if hook.tool_names:
                    section += f"  Created by: {', '.join(hook.tool_names)}\n"
            section += "\n"

        return section

    def generate_tool_hook_mapping(self) -> str:
        """Generate mapping of tools to hooks.

        Returns:
            Formatted tool-hook mapping
        """
        tools = self.registry.get_tools_with_hooks()

        if not tools:
            return "No tools with hooks found."

        mapping = "## 🔗 Tool-Hook Mapping\n\n"
        mapping += "Tools that create hooks:\n\n"

        for tool_name in sorted(tools):
            hooks = self.registry.get_hooks_by_tool(tool_name)
            hook_names = [h.name for h in hooks]
            mapping += f"- **{tool_name}**: {', '.join(f'`{h}`' for h in hook_names)}\n"

        return mapping

    def generate_hook_usage_guide(self) -> str:
        """Generate a comprehensive hook usage guide.

        Returns:
            Formatted usage guide
        """
        guide = "# Hook Usage Guide\n\n"
        guide += "## Core Principles\n\n"
        guide += "1. **Hooks are buttons, not questions** - Don't ask permission\n"
        guide += "2. **Call tools to create hooks** - Never create JSON manually\n"
        guide += "3. **One hook per action** - Avoid duplicate hooks\n"
        guide += "4. **Include context** - Make hook content specific and useful\n\n"

        guide += self.generate_hook_reference_section()
        guide += "\n"
        guide += self.generate_tool_hook_mapping()

        return guide

    def validate_hook_usage(self, hook_name: str) -> bool:
        """Validate that a hook is registered and active.

        Args:
            hook_name: Name of the hook

        Returns:
            True if hook is valid and active
        """
        metadata = self.registry.get_hook(hook_name)
        if not metadata:
            logger.warning(f"Hook '{hook_name}' not found in registry")
            return False

        if metadata.deprecated:
            logger.warning(
                f"Hook '{hook_name}' is deprecated. Use '{metadata.replacement}' instead"
            )
            return False

        return True


# Global helper instance
_global_helper: Optional[PromptHookHelper] = None


def get_prompt_hook_helper() -> PromptHookHelper:
    """Get or create the global prompt hook helper."""
    global _global_helper
    if _global_helper is None:
        _global_helper = PromptHookHelper()
    return _global_helper

