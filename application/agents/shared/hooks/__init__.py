"""Hook system for Cyoda AI Studio.

This package provides hook functionality for agent tool integration:
- Hook decorators for marking tools that create hooks
- Hook definitions and registry
- Hook utilities and factories
- Prompt hook helpers
"""

from __future__ import annotations

# Core hook functionality
from .hook_decorator import creates_hook
# from .hook_definitions import HookType  # TODO: HookType is not defined in hook_definitions.py
from .hook_factory import HookFactory
from .hook_registry import HookRegistry
from .hook_utils import (
    create_code_changes_hook,
    create_background_task_hook,
    create_canvas_open_hook,
    create_proceed_button_hook,
    create_canvas_with_proceed_hook,
    create_resource_links_hook,
    create_repository_config_selection_hook,
    create_cloud_window_hook,
    create_open_canvas_tab_hook,
    create_option_selection_hook,
    create_deployment_hook,
    create_deploy_and_open_cloud_hook,
    create_combined_hook,
    wrap_response_with_hook,
    create_deploy_cyoda_environment_hook,
    create_launch_setup_assistant_hook,
    create_build_and_deploy_hooks,
    create_open_tasks_panel_hook,
    create_issue_technical_user_hook,
    detect_canvas_resources,
)

# Prompt hook functionality
from .prompt_hook_helper import PromptHookHelper, get_prompt_hook_helper

__all__ = [
    # Core hooks
    "creates_hook",
    "HookFactory",
    "HookRegistry",
    # Hook creation functions
    "create_code_changes_hook",
    "create_background_task_hook",
    "create_canvas_open_hook",
    "create_proceed_button_hook",
    "create_canvas_with_proceed_hook",
    "create_resource_links_hook",
    "create_repository_config_selection_hook",
    "create_cloud_window_hook",
    "create_open_canvas_tab_hook",
    "create_option_selection_hook",
    "create_deployment_hook",
    "create_deploy_and_open_cloud_hook",
    "create_combined_hook",
    "create_deploy_cyoda_environment_hook",
    "create_launch_setup_assistant_hook",
    "create_build_and_deploy_hooks",
    "create_open_tasks_panel_hook",
    "create_issue_technical_user_hook",
    # Utility functions
    "wrap_response_with_hook",
    "detect_canvas_resources",
    # Prompt hooks
    "PromptHookHelper",
    "get_prompt_hook_helper",
]
