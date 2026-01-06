"""Hook utility functions for UI integration.

This package is organized into focused modules:
- task_hooks: Background task notifications and task panel management
- selection_hooks: Option selection, repository config, and resource links
- canvas_hooks: Proceed buttons, canvas integration, and combined hooks

All functions are re-exported from this package for backward compatibility.
"""

# Task-related hooks
from .task_hooks import (
    create_background_task_hook,
    create_open_tasks_panel_hook,
    create_launch_setup_assistant_hook,
    create_build_and_deploy_hooks,
)

# Selection and configuration hooks
from .selection_hooks import (
    create_repository_config_selection_hook,
    create_option_selection_hook,
    create_resource_links_hook,
    create_issue_technical_user_hook,
    _create_branch_choice_options,
    _create_repository_type_options,
    _create_language_options,
    _build_repository_config_options,
)

# Canvas and UI element hooks
from .canvas_hooks import (
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
