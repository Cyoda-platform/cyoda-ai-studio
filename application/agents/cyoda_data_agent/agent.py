"""Cyoda Data Agent - Multi-tenant orchestrator for user-provided Cyoda environments.

This is the root agent that orchestrates subagents for different Cyoda API domains.
All entity operations are delegated to the Entity Management subagent.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool

from application.agents.shared import get_model_config
from application.agents.shared.prompts import create_instruction_provider
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .subagents.entity_management import entity_management_agent
from .subagents.entity_model import entity_model_agent
from .subagents.search import search_agent

root_agent = LlmAgent(
    name="cyoda_data_agent",
    model=get_model_config(),
    description="Multi-tenant Cyoda data agent. Accepts user credentials and interacts with their Cyoda environment.",
    instruction=create_instruction_provider("cyoda_data_agent"),
    tools=[
        # Entity Management subagent handles CRUD operations on entities
        AgentTool(entity_management_agent),
        # Entity Model subagent handles model lifecycle and configuration
        AgentTool(entity_model_agent),
        # Search subagent handles synchronous entity searches
        AgentTool(search_agent),
    ],
    after_agent_callback=accumulate_streaming_response,
)

agent = root_agent
