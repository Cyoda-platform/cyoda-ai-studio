"""
Shared tools and utilities for all agents.

This module contains tools that can be used by multiple agents in the system.
"""

from typing import Union

from google.adk.models.lite_llm import LiteLlm

# Monkey patch: Fix Google ADK agent_transfer tool's Optional type hint issue
# When typing.get_type_hints() is called on transfer_to_agent function,
# it needs Optional in the namespace for string annotation evaluation
try:
    import sys
    from typing import Optional

    from google.adk.tools import transfer_to_agent_tool

    # Add Optional to the module's globals so typing.get_type_hints() can find it
    # This is needed because the module uses 'from __future__ import annotations'
    # which makes all annotations strings, and typing.get_type_hints() needs to
    # evaluate them in the module's namespace
    transfer_to_agent_tool.__dict__["Optional"] = Optional

    # Also patch the transfer_to_agent function's globals directly
    if hasattr(transfer_to_agent_tool, "transfer_to_agent"):
        transfer_to_agent_tool.transfer_to_agent.__globals__["Optional"] = Optional
except (ImportError, AttributeError, KeyError):
    pass


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
            # Note: GPT-5-mini only supports temperature=1
        )

    # Otherwise, assume it's a Gemini model
    return AI_MODEL
