"""Entity Management Subagent for Cyoda Data Agent.

This is the main subagent that handles all entity operations:
- Search operations (get, search, find all)
- CRUD operations (create, update, delete)
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from application.agents.shared import get_model_config
from application.agents.shared.prompt_loader import load_template
from application.agents.shared.streaming_callback import accumulate_streaming_response

from .tools import (
    create_entity,
    create_multiple_entities,
    delete_all_entities,
    delete_entity,
    execute_workflow_transition,
    find_all_entities,
    get_entity,
    get_entity_changes_metadata,
    get_entity_statistics,
    get_entity_statistics_by_state,
    get_entity_statistics_by_state_for_model,
    get_entity_statistics_for_model,
    save_multiple_entities,
    search_entities,
    update_entity,
    update_multiple_entities,
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


entity_management_agent = LlmAgent(
    name="entity_management_agent",
    model=get_model_config(),
    description="Manages all entity operations: search, create, update, delete, statistics, and workflows in user's Cyoda environment.",
    instruction=_get_instruction(),
    tools=[
        # Search operations
        get_entity,
        search_entities,
        find_all_entities,
        # Statistics operations
        get_entity_statistics,
        get_entity_statistics_by_state,
        get_entity_statistics_for_model,
        get_entity_statistics_by_state_for_model,
        # CRUD operations
        create_entity,
        create_multiple_entities,
        update_entity,
        update_multiple_entities,
        save_multiple_entities,
        delete_entity,
        delete_all_entities,
        # Workflow operations
        execute_workflow_transition,
        # Audit operations
        get_entity_changes_metadata,
    ],
    after_agent_callback=accumulate_streaming_response,
)

