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
Agent: "I've created the Customer entity. Would you like me to open the Entities tab so you can view it? (I can open it for you)"
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
from application.agents.shared.hook_utils import create_open_canvas_tab_hook

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

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def create_code_changes_hook(
    conversation_id: str,
    repository_name: str,
    branch_name: str,
    changed_files: List[str],
    commit_message: Optional[str] = None,
    resources: Optional[Dict[str, List[str]]] = None,
    resource_type: Optional[str] = None,
    repository_owner: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook for code changes that triggers canvas refresh in UI.

    When this hook is returned, the UI should:
    1. Open canvas automatically
    2. Switch to the appropriate tab based on resource_type
    3. Refresh canvas to show new/updated resources

    Args:
        conversation_id: Conversation technical ID
        repository_name: Repository name
        branch_name: Branch name
        changed_files: List of changed file paths
        commit_message: Optional commit message
        resources: Optional dict of resource types (entities, workflows, etc.)
        resource_type: Optional resource type ("entity", "workflow", "requirement")
                      If not provided, will be auto-detected from resources
        repository_owner: Optional repository owner (GitHub username/org)

    Returns:
        Hook dictionary with type "code_changes"
    """
    # Auto-detect resource_type from resources if not provided
    detected_type = resource_type
    if not detected_type and resources:
        if resources.get("entities"):
            detected_type = "entity"
        elif resources.get("workflows"):
            detected_type = "workflow"
        elif resources.get("requirements"):
            detected_type = "requirement"

    hook = {
        "type": "code_changes",
        "action": "refresh_canvas",
        "data": {
            "conversation_id": conversation_id,
            "repository_name": repository_name,
            "branch_name": branch_name,
            "changed_files": changed_files[:20],  # Limit to first 20 files
        }
    }

    if repository_owner:
        hook["data"]["repository_owner"] = repository_owner

    if commit_message:
        hook["data"]["commit_message"] = commit_message

    if resources:
        hook["data"]["resources"] = resources

    if detected_type:
        hook["data"]["resource_type"] = detected_type

    logger.info(f"🎣 Created code_changes hook for conversation {conversation_id} with resource_type={detected_type}")
    return hook


def create_background_task_hook(
    task_id: str,
    task_type: str,
    task_name: str,
    task_description: str,
    conversation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a hook for background task launch.
    
    When this hook is returned, the UI should:
    1. Show task notification with description
    2. Show "View Tasks" button that opens entities window
    3. Track task progress
    
    Args:
        task_id: Background task technical ID
        task_type: Type of task (code_generation, application_build, etc.)
        task_name: Display name for task
        task_description: Task description
        conversation_id: Optional conversation ID
        metadata: Optional additional metadata
    
    Returns:
        Hook dictionary with type "background_task"
    """
    hook = {
        "type": "background_task",
        "action": "show_task_notification",
        "data": {
            "task_id": task_id,
            "task_type": task_type,
            "task_name": task_name,
            "task_description": task_description,
        }
    }
    
    if conversation_id:
        hook["data"]["conversation_id"] = conversation_id
    
    if metadata:
        hook["data"]["metadata"] = metadata
    
    # Also include background_task_ids for backward compatibility
    hook["background_task_ids"] = [task_id]
    
    logger.info(f"🎣 Created background_task hook for task {task_id}")
    return hook


def create_canvas_open_hook(
    conversation_id: str,
    repository_name: str,
    branch_name: str,
    repository_url: str,
) -> Dict[str, Any]:
    """
    Create a hook for opening Canvas after repository configuration.

    When this hook is returned, the UI should:
    1. Show "Open Canvas" button to user
    2. When clicked, open the Canvas panel
    3. Optionally trigger repository analysis to populate Canvas

    Args:
        conversation_id: Conversation technical ID
        repository_name: Repository name (owner/repo)
        branch_name: Branch name
        repository_url: Full GitHub URL to the branch

    Returns:
        Hook dictionary with type "canvas_open"
    """
    hook = {
        "type": "canvas_open",
        "action": "suggest_canvas",
        "data": {
            "conversation_id": conversation_id,
            "repository_name": repository_name,
            "branch_name": branch_name,
            "repository_url": repository_url,
            "message": "Repository configured! Open Canvas to design your requirements, entities, and workflows visually."
        }
    }

    logger.info(f"🎣 Created canvas_open hook for conversation {conversation_id}")
    return hook


def create_proceed_button_hook(
    conversation_id: str,
    question: str = "Ready to proceed?",
) -> Dict[str, Any]:
    """
    Create a hook for a simple "Proceed" button confirmation.

    When this hook is returned, the UI should:
    1. Show a "Proceed" button to the user
    2. When clicked, send "Proceed" as a message back to the agent

    Args:
        conversation_id: Conversation technical ID
        question: Question to display to the user

    Returns:
        Hook dictionary with type "option_selection"
    """
    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": question,
            "options": [
                {
                    "value": "proceed",
                    "label": "Proceed",
                    "description": "Click to continue"
                }
            ],
            "selection_type": "single"
        }
    }

    logger.info(f"🎣 Created proceed button hook for conversation {conversation_id}")
    return hook


def create_canvas_with_proceed_hook(
    conversation_id: str,
    repository_name: str,
    branch_name: str,
    repository_url: str,
    question: str = "Ready to proceed?",
) -> Dict[str, Any]:
    """
    DEPRECATED: This function is kept for backward compatibility only.

    Use create_proceed_button_hook() instead for a simple proceed button.
    Use create_open_canvas_tab_hook() separately if you need to open canvas.

    The agent should dynamically decide whether to use open_canvas_tab hook
    based on the context and user needs.

    Args:
        conversation_id: Conversation technical ID
        repository_name: Repository name (owner/repo) - IGNORED
        branch_name: Branch name - IGNORED
        repository_url: Full GitHub URL to the branch - IGNORED
        question: Question to display with the proceed button

    Returns:
        Hook dictionary with option_selection (proceed button only)
    """
    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": question,
            "options": [
                {
                    "value": "proceed",
                    "label": "Proceed",
                    "description": "Click to continue"
                }
            ],
            "selection_type": "single"
        }
    }

    logger.info(f"🎣 Created proceed button hook for conversation {conversation_id} (canvas_with_proceed deprecated)")
    return hook


def create_resource_links_hook(
    conversation_id: str,
) -> Dict[str, Any]:
    """
    Create a hook for displaying Cyoda resource links.

    When this hook is returned, the UI should:
    1. Show clickable links to Cyoda resources
    2. Links include: GitHub, Docs, API Reference, Discord

    Args:
        conversation_id: Conversation technical ID

    Returns:
        Hook dictionary with type "resource_links"
    """
    hook = {
        "type": "resource_links",
        "action": "show_resources",
        "data": {
            "conversation_id": conversation_id,
            "resources": [
                {
                    "title": "GitHub Repository",
                    "description": "Visit Cyoda on GitHub",
                    "url": "https://github.com/Cyoda-platform",
                    "icon": "github"
                },
                {
                    "title": "Documentation",
                    "description": "Read Cyoda documentation",
                    "url": "https://docs.cyoda.net/",
                    "icon": "book"
                },
                {
                    "title": "API Reference",
                    "description": "Explore the Cyoda API",
                    "url": "https://docs.cyoda.net/api-reference/",
                    "icon": "code"
                },
                {
                    "title": "Discord Community",
                    "description": "Join us on Discord - let's chat!",
                    "url": "https://discord.com/invite/95rdAyBZr2",
                    "icon": "discord"
                }
            ]
        }
    }

    logger.info(f"🎣 Created resource_links hook for conversation {conversation_id}")
    return hook


def create_repository_config_selection_hook(
    conversation_id: str,
    question: str = "Let's start by setting up the repository for your application.",
) -> Dict[str, Any]:
    """
    Create a comprehensive hook for complete repository setup with all options.

    When this hook is returned, the UI should display:
    1. Branch choice (New vs Existing)
    2. Repository type (Public vs Private)
    3. Programming language (Python vs Java)
    4. All in a single form with a "Continue" button

    Args:
        conversation_id: Conversation technical ID
        question: Question text to display (optional)

    Returns:
        Hook dictionary with type "repository_config_selection"
    """
    hook = {
        "type": "repository_config_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": question,
            "options": {
                "branch_choice": {
                    "label": "Branch",
                    "choices": [
                        {"value": "new_branch", "label": "Create New Branch", "description": "Start fresh with a new branch"},
                        {"value": "existing_branch", "label": "Use Existing Branch", "description": "Continue on existing branch"}
                    ],
                    "default": "new_branch"
                },
                "repository_type": {
                    "label": "Repository Type",
                    "choices": [
                        {"value": "public", "label": "Public", "description": "Visible to everyone"},
                        {"value": "private", "label": "Private", "description": "Only visible to you"}
                    ],
                    "default": "public"
                },
                "language": {
                    "label": "Programming Language",
                    "choices": [
                        {"value": "python", "label": "Python", "description": "Python-based application"},
                        {"value": "java", "label": "Java", "description": "Java-based application"}
                    ],
                    "default": "python"
                }
            }
        }
    }

    logger.info(f"🎣 Created repository_config_selection hook for conversation {conversation_id}")
    return hook


def create_cloud_window_hook(
    conversation_id: str,
    environment_url: Optional[str] = None,
    environment_status: Optional[str] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook for opening the Cloud/Environments window in the UI.

    When this hook is returned, the UI should:
    1. Open the Cloud/Environments panel (left sidebar)
    2. Highlight the user's environment if it exists
    3. Show environment status and details

    Args:
        conversation_id: Conversation technical ID
        environment_url: Optional environment URL (e.g., "https://client-user.cyoda.cloud")
        environment_status: Optional environment status (e.g., "deployed", "pending", "failed")
        message: Optional message to display to user

    Returns:
        Hook dictionary with type "cloud_window"
    """
    hook = {
        "type": "cloud_window",
        "action": "open_environments_panel",
        "data": {
            "conversation_id": conversation_id,
        }
    }

    if environment_url:
        hook["data"]["environment_url"] = environment_url

    if environment_status:
        hook["data"]["environment_status"] = environment_status

    if message:
        hook["data"]["message"] = message
    else:
        hook["data"]["message"] = "View your Cyoda environment details in the Cloud panel."

    logger.info(f"🎣 Created cloud_window hook for conversation {conversation_id}")
    return hook


def create_open_canvas_tab_hook(
    conversation_id: str,
    tab_name: str,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook for opening a specific canvas tab in the UI.

    🎯 KEY PRINCIPLE: Do NOT ask the user if they want to open the tab.
    Simply return this hook - the UI will render it as a clickable button.

    When this hook is returned, the UI will:
    1. Render a clickable button with the message text
    2. When user clicks the button, open the Canvas panel
    3. Navigate to the specified tab
    4. Display the resource on canvas

    ❌ WRONG: "Would you like me to open the Entities tab? (I can open it for you)"
    ✅ RIGHT: Return this hook directly - UI renders as button

    Args:
        conversation_id: Conversation technical ID
        tab_name: Name of the canvas tab to open. Valid values:
            - "entities" - Opens Canvas Entities tab
            - "workflows" - Opens Canvas Workflows tab
            - "requirements" - Opens Canvas Requirements tab
            - "cloud" - Opens Cloud/Environments tab
        message: Optional message to display on the button.
                If not provided, a default message is used based on tab_name.
                This message is what the user sees on the clickable button.

    Returns:
        Hook dictionary with type "canvas_tab"

    Raises:
        ValueError: If tab_name is not one of the valid options

    Example - After creating an entity:
        >>> hook = create_open_canvas_tab_hook(
        ...     conversation_id="conv-123",
        ...     tab_name="entities",
        ...     message="View Customer Entity"  # This becomes the button text
        ... )
        >>> # Return in agent response:
        >>> return {
        ...     "message": "✅ Customer entity created and saved!",
        ...     "hook": hook
        ... }
        >>> # UI renders: [View Customer Entity] button
    """
    valid_tabs = ["entities", "workflows", "requirements", "cloud"]

    if tab_name not in valid_tabs:
        raise ValueError(
            f"Invalid tab_name '{tab_name}'. Must be one of: {', '.join(valid_tabs)}"
        )

    hook = {
        "type": "canvas_tab",
        "action": "open_canvas_tab",
        "data": {
            "conversation_id": conversation_id,
            "tab_name": tab_name,
        }
    }

    if message:
        hook["data"]["message"] = message
    else:
        # Default messages for each tab
        default_messages = {
            "entities": "Open Canvas to view and manage your entities.",
            "workflows": "Open Canvas to view and manage your workflows.",
            "requirements": "Open Canvas to view and manage your requirements.",
            "cloud": "Open Cloud tab to view your environment details.",
        }
        hook["data"]["message"] = default_messages.get(tab_name, "Open Canvas")

    logger.info(f"🎣 Created canvas_tab hook for conversation {conversation_id}, tab: {tab_name}")
    return hook


def create_option_selection_hook(
    conversation_id: str,
    question: str,
    options: list[Dict[str, str]],
    selection_type: str = "single",
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a generic hook for option selection with interactive UI.

    This hook can be used by any agent when they need to ask the user to select from a list of options.
    The UI will display the options as clickable buttons or checkboxes.

    Args:
        conversation_id: Conversation technical ID
        question: Question text to display
        options: List of option dictionaries, each with:
            - value: The value to return when selected (required)
            - label: Display text for the option (required)
            - description: Optional description text (optional)
            - icon: Optional icon name (optional)
        selection_type: Either "single" (radio buttons) or "multiple" (checkboxes)
        context: Optional context or additional information to display

    Returns:
        Hook dictionary with type "option_selection"

    Example:
        hook = create_option_selection_hook(
            conversation_id="123",
            question="Would you like to create a new branch or use an existing one?",
            options=[
                {
                    "value": "new_branch",
                    "label": "Create a new branch",
                    "description": "Start fresh with a new branch for your application"
                },
                {
                    "value": "existing_branch",
                    "label": "Use an existing branch",
                    "description": "Continue working on a branch you've already created"
                }
            ],
            selection_type="single"
        )
    """
    # Validate options
    if not options or len(options) == 0:
        raise ValueError("At least one option must be provided")

    for option in options:
        if "value" not in option or "label" not in option:
            raise ValueError("Each option must have 'value' and 'label' fields")

    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": question,
            "options": options,
            "selection_type": selection_type,
            "context": context,
        }
    }

    logger.info(f"🎣 Created option_selection hook for conversation {conversation_id} with {len(options)} options")
    return hook


def create_deployment_hook(
    conversation_id: str,
    environment_name: Optional[str] = None,
    environment_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook for deployment options after application build completes.

    When this hook is returned, the UI should:
    1. Show deployment options (Deploy, Redeploy, Check Status)
    2. Display warning about data cleanup on redeploy
    3. Send user's choice back to the agent

    Args:
        conversation_id: Conversation technical ID
        environment_name: Optional environment name
        environment_url: Optional environment URL

    Returns:
        Hook dictionary with type "option_selection"
    """
    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": "Your application build is complete! What would you like to do?",
            "options": [
                {
                    "value": "deploy",
                    "label": "🚀 Deploy Environment",
                    "description": "Deploy your application to a new Cyoda environment"
                },
                {
                    "value": "redeploy",
                    "label": "🔄 Redeploy Environment",
                    "description": "Redeploy to existing environment (⚠️ data will be cleaned up)"
                },
                {
                    "value": "check_status",
                    "label": "📊 Check Environment Status",
                    "description": "View current environment status and details"
                }
            ],
            "selection_type": "single"
        }
    }

    if environment_name:
        hook["data"]["environment_name"] = environment_name

    if environment_url:
        hook["data"]["environment_url"] = environment_url

    logger.info(f"🎣 Created deployment_options hook for conversation {conversation_id}")
    return hook


def create_deploy_and_open_cloud_hook(
    conversation_id: str,
    environment_name: Optional[str] = None,
    environment_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a combined hook that opens cloud tab and shows deployment options.

    When this hook is returned, the UI should:
    1. Open the Cloud/Environments panel
    2. Show deployment options (Deploy, Redeploy, Check Status)
    3. Allow user to deploy directly from the cloud panel

    Args:
        conversation_id: Conversation technical ID
        environment_name: Optional environment name
        environment_url: Optional environment URL

    Returns:
        Hook dictionary with type "combined" containing cloud_window and deployment hooks
    """
    # Create cloud window hook to open deployment panel
    cloud_hook = {
        "type": "cloud_window",
        "action": "open_environments_panel",
        "data": {
            "conversation_id": conversation_id,
            "message": "🚀 Build complete! Deploy your application to a Cyoda environment.",
        }
    }

    if environment_url:
        cloud_hook["data"]["environment_url"] = environment_url

    if environment_name:
        cloud_hook["data"]["environment_name"] = environment_name

    # Create deployment options hook
    deployment_hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": "Your application build is complete! What would you like to do?",
            "options": [
                {
                    "value": "deploy",
                    "label": "🚀 Deploy Environment",
                    "description": "Deploy your application to a new Cyoda environment"
                },
                {
                    "value": "redeploy",
                    "label": "🔄 Redeploy Environment",
                    "description": "Redeploy to existing environment (⚠️ data will be cleaned up)"
                },
                {
                    "value": "check_status",
                    "label": "📊 Check Environment Status",
                    "description": "View current environment status and details"
                }
            ],
            "selection_type": "single"
        }
    }

    # Combine both hooks
    combined = {
        "type": "combined",
        "hooks": [cloud_hook, deployment_hook]
    }

    logger.info(f"🎣 Created deploy_and_open_cloud hook for conversation {conversation_id}")
    return combined


def create_combined_hook(
    code_changes_hook: Optional[Dict[str, Any]] = None,
    background_task_hook: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Combine multiple hooks into a single hook response.
    
    This is useful when an action triggers both code changes and background tasks.
    
    Args:
        code_changes_hook: Optional code changes hook
        background_task_hook: Optional background task hook
    
    Returns:
        Combined hook dictionary
    """
    combined = {
        "type": "combined",
        "hooks": []
    }
    
    if code_changes_hook:
        combined["hooks"].append(code_changes_hook)
    
    if background_task_hook:
        combined["hooks"].append(background_task_hook)
        # Preserve background_task_ids for backward compatibility
        if "background_task_ids" in background_task_hook:
            combined["background_task_ids"] = background_task_hook["background_task_ids"]
    
    logger.info(f"🎣 Created combined hook with {len(combined['hooks'])} hooks")
    return combined


def wrap_response_with_hook(
    message: str,
    hook: Dict[str, Any],
) -> str:
    """
    Wrap a response message with a hook for UI integration.
    
    The hook is stored in tool_context.state["last_tool_hook"] and will be
    included in the SSE done event by StreamingService.
    
    Args:
        message: Response message to display to user
        hook: Hook dictionary
    
    Returns:
        JSON string with message and hook
    """
    response = {
        "message": message,
        "hook": hook
    }
    
    return json.dumps(response, indent=2)


def create_deploy_cyoda_environment_hook(
    conversation_id: str,
    task_id: Optional[str] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook to deploy Cyoda environment while application build is running.

    When this hook is returned, the UI should:
    1. Show "Deploy Cyoda Environment" button/option
    2. Allow user to start environment deployment in parallel with build
    3. Track deployment progress separately from build progress

    Args:
        conversation_id: Conversation technical ID
        task_id: Optional background task ID for deployment tracking
        message: Optional custom message

    Returns:
        Hook dictionary with type "option_selection" for deployment
    """
    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": "While the build is running, would you like to deploy the Cyoda environment?",
            "options": [
                {
                    "value": "deploy_environment",
                    "label": "🌐 Deploy Cyoda Environment",
                    "description": "Start deploying the environment now (runs in parallel with build)"
                },
                {
                    "value": "skip_deployment",
                    "label": "⏭️ Skip for Now",
                    "description": "Deploy after the build completes"
                }
            ],
            "selection_type": "single"
        }
    }

    if task_id:
        hook["data"]["task_id"] = task_id

    if message:
        hook["data"]["message"] = message

    logger.info(f"🎣 Created deploy_cyoda_environment hook for conversation {conversation_id}")
    return hook


def create_launch_setup_assistant_hook(
    conversation_id: str,
    task_id: Optional[str] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook to launch setup assistant for application configuration.

    When this hook is returned, the UI should:
    1. Show "Launch Setup Assistant" button/option
    2. Open interactive setup wizard for application configuration
    3. Guide user through environment variables, API keys, database setup, etc.

    Args:
        conversation_id: Conversation technical ID
        task_id: Optional background task ID for setup tracking
        message: Optional custom message

    Returns:
        Hook dictionary with type "option_selection" for setup assistant
    """
    hook = {
        "type": "option_selection",
        "action": "show_selection_ui",
        "data": {
            "conversation_id": conversation_id,
            "question": "Would you like to launch the Setup Assistant to configure your application?",
            "options": [
                {
                    "value": "launch_setup_assistant",
                    "label": "🛠️ Launch Setup Assistant",
                    "description": "Interactive wizard to configure environment, API keys, and services"
                },
                {
                    "value": "skip_setup_assistant",
                    "label": "⏭️ Skip Setup",
                    "description": "Configure manually later"
                }
            ],
            "selection_type": "single"
        }
    }

    if task_id:
        hook["data"]["task_id"] = task_id

    if message:
        hook["data"]["message"] = message

    logger.info(f"🎣 Created launch_setup_assistant hook for conversation {conversation_id}")
    return hook


def create_build_and_deploy_hooks(
    conversation_id: str,
    build_task_id: str,
    deploy_task_id: Optional[str] = None,
    setup_task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create combined hooks for build start with deployment and setup options.

    When this hook is returned, the UI should:
    1. Show deployment environment option
    2. Show setup assistant option
    3. Allow user to start both in parallel with build

    Args:
        conversation_id: Conversation technical ID
        build_task_id: Background task ID for build
        deploy_task_id: Optional background task ID for deployment
        setup_task_id: Optional background task ID for setup

    Returns:
        Combined hook dictionary with deployment and setup options
    """
    combined = {
        "type": "combined",
        "hooks": [
            create_deploy_cyoda_environment_hook(conversation_id, deploy_task_id),
            create_launch_setup_assistant_hook(conversation_id, setup_task_id)
        ],
        "data": {
            "build_task_id": build_task_id,
            "context": "Application build started - configure environment while build runs"
        }
    }

    logger.info(f"🎣 Created build_and_deploy_hooks for conversation {conversation_id}")
    return combined


def create_open_tasks_panel_hook(
    conversation_id: str,
    task_id: Optional[str] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a hook to open the Tasks panel for tracking deployment/build progress.

    When this hook is returned, the UI should:
    1. Open the Tasks panel on the right side
    2. Show task progress and status
    3. Optionally focus on a specific task if task_id is provided

    Args:
        conversation_id: Conversation technical ID
        task_id: Optional task ID to focus on
        message: Optional message to display

    Returns:
        Hook dictionary with type "tasks_panel"
    """
    hook = {
        "type": "tasks_panel",
        "action": "open_tasks_panel",
        "data": {
            "conversation_id": conversation_id,
        }
    }

    if task_id:
        hook["data"]["task_id"] = task_id

    if message:
        hook["data"]["message"] = message

    logger.info(f"🎣 Created open_tasks_panel hook for conversation {conversation_id}")
    return hook


def create_issue_technical_user_hook(
    conversation_id: str,
    env_url: str,
) -> Dict[str, Any]:
    """
    Create a hook for issuing M2M (machine-to-machine) technical user credentials.

    When this hook is returned, the UI should:
    1. Display a button to issue technical user credentials
    2. Make a POST request to /api/clients on the specified environment
    3. Return CYODA_CLIENT_ID and CYODA_CLIENT_SECRET for OAuth2 authentication

    Args:
        conversation_id: Conversation technical ID
        env_url: Environment URL (e.g., 'client-user-env.cyoda.cloud')

    Returns:
        Hook dictionary with type "ui_function" for issuing credentials
    """
    hook = {
        "type": "ui_function",
        "function": "issue_technical_user",
        "method": "POST",
        "path": "/api/clients",
        "response_format": "json",
        "data": {
            "conversation_id": conversation_id,
            "env_url": env_url,
        }
    }

    logger.info(f"🎣 Created issue_technical_user hook for environment {env_url}")
    return hook


def detect_canvas_resources(changed_files: List[str]) -> Optional[Dict[str, List[str]]]:
    """
    Detect canvas-relevant resources from changed files.

    Args:
        changed_files: List of changed file paths

    Returns:
        Dictionary of resource types or None if no canvas resources detected
    """
    resources = {
        "entities": [],
        "workflows": [],
        "requirements": [],
        "processors": [],
        "routes": [],
    }

    for file_path in changed_files:
        file_lower = file_path.lower()

        # Detect entities
        if "/entity/" in file_lower or file_lower.endswith(".py") and "entity" in file_lower:
            resources["entities"].append(file_path)

        # Detect workflows
        elif "/workflow/" in file_lower or file_lower.endswith(".json") and "workflow" in file_lower:
            resources["workflows"].append(file_path)

        # Detect requirements
        elif "requirement" in file_lower and file_lower.endswith((".txt", ".md", ".json")):
            resources["requirements"].append(file_path)

        # Detect processors
        elif "/processor/" in file_lower or "processor" in file_lower:
            resources["processors"].append(file_path)

        # Detect routes
        elif "/route" in file_lower or "route" in file_lower:
            resources["routes"].append(file_path)

    # Check if any canvas resources were detected
    has_resources = any(len(files) > 0 for files in resources.values())

    if has_resources:
        logger.info(f"🎨 Detected canvas resources: {sum(len(files) for files in resources.values())} files")
        return resources

    return None

