"""Thin registry for Deployment Monitoring agent tools.

This file imports tool implementations from the tool_definitions/ structure
and re-exports them for use by the agent. All implementations live in
tool_definitions/ following the modular architecture pattern.
"""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation by Google ADK
# This is needed because 'from __future__ import annotations' makes all annotations strings,
# and typing.get_type_hints() needs to resolve ToolContext in the module's globals
# Must be done BEFORE any function definitions so it's in the module's namespace
__all__ = ["ToolContext"]

# Deployment monitoring tools
from .tool_definitions.deployment.tools.check_deployment_tool import (
    check_deployment_and_decide,
)
from .tool_definitions.deployment.tools.wait_tool import wait_before_next_check

# Export all tools
__all__.extend(
    [
        "check_deployment_and_decide",
        "wait_before_next_check",
    ]
)
