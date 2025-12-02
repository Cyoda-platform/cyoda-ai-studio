"""
Shared tools and utilities for all agents.

This module contains tools that can be used by multiple agents in the system.
"""

from typing import Union

from google.adk.models.lite_llm import LiteLlm


# LLM configuration constants
LLM_REQUEST_TIMEOUT = 300  # 5 minutes timeout for LLM requests
LLM_NUM_RETRIES = 2  # Retry up to 2 times on LLM failures (total 3 attempts)


def get_model_config() -> Union[str, LiteLlm]:
    """Get model configuration based on AI_MODEL environment variable.

    Provides consistent LLM configuration across all agents with:
    - 5 minute request timeout for long tool executions
    - 2 retries on LLM failures (total 3 attempts)

    Returns:
        Model configuration (string for Gemini, LiteLlm instance for others)
    """
    from common.config.config import AI_MODEL

    # If model starts with "openai/" or "anthropic/", use LiteLLM
    if AI_MODEL.startswith(("openai/", "anthropic/")):
        return LiteLlm(
            model=AI_MODEL,
            request_timeout=LLM_REQUEST_TIMEOUT,
            num_retries=LLM_NUM_RETRIES,
        )

    # Otherwise, assume it's a Gemini model
    return AI_MODEL
