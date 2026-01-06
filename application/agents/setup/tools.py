"""Thin registry for Setup agent tools.

This file imports tool implementations from the tool_definitions/ structure
and re-exports them for use by the agent. All implementations live in
tool_definitions/ following the modular architecture pattern.
"""

from __future__ import annotations

# Validation tools
from .tool_definitions.validation.tools.check_project_structure_tool import (
    check_project_structure,
)
from .tool_definitions.validation.tools.validate_environment_tool import (
    validate_environment,
)
from .tool_definitions.validation.tools.validate_workflow_file_tool import (
    validate_workflow_file,
)

# Context tools
from .tool_definitions.context.tools.get_build_context_tool import get_build_context
from .tool_definitions.context.tools.get_build_id_tool import get_build_id_from_context
from .tool_definitions.context.tools.get_user_info_tool import get_user_info

# Deployment tools
from .tool_definitions.deployment.tools.get_deploy_status_tool import (
    get_env_deploy_status,
)
from .tool_definitions.deployment.tools.issue_technical_user_tool import (
    ui_function_issue_technical_user,
)

# File operation tools
from .tool_definitions.files.tools.add_resource_tool import add_application_resource
from .tool_definitions.files.tools.list_directory_tool import list_directory_files
from .tool_definitions.files.tools.read_file_tool import read_file

# Setup tools
from .tool_definitions.setup.tools.finish_discussion_tool import finish_discussion
from .tool_definitions.setup.tools.set_setup_context_tool import set_setup_context

# UI tools
from .tool_definitions.ui.tools.show_setup_options_tool import show_setup_options

# Export all tools
__all__ = [
    # Validation
    "validate_environment",
    "check_project_structure",
    "validate_workflow_file",
    # Context
    "get_build_id_from_context",
    "get_build_context",
    "get_user_info",
    # Deployment
    "get_env_deploy_status",
    "ui_function_issue_technical_user",
    # Files
    "list_directory_files",
    "read_file",
    "add_application_resource",
    # Setup
    "set_setup_context",
    "finish_discussion",
    # UI
    "show_setup_options",
]
