"""Hook utility functions for UI integration.

This module has been refactored into a package structure with focused modules.
All functions are re-exported from the subpackage for backward compatibility.

Original file: 623 lines
After split: 3 focused modules (task_hooks, selection_hooks, canvas_hooks)
All imports remain the same - this is a transparent refactoring.
"""

# Re-export all functions from the utilities subpackage
from .utilities import (
    # Task hooks
    create_background_task_hook,
    create_open_tasks_panel_hook,
    create_launch_setup_assistant_hook,
    create_build_and_deploy_hooks,
    # Selection hooks
    create_repository_config_selection_hook,
    create_option_selection_hook,
    create_resource_links_hook,
    create_issue_technical_user_hook,
    _create_branch_choice_options,
    _create_repository_type_options,
    _create_language_options,
    _build_repository_config_options,
    # Canvas hooks
    create_proceed_button_hook,
    create_canvas_with_proceed_hook,
    create_combined_hook,
    wrap_response_with_hook,
)

__all__ = [
    # Task hooks
    "create_background_task_hook",
    "create_open_tasks_panel_hook",
    "create_launch_setup_assistant_hook",
    "create_build_and_deploy_hooks",
    # Selection hooks
    "create_repository_config_selection_hook",
    "create_option_selection_hook",
    "create_resource_links_hook",
    "create_issue_technical_user_hook",
    "_create_branch_choice_options",
    "_create_repository_type_options",
    "_create_language_options",
    "_build_repository_config_options",
    # Canvas hooks
    "create_proceed_button_hook",
    "create_canvas_with_proceed_hook",
    "create_combined_hook",
    "wrap_response_with_hook",
]
