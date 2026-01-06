"""Setup agent for Cyoda project configuration."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.setup.prompts import create_instruction_provider
from application.agents.shared import get_model_config
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import show_setup_options


root_agent = LlmAgent(
    name="setup_agent",
    model=get_model_config(),
    description=(
        "Cyoda setup guidance specialist. Helps users understand the setup process and connects them "
        "with specialized agents for code analysis, deployment, and credentials."
    ),
    instruction=create_instruction_provider(
        "setup_agent",
        git_branch="<unknown>",
        programming_language="<unknown>",
        repository_name="<unknown>",
        entity_name="<unknown>",
        language="<unknown>",
    ),
    tools=[
        show_setup_options,
    ],
    after_agent_callback=accumulate_streaming_response,
)
agent = root_agent