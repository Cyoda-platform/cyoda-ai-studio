"""Coordinator Agent - Routes user requests to appropriate specialist agents."""

from __future__ import annotations

import logging

from google.adk.agents import LlmAgent

# Import all sub-agents
from application.agents.cyoda_data_agent.agent import root_agent as cyoda_data_agent
from application.agents.environment.agent import root_agent as environment_agent
from application.agents.github.agent import root_agent as github_agent
from application.agents.qa.agent import root_agent as qa_agent
from application.agents.shared import get_model_config
from application.agents.shared.prompts import create_instruction_provider

logger = logging.getLogger(__name__)

# Create coordinator agent with sub-agents
root_agent = LlmAgent(
    name="coordinator",
    model=get_model_config(),
    description="Coordinator - routes user requests to the appropriate specialist agent",
    instruction=create_instruction_provider("coordinator"),
    tools=[],
    sub_agents=[
        qa_agent,
        environment_agent,
        github_agent,
        cyoda_data_agent,
    ],
)

logger.info(
    "✓ Coordinator created with QA, Environment, " "GitHub, and Cyoda Data sub-agents"
)

agent = root_agent
