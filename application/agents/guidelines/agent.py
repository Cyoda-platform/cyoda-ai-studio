"""Guidelines agent for Cyoda development best practices."""

from __future__ import annotations

import os
from typing import Union

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from application.agents.prompts import create_instruction_provider
from application.agents.shared.tools import load_web_page

from .tools import get_design_principle, get_testing_guideline


def _get_model_config() -> Union[str, LiteLlm]:
    """Get model configuration based on AI_MODEL environment variable."""
    model_name = os.getenv("AI_MODEL", "gemini-2.0-flash-exp")
    if model_name.startswith(("openai/", "anthropic/")):
        return LiteLlm(model=model_name)
    return model_name


root_agent = LlmAgent(
    name="guidelines_agent",
    model=_get_model_config(),
    description="Cyoda development expert. Provides guidelines, best practices, and design patterns for Pythonic Cyoda development.",
    instruction=create_instruction_provider("guidelines_agent"),
    tools=[
        get_design_principle,
        get_testing_guideline,
        load_web_page,
    ],
)
