"""OpenAI SDK implementation of QA agent."""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Import OpenAI agents module directly to avoid namespace collision
_openai_agents = importlib.import_module("agents")
Agent = _openai_agents.Agent

from application.agents.qa.prompts import create_instruction_provider
from application.agents.shared.openai_tool_adapter import adapt_adk_tools_list
from application.agents.qa.tools import explain_cyoda_pattern, search_cyoda_concepts
from application.agents.shared.tools import load_web_page, read_documentation


def create_openai_qa_agent() -> Agent:
    """Create QA agent for OpenAI SDK.

    Answers questions about CYODA platform architecture, concepts,
    entity management, workflows, and troubleshooting.
    """
    # Create instruction provider (Google ADK format)
    adk_instruction_provider = create_instruction_provider("qa_agent")

    # Adapt to OpenAI SDK format (requires 2 arguments: context, agent)
    def qa_instructions(context: Any, agent: Any) -> str:
        return adk_instruction_provider(context)

    # Adapt ADK tools to OpenAI SDK format
    adk_tools = [
        search_cyoda_concepts,
        explain_cyoda_pattern,
        read_documentation,
        load_web_page,
    ]
    openai_tools = adapt_adk_tools_list(adk_tools)

    qa_agent = Agent(
        name="qa_agent",
        instructions=qa_instructions,
        handoff_description=(
            "Cyoda platform expert. Answers questions about architecture, concepts, entity management, "
            "workflows, and troubleshooting."
        ),
        tools=openai_tools,
    )

    logger.info("✓ OpenAI QA Agent created with tools")
    return qa_agent

