"""Cyoda Data Agent - Multi-tenant agent for user-provided Cyoda environments."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.shared import get_model_config
from application.agents.shared.prompts import create_instruction_provider
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import create_entity, find_all_entities, get_entity, search_entities


root_agent = LlmAgent(
    name="cyoda_data_agent",
    model=get_model_config(),
    description="Multi-tenant Cyoda data agent. Accepts user credentials and interacts with their Cyoda environment.",
    instruction=create_instruction_provider("cyoda_data_agent"),
    tools=[
        get_entity,
        search_entities,
        create_entity,
        find_all_entities,
    ],
    after_agent_callback=accumulate_streaming_response,
)

