"""QA agent for Cyoda platform questions."""

from __future__ import annotations

import os
from typing import Union

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from application.agents.prompts import create_instruction_provider
from application.agents.shared.tools import load_web_page

from .tools import explain_cyoda_pattern, search_cyoda_concepts


def _get_model_config() -> Union[str, LiteLlm]:
    """Get model configuration based on AI_MODEL environment variable."""
    model_name = os.getenv("AI_MODEL", "gemini-2.0-flash-exp")
    if model_name.startswith(("openai/", "anthropic/")):
        return LiteLlm(model=model_name)
    return model_name


root_agent = LlmAgent(
    name="qa_agent",
    model=_get_model_config(),
    description="Cyoda platform expert. Answers questions about architecture, concepts, entity management, workflows, and troubleshooting.",
    instruction=create_instruction_provider("qa_agent"),
    tools=[
        search_cyoda_concepts,
        explain_cyoda_pattern,
        load_web_page,
    ],
)
