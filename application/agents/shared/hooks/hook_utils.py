"""
Hook Utilities for Agent-UI Communication

Provides standardized hook responses for UI integration.
Hooks enable the UI to react to agent actions (code changes, background tasks, etc.)

## 🎯 UI Hook Pattern: open_canvas_tab

The `open_canvas_tab` hook is used to open a specific canvas tab in the UI. The key principle is:

**DO NOT ASK THE USER IF THEY WANT TO OPEN THE TAB**

Instead, directly return the hook. The UI will render it as a clickable button that the user can click.

### ❌ WRONG Pattern (Don't do this):
```
Agent: "I've created the Customer entity. Would you like me to open the Entities
tab so you can view it? (I can open it for you)"
```

### ✅ CORRECT Pattern (Do this):
```
Agent: "✅ Customer entity created and saved!

📊 The entity is now on your canvas with fields: id, name, email, created_at

[Open Entities Tab] ← This button is rendered by the UI from the hook
```

The hook is returned in the response, and the UI automatically renders it as a button.

### How it works:
1. Agent generates/saves a resource (entity, workflow, requirement)
2. Agent returns `create_open_canvas_tab_hook()` in the response
3. UI receives the hook and renders it as a clickable button
4. User clicks the button to open the canvas tab
5. No need for agent to ask permission - the hook IS the permission

### Example Usage in Agent Code:
```python
from .hook_utils import create_open_canvas_tab_hook

# After saving an entity
hook = create_open_canvas_tab_hook(
    conversation_id=conversation_id,
    tab_name="entities",
    message="Open Canvas to view your entities"
)

# Return hook in response (UI will render as button)
return {
    "message": "✅ Customer entity created and saved!",
    "hook": hook
}
```

### Valid tab_name values:
- "entities" - Opens Canvas Entities tab
- "workflows" - Opens Canvas Workflows tab
- "requirements" - Opens Canvas Requirements tab
- "cloud" - Opens Cloud/Environments tab

### Key Principles:
1. **No Permission Asking**: Don't ask "would you like me to open...?"
2. **Direct Hook Return**: Return the hook directly in your response
3. **UI Renders Button**: The UI automatically renders the hook as a clickable button
4. **User Controls**: User decides whether to click the button
5. **Clean UX**: One hook per action, no duplicate hooks
"""

# Re-export all hooks for backward compatibility
from .canvas_hooks import (
    create_code_changes_hook,
    create_canvas_open_hook,
    create_open_canvas_tab_hook,
    detect_canvas_resources,
)
from .cloud_hooks import (
    create_cloud_window_hook,
    _create_cloud_window_hook,
)
from .deployment_hooks import (
    create_deployment_hook,
    _create_deployment_options_hook,
    create_deploy_and_open_cloud_hook,
    create_deploy_cyoda_environment_hook,
)
from .utilities import (
    create_background_task_hook,
    create_proceed_button_hook,
    create_canvas_with_proceed_hook,
    create_resource_links_hook,
    _create_branch_choice_options,
    _create_repository_type_options,
    _create_language_options,
    _build_repository_config_options,
    create_repository_config_selection_hook,
    create_option_selection_hook,
    create_combined_hook,
    wrap_response_with_hook,
    create_launch_setup_assistant_hook,
    create_build_and_deploy_hooks,
    create_open_tasks_panel_hook,
    create_issue_technical_user_hook,
)

__all__ = [
    # Canvas hooks
    "create_code_changes_hook",
    "create_canvas_open_hook",
    "create_open_canvas_tab_hook",
    "detect_canvas_resources",
    # Cloud hooks
    "create_cloud_window_hook",
    "_create_cloud_window_hook",
    # Deployment hooks
    "create_deployment_hook",
    "_create_deployment_options_hook",
    "create_deploy_and_open_cloud_hook",
    "create_deploy_cyoda_environment_hook",
    # Utilities
    "create_background_task_hook",
    "create_proceed_button_hook",
    "create_canvas_with_proceed_hook",
    "create_resource_links_hook",
    "_create_branch_choice_options",
    "_create_repository_type_options",
    "_create_language_options",
    "_build_repository_config_options",
    "create_repository_config_selection_hook",
    "create_option_selection_hook",
    "create_combined_hook",
    "wrap_response_with_hook",
    "create_launch_setup_assistant_hook",
    "create_build_and_deploy_hooks",
    "create_open_tasks_panel_hook",
    "create_issue_technical_user_hook",
]
