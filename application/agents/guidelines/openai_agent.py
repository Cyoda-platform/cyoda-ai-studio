"""OpenAI SDK implementation of Guidelines agent."""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Import OpenAI agents module directly to avoid namespace collision
_openai_agents = importlib.import_module("agents")
Agent = _openai_agents.Agent

from application.agents.guidelines.prompts import create_instruction_provider
from application.agents.shared.openai_tool_adapter import adapt_adk_tools_list
from application.agents.guidelines.tools import get_design_principle, get_testing_guideline
from application.agents.shared.tools import load_web_page


def create_openai_guidelines_agent() -> Agent:
    """Create Guidelines agent for OpenAI SDK.

    Provides guidance on best practices and patterns.
    """
    adk_instruction_provider = create_instruction_provider("guidelines_agent")

    def guidelines_instructions(context: Any, agent: Any) -> str:
        return adk_instruction_provider(context)

    # Adapt ADK tools to OpenAI SDK format
    adk_tools = [
        get_design_principle,
        get_testing_guideline,
        load_web_page,
    ]
    openai_tools = adapt_adk_tools_list(adk_tools)

    guidelines_agent = Agent(
        name="guidelines_agent",
        instructions=guidelines_instructions,
        handoff_description="Provides guidance on best practices and patterns.",
        tools=openai_tools,
    )

    logger.info("✓ OpenAI Guidelines Agent created with tools")
    return guidelines_agent

