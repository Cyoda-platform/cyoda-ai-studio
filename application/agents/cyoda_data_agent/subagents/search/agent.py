"""Search Subagent for Cyoda Data Agent.

This is the main subagent that handles synchronous entity search operations.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.shared import get_model_config
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import search_entities


def _get_instruction() -> str:
    """Load instruction template from subagent's prompts directory."""
    from pathlib import Path

    current_file = Path(__file__).resolve()
    prompts_dir = current_file.parent / "prompts"
    template_file = prompts_dir / "agent.template"

    if template_file.exists():
        return template_file.read_text(encoding="utf-8")
    else:
        raise FileNotFoundError(f"Template not found at {template_file}")


search_agent = LlmAgent(
    name="search_agent",
    model=get_model_config(),
    description="Performs synchronous entity searches with optional filtering conditions in user's Cyoda environment.",
    instruction=_get_instruction(),
    tools=[
        search_entities,
    ],
    after_agent_callback=accumulate_streaming_response,
)
