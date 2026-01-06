"""Hook Definitions - Metadata for all UI hooks.

Centralizes hook definitions to enable:
- Single source of truth for hook parameters
- Automatic documentation generation
- Hook discovery and validation
- Tool-hook mapping
"""

from __future__ import annotations

from .hook_registry import (
    HookMetadata,
    HookRegistry,
    ParameterSpec,
)


def _register_canvas_hooks(registry: HookRegistry) -> None:
    """Register hooks for canvas tab interactions."""
    registry.register(
        HookMetadata(
            name="open_canvas_tab",
            hook_type="canvas_tab",
            description="Opens a specific canvas tab (entities, workflows, requirements, cloud)",
            parameters=[
                ParameterSpec(
                    name="conversation_id",
                    type="str",
                    required=True,
                    description="Conversation technical ID",
                ),
                ParameterSpec(
                    name="tab_name",
                    type="str",
                    required=True,
                    description="Tab to open: entities, workflows, requirements, or cloud",
                    example="entities",
                ),
                ParameterSpec(
                    name="message",
                    type="str",
                    required=False,
                    description="Button text to display",
                    example="View Customer Entity",
                ),
            ],
            when_to_use="After creating/modifying entities, workflows, or requirements",
            tool_names=["github_agent_tools"],
            example="hook = create_open_canvas_tab_hook(conversation_id, tab_name='entities')",
        )
    )


def _register_code_change_hooks(registry: HookRegistry) -> None:
    """Register hooks for tracking code changes."""
    registry.register(
        HookMetadata(
            name="code_changes",
            hook_type="code_changes",
            description="Triggers canvas refresh after code changes",
            parameters=[
                ParameterSpec(
                    name="conversation_id",
                    type="str",
                    required=True,
                    description="Conversation technical ID",
                ),
                ParameterSpec(
                    name="repository_name",
                    type="str",
                    required=True,
                    description="Repository name",
                ),
                ParameterSpec(
                    name="branch_name",
                    type="str",
                    required=True,
                    description="Git branch name",
                ),
                ParameterSpec(
                    name="changed_files",
                    type="List[str]",
                    required=True,
                    description="List of changed file paths",
                ),
                ParameterSpec(
                    name="resource_type",
                    type="str",
                    required=False,
                    description="Type of resource: entity, workflow, requirement",
                ),
            ],
            when_to_use="After committing code changes to refresh canvas",
            tool_names=["github_agent_tools"],
        )
    )


def _register_option_selection_hooks(registry: HookRegistry) -> None:
    """Register hooks for user option selection prompts."""
    registry.register(
        HookMetadata(
            name="option_selection",
            hook_type="option_selection",
            description="Shows user a selection of options to choose from",
            parameters=[
                ParameterSpec(
                    name="conversation_id",
                    type="str",
                    required=True,
                    description="Conversation technical ID",
                ),
                ParameterSpec(
                    name="question",
                    type="str",
                    required=True,
                    description="Question to display to user",
                ),
                ParameterSpec(
                    name="options",
                    type="List[Dict]",
                    required=True,
                    description="List of option dicts with value, label, description",
                ),
                ParameterSpec(
                    name="selection_type",
                    type="str",
                    required=False,
                    description="single or multiple",
                    example="single",
                ),
            ],
            when_to_use="When user needs to choose from predefined options",
            tool_names=["environment_agent_tools", "setup_agent_tools"],
        )
    )


def _register_cloud_window_hooks(registry: HookRegistry) -> None:
    """Register hooks for cloud/environment panel interactions."""
    registry.register(
        HookMetadata(
            name="cloud_window",
            hook_type="cloud_window",
            description="Opens Cloud/Environments panel in UI",
            parameters=[
                ParameterSpec(
                    name="conversation_id",
                    type="str",
                    required=True,
                    description="Conversation technical ID",
                ),
                ParameterSpec(
                    name="action",
                    type="str",
                    required=True,
                    description="Action to perform: open_environments_panel, open_cloud_tab",
                ),
                ParameterSpec(
                    name="environment_url",
                    type="str",
                    required=False,
                    description="Optional environment URL",
                ),
            ],
            when_to_use="After environment deployment or status check",
            tool_names=["environment_agent_tools"],
        )
    )


def _register_background_task_hooks(registry: HookRegistry) -> None:
    """Register hooks for background task tracking."""
    registry.register(
        HookMetadata(
            name="background_task",
            hook_type="background_task",
            description="Tracks background task execution (build, deploy, etc.)",
            parameters=[
                ParameterSpec(
                    name="task_id",
                    type="str",
                    required=True,
                    description="Unique task ID",
                ),
                ParameterSpec(
                    name="task_type",
                    type="str",
                    required=True,
                    description="Type: build, deploy, setup, etc.",
                ),
                ParameterSpec(
                    name="task_name",
                    type="str",
                    required=True,
                    description="Human-readable task name",
                ),
                ParameterSpec(
                    name="conversation_id",
                    type="str",
                    required=True,
                    description="Conversation technical ID",
                ),
            ],
            when_to_use="When starting long-running background tasks",
            tool_names=["environment_agent_tools", "github_agent_tools"],
        )
    )


def _register_tasks_panel_hooks(registry: HookRegistry) -> None:
    """Register hooks for tasks panel display."""
    registry.register(
        HookMetadata(
            name="open_tasks_panel",
            hook_type="tasks_panel",
            description="Opens the Tasks panel to show deployment/build progress",
            parameters=[
                ParameterSpec(
                    name="conversation_id",
                    type="str",
                    required=True,
                    description="Conversation technical ID",
                ),
                ParameterSpec(
                    name="task_id",
                    type="str",
                    required=False,
                    description="Optional task ID to focus on",
                ),
                ParameterSpec(
                    name="message",
                    type="str",
                    required=False,
                    description="Optional message to display",
                ),
            ],
            when_to_use="When starting deployment or build tasks to show progress tracking",
            tool_names=["environment_agent_tools", "github_agent_tools"],
        )
    )


def _register_ui_function_hooks(registry: HookRegistry) -> None:
    """Register hooks for UI utility functions."""
    registry.register(
        HookMetadata(
            name="issue_technical_user",
            hook_type="ui_function",
            description="Issues M2M technical user credentials",
            parameters=[
                ParameterSpec(
                    name="conversation_id",
                    type="str",
                    required=True,
                    description="Conversation technical ID",
                ),
                ParameterSpec(
                    name="env_url",
                    type="str",
                    required=True,
                    description="Environment URL",
                ),
            ],
            when_to_use="When user requests technical user credentials",
            tool_names=["environment_agent_tools", "setup_agent_tools"],
        )
    )


def register_all_hooks(registry: HookRegistry) -> None:
    """Register all available hooks in the registry.

    Coordinates registration of all hook categories in a single orchestration
    point, following the step-down rule for narrative flow.
    """
    _register_canvas_hooks(registry)
    _register_code_change_hooks(registry)
    _register_option_selection_hooks(registry)
    _register_cloud_window_hooks(registry)
    _register_background_task_hooks(registry)
    _register_tasks_panel_hooks(registry)
    _register_ui_function_hooks(registry)

