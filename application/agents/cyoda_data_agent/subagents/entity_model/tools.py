"""Thin registry for Entity Model tools.

This file imports tool implementations from the tool_definitions/ structure
and re-exports them for use by the agent. All implementations live in
tool_definitions/ following the modular architecture pattern.
"""

from __future__ import annotations

# Configuration tools
from .tool_definitions.config.tools.set_model_change_level_tool import (
    set_model_change_level,
)

# Model I/O tools
from .tool_definitions.model_io.tools.delete_entity_model_tool import (
    delete_entity_model,
)
from .tool_definitions.model_io.tools.export_model_metadata_tool import (
    export_model_metadata,
)
from .tool_definitions.model_io.tools.import_entity_model_tool import (
    import_entity_model,
)

# Model management tools
from .tool_definitions.model_management.tools.list_entity_models_tool import (
    list_entity_models,
)
from .tool_definitions.model_management.tools.lock_entity_model_tool import (
    lock_entity_model,
)
from .tool_definitions.model_management.tools.unlock_entity_model_tool import (
    unlock_entity_model,
)

# Workflow tools
from .tool_definitions.workflow.tools.export_entity_workflows_tool import (
    export_entity_workflows,
)
from .tool_definitions.workflow.tools.import_entity_workflows_tool import (
    import_entity_workflows,
)

# Export all tools
__all__ = [
    # Model management
    "list_entity_models",
    "lock_entity_model",
    "unlock_entity_model",
    # Model I/O
    "export_model_metadata",
    "import_entity_model",
    "delete_entity_model",
    # Workflow
    "export_entity_workflows",
    "import_entity_workflows",
    # Configuration
    "set_model_change_level",
]
