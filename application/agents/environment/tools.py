"""Tools for the Environment Management agent.

This module serves as a Tool Registry that imports and re-exports tool implementations
from the tool_definitions/ package. Each tool is implemented in its own file for better
modularity and maintainability.
"""

from __future__ import annotations

import logging

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation by Google ADK
# This is needed because 'from __future__ import annotations' makes all annotations strings,
# and typing.get_type_hints() needs to resolve ToolContext in the module's globals
# Must be done BEFORE any function definitions so it's in the module's namespace
__all__ = ["ToolContext"]

# Import tool implementations from tool_definitions package (organized by category)

# Re-export service getters for backward compatibility with tests
from application.services.cloud_manager_service import get_cloud_manager_service
from application.services.deployment.service import get_deployment_service
from application.services.environment_management_service import (
    get_environment_management_service,
)

# Cyoda application tools
from .tool_definitions.application import (
    get_application_details,
    get_application_status,
    restart_application,
    scale_application,
    update_application_image,
)

# Deployment tools
from .tool_definitions.deployment import (
    deploy_cyoda_environment,
    deploy_user_application,
    get_build_logs,
    get_deployment_status,
)

# Re-export deployment helpers for backward compatibility with tests
from .tool_definitions.deployment.helpers._deployment_helpers import (
    handle_deployment_success as _handle_deployment_success,
)
from .tool_definitions.deployment.helpers._deployment_monitor import (
    monitor_deployment_progress as _monitor_deployment_progress,
)

# Environment management tools
from .tool_definitions.environment import (
    check_environment_exists,
    delete_environment,
    describe_environment,
    get_environment_metrics,
    get_environment_pods,
    list_environments,
)

# Other tools
from .tool_definitions.other import (
    issue_technical_user,
    search_logs,
)

# User application tools
from .tool_definitions.user_apps import (
    delete_user_app,
    get_user_app_details,
    get_user_app_metrics,
    get_user_app_pods,
    get_user_app_status,
    list_user_apps,
    restart_user_app,
    scale_user_app,
    update_user_app_image,
)

logger = logging.getLogger(__name__)

# All tool implementations have been migrated to individual files in tool_definitions/
# This module now serves purely as a tool registry that imports and re-exports tools
