"""Entity Management Subagent for Cyoda Data Agent."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.shared import get_model_config
from application.agents.shared.prompts import create_instruction_provider
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .entity_management_tools import create_entity, delete_entity, update_entity


entity_management_agent = LlmAgent(
    name="entity_management_agent",
    model=get_model_config(),
    description="Manages entity lifecycle: create, update, and delete operations in user's Cyoda environment.",
    instruction=create_instruction_provider("entity_management_agent"),
    tools=[
        create_entity,
        update_entity,
        delete_entity,
    ],
    after_agent_callback=accumulate_streaming_response,
)

