"""Cyoda Data Agent - Multi-tenant agent for user-provided Cyoda environments."""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation
__all__ = ["ToolContext", "root_agent"]

from application.agents.cyoda_data_agent.agent import root_agent
