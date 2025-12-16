"""OpenAI SDK implementation of Setup agent."""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Import OpenAI agents module directly to avoid namespace collision
_openai_agents = importlib.import_module("agents")
Agent = _openai_agents.Agent

from application.agents.setup.prompts import create_instruction_provider


def create_openai_setup_agent() -> Agent:
    """Create Setup agent for OpenAI SDK.

    Helps users understand the setup process and connects them with specialized agents.
    """
    adk_instruction_provider = create_instruction_provider(
        "setup_agent",
        git_branch="<unknown>",
        programming_language="<unknown>",
        repository_name="<unknown>",
        entity_name="<unknown>",
        language="<unknown>",
    )

    def setup_instructions(context: Any, agent: Any) -> str:
        return adk_instruction_provider(context)

    # Setup agent is a guidance agent with no tools
    setup_agent = Agent(
        name="setup_agent",
        instructions=setup_instructions,
        handoff_description="Helps users understand the setup process and connects them with specialized agents for code analysis, deployment, and credentials.",
        tools=[],
    )

    logger.info("✓ OpenAI Setup Agent created (guidance agent, no tools)")
    return setup_agent

