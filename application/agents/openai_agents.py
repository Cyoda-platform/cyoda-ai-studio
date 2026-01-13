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

from application.agents.cyoda_data_agent.openai_agent import (
    create_openai_cyoda_data_agent,
)
from application.agents.environment.openai_agent import create_openai_environment_agent
from application.agents.github.openai_agent import create_openai_github_agent
from application.agents.qa.openai_agent import create_openai_qa_agent
from application.agents.shared.prompts import create_instruction_provider


def create_openai_coordinator_agent() -> Agent:
    """Create coordinator agent with handoffs to all sub-agents.

    The coordinator routes user requests to appropriate sub-agents
    based on the nature of the request.
    """
    # Create all sub-agents
    qa_agent = create_openai_qa_agent()
    environment_agent = create_openai_environment_agent()
    github_agent = create_openai_github_agent()
    cyoda_data_agent = create_openai_cyoda_data_agent()

    # Create coordinator instructions
    # Load from coordinator/prompts directory explicitly
    from pathlib import Path

    coordinator_agent_file = str(Path(__file__).parent / "coordinator" / "agent.py")
    adk_instruction_provider = create_instruction_provider("coordinator")

    # Load template directly with explicit caller path
    from application.agents.shared.prompt_loader import load_template

    coordinator_prompt = load_template(
        "coordinator", caller_file=coordinator_agent_file
    )

    def coordinator_instructions(context: Any, agent: Any) -> str:
        return coordinator_prompt

    # Create coordinator with handoffs to all sub-agents
    coordinator = Agent(
        name="cyoda_assistant",
        instructions=coordinator_instructions,
        handoff_description="Cyoda AI Assistant - helps users build and edit event-driven applications naturally",
        tools=[],
        handoffs=[
            handoff(qa_agent),
            handoff(environment_agent),
            handoff(github_agent),
            handoff(cyoda_data_agent),
        ],
    )

    logger.info("✓ OpenAI Coordinator Agent created with handoffs to all sub-agents")
    return coordinator
