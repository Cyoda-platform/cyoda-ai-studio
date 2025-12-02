"""Guidelines agent for Cyoda development best practices."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.guidelines.prompts import create_instruction_provider
from application.agents.shared import get_model_config
from application.agents.shared.tools import load_web_page
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import get_design_principle, get_testing_guideline


root_agent = LlmAgent(
    name="guidelines_agent",
    model=get_model_config(),
    description="Cyoda development expert. Provides guidelines, best practices, and design patterns for Pythonic Cyoda development.",
    instruction=create_instruction_provider("guidelines_agent"),
    tools=[
        get_design_principle,
        get_testing_guideline,
        load_web_page,
    ],
    after_agent_callback=accumulate_streaming_response,
)
