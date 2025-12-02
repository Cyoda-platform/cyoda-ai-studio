"""Shared prompts used by multiple agents.

This directory contains prompt templates that are used by multiple agents
or by the coordinator.
"""

from application.agents.shared.prompt_loader import (
    create_instruction_provider,
    load_template,
    load_nested_template,
)

__all__ = ["create_instruction_provider", "load_template", "load_nested_template"]

