"""OpenAI SDK implementation of Canvas agent."""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Import OpenAI agents module directly to avoid namespace collision
_openai_agents = importlib.import_module("agents")
Agent = _openai_agents.Agent

from application.agents.canvas.prompts import create_instruction_provider
from application.agents.shared.openai_tool_adapter import adapt_adk_tools_list
from application.agents.canvas.tools import (
    validate_workflow_schema,
    validate_entity_schema,
    create_canvas_refresh_hook,
)


def create_openai_canvas_agent() -> Agent:
    """Create Canvas agent for OpenAI SDK.

    Helps create and manage canvas workflows.
    """
    adk_instruction_provider = create_instruction_provider("canvas_agent")

    def canvas_instructions(context: Any, agent: Any) -> str:
        return adk_instruction_provider(context)

    # Adapt ADK tools to OpenAI SDK format
    adk_tools = [
        validate_workflow_schema,
        validate_entity_schema,
        create_canvas_refresh_hook,
    ]
    openai_tools = adapt_adk_tools_list(adk_tools)

    canvas_agent = Agent(
        name="canvas_agent",
        instructions=canvas_instructions,
        handoff_description="Helps create and manage canvas workflows.",
        tools=openai_tools,
    )

    logger.info("✓ OpenAI Canvas Agent created with tools")
    return canvas_agent

