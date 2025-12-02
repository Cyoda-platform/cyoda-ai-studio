"""QA agent prompts.

This directory contains all prompt templates specific to the QA agent.
"""

from application.agents.shared.prompt_loader import (
    create_instruction_provider,
    load_template,
    load_nested_template,
)

__all__ = ["create_instruction_provider", "load_template", "load_nested_template"]

