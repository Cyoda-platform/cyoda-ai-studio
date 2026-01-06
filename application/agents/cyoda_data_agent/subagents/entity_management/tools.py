"""Thin registry for Entity Management tools.

This file imports tool implementations from the tool_definitions/ structure
and re-exports them for use by the agent. All implementations live in
tool_definitions/ following the modular architecture pattern.
"""

from __future__ import annotations

# Search tools
from .tool_definitions.search.tools.find_all_entities_tool import find_all_entities
from .tool_definitions.search.tools.get_entity_tool import get_entity
from .tool_definitions.search.tools.search_entities_tool import search_entities

# Statistics tools
from .tool_definitions.statistics.tools.get_entity_statistics_by_state_for_model_tool import (
    get_entity_statistics_by_state_for_model,
)
from .tool_definitions.statistics.tools.get_entity_statistics_by_state_tool import (
    get_entity_statistics_by_state,
)
from .tool_definitions.statistics.tools.get_entity_statistics_for_model_tool import (
    get_entity_statistics_for_model,
)
from .tool_definitions.statistics.tools.get_entity_statistics_tool import (
    get_entity_statistics,
)

# CRUD tools
from .tool_definitions.crud.tools.create_entity_tool import create_entity
from .tool_definitions.crud.tools.delete_all_entities_tool import delete_all_entities
from .tool_definitions.crud.tools.delete_entity_tool import delete_entity
from .tool_definitions.crud.tools.execute_workflow_transition_tool import (
    execute_workflow_transition,
)
from .tool_definitions.crud.tools.get_entity_changes_metadata_tool import (
    get_entity_changes_metadata,
)
from .tool_definitions.crud.tools.update_entity_tool import update_entity

# Batch tools
from .tool_definitions.batch.tools.create_multiple_entities_tool import (
    create_multiple_entities,
)
from .tool_definitions.batch.tools.save_multiple_entities_tool import (
    save_multiple_entities,
)
from .tool_definitions.batch.tools.update_multiple_entities_tool import (
    update_multiple_entities,
)

# Export all tools
__all__ = [
    # Search
    "get_entity",
    "search_entities",
    "find_all_entities",
    # Statistics
    "get_entity_statistics",
    "get_entity_statistics_by_state",
    "get_entity_statistics_for_model",
    "get_entity_statistics_by_state_for_model",
    # CRUD
    "create_entity",
    "update_entity",
    "delete_entity",
    "get_entity_changes_metadata",
    "delete_all_entities",
    "execute_workflow_transition",
    # Batch
    "create_multiple_entities",
    "update_multiple_entities",
    "save_multiple_entities",
]
