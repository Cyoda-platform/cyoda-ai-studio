"""Entity Model Subagent for Cyoda Data Agent.

This is the main subagent that handles all entity model operations:
- Model listing and retrieval
- Model import/export operations
- Model lifecycle management (lock/unlock)
- Workflow import/export
- Change level control
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.shared import get_model_config
from application.agents.shared.prompt_loader import load_template
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import (
    delete_entity_model,
    export_entity_workflows,
    export_model_metadata,
    import_entity_model,
    import_entity_workflows,
    list_entity_models,
    lock_entity_model,
    set_model_change_level,
    unlock_entity_model,
)


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


entity_model_agent = LlmAgent(
    name="entity_model_agent",
    model=get_model_config(),
    description="Manages all entity model operations: listing, import/export, lifecycle management, and workflows in user's Cyoda environment.",
    instruction=_get_instruction(),
    tools=[
        # Model listing and retrieval
        list_entity_models,
        # Model import/export
        export_model_metadata,
        import_entity_model,
        # Model lifecycle
        delete_entity_model,
        lock_entity_model,
        unlock_entity_model,
        set_model_change_level,
        # Workflow operations
        export_entity_workflows,
        import_entity_workflows,
    ],
    after_agent_callback=accumulate_streaming_response,
)

