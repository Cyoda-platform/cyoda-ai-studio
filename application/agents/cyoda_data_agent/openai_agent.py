"""OpenAI Agents SDK version of Cyoda Data Agent."""

from __future__ import annotations

import importlib
import logging

logger = logging.getLogger(__name__)

# Import OpenAI Agent SDK
_openai_agents = importlib.import_module("agents")
Agent = _openai_agents.Agent

from application.agents.cyoda_data_agent.tools import (
    create_entity,
    find_all_entities,
    get_entity,
    search_entities,
)
from application.agents.shared.openai_tool_adapter import adapt_adk_tools_list
from application.agents.shared.prompts import create_instruction_provider


def create_openai_cyoda_data_agent() -> Agent:
    """Create OpenAI Agents SDK version of Cyoda Data Agent.

    Returns:
        OpenAI Agent configured for multi-tenant Cyoda data operations
    """
    # Create instructions from template
    adk_instruction_provider = create_instruction_provider("cyoda_data_agent")

    def cyoda_data_instructions(context: any, agent: any) -> str:
        return adk_instruction_provider(context)

    # Adapt ADK tools to OpenAI SDK format
    adk_tools = [
        get_entity,
        search_entities,
        find_all_entities,
        create_entity,
    ]
    openai_tools = adapt_adk_tools_list(adk_tools)

    # Create agent
    cyoda_data_agent = Agent(
        name="cyoda_data_agent",
        instructions=cyoda_data_instructions,
        handoff_description=(
            "Multi-tenant Cyoda data agent. Accepts user credentials and interacts "
            "with their Cyoda environment."
        ),
        tools=openai_tools,
    )

    logger.info("✓ OpenAI Cyoda Data Agent created with tools")
    return cyoda_data_agent
