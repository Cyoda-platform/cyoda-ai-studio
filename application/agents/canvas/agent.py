"""Canvas Agent for workflow, entity, and requirements creation with immediate persistence."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.canvas.prompts import create_instruction_provider
from application.agents.shared import get_model_config
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import (
    validate_workflow_schema,
    validate_entity_schema,
    create_canvas_refresh_hook,
)


# Prepare tools list
tools = [
    # Schema validation
    validate_workflow_schema,
    validate_entity_schema,
    # Canvas hooks
    create_canvas_refresh_hook,
]

# Main Canvas Agent
root_agent = LlmAgent(
    name="canvas_agent",
    model=get_model_config(),
    description=(
        "Canvas specialist for workflow, entity, and requirements creation with "
        "immediate persistence to repository."
    ),
    instruction=create_instruction_provider("canvas_agent"),
    tools=tools,
    after_agent_callback=accumulate_streaming_response,
)

import logging
logger = logging.getLogger(__name__)
logger.info("✓ Canvas Agent created with workflow, entity, and requirements creation tools")

agent = root_agent