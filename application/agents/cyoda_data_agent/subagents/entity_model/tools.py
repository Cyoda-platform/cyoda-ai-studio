"""Thin registry for Entity Model tools.

This file imports tool implementations from the tool_definitions/ structure
and re-exports them for use by the agent. All implementations live in
tool_definitions/ following the modular architecture pattern.
"""

from __future__ import annotations

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation by Google ADK
# This is needed because 'from __future__ import annotations' makes all annotations strings,
# and typing.get_type_hints() needs to resolve ToolContext in the module's globals
# Must be done BEFORE any function definitions so it's in the module's namespace
__all__ = ["ToolContext"]

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
__all__.extend(
    [
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
)
