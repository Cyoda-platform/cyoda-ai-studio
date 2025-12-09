"""OpenAI Agents SDK coordinator with handoffs to all sub-agents.

Imports OpenAI Agent versions from each sub-agent's openai_agent.py
and creates a coordinator with handoffs.
"""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Import OpenAI agents module directly to avoid namespace collision
_openai_agents = importlib.import_module("agents")
Agent = _openai_agents.Agent
handoff = _openai_agents.handoff

from application.agents.qa.openai_agent import create_openai_qa_agent
from application.agents.setup.openai_agent import create_openai_setup_agent
from application.agents.guidelines.openai_agent import create_openai_guidelines_agent
from application.agents.environment.openai_agent import create_openai_environment_agent
from application.agents.canvas.openai_agent import create_openai_canvas_agent
from application.agents.github.openai_agent import create_openai_github_agent
from application.agents.cyoda_data_agent.openai_agent import create_openai_cyoda_data_agent
from application.agents.shared.prompts import create_instruction_provider





def create_openai_coordinator_agent() -> Agent:
    """Create coordinator agent with handoffs to all sub-agents.

    The coordinator routes user requests to appropriate sub-agents
    based on the nature of the request.
    """
    from application.agents.shared.openai_tool_adapter import adapt_adk_tools_list
    from application.agents.setup.tools import get_user_info

    # Create all sub-agents
    qa_agent = create_openai_qa_agent()
    setup_agent = create_openai_setup_agent()
    guidelines_agent = create_openai_guidelines_agent()
    environment_agent = create_openai_environment_agent()
    canvas_agent = create_openai_canvas_agent()
    github_agent = create_openai_github_agent()
    cyoda_data_agent = create_openai_cyoda_data_agent()

    # Create coordinator instructions
    adk_instruction_provider = create_instruction_provider("coordinator")

    def coordinator_instructions(context: Any, agent: Any) -> str:
        return adk_instruction_provider(context)

    # Adapt coordinator tools
    adk_tools = [get_user_info]
    openai_tools = adapt_adk_tools_list(adk_tools)

    # Create coordinator with handoffs to all sub-agents
    coordinator = Agent(
        name="cyoda_assistant",
        instructions=coordinator_instructions,
        handoff_description="Cyoda AI Assistant - helps users build and edit event-driven applications naturally",
        tools=openai_tools,
        handoffs=[
            handoff(qa_agent),
            handoff(setup_agent),
            handoff(guidelines_agent),
            handoff(environment_agent),
            handoff(canvas_agent),
            handoff(github_agent),
            handoff(cyoda_data_agent),
        ],
    )

    logger.info("✓ OpenAI Coordinator Agent created with handoffs to all sub-agents and tools")
    return coordinator

