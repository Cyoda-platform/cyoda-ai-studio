"""Canvas-related hooks for UI integration."""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def create_code_changes_hook(
    conversation_id: str,
    repository_name: str,
    branch_name: str,
    changed_files: list[str],
    commit_message: Optional[str] = None,
    resources: Optional[Dict[str, list[str]]] = None,
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
            "message": (
                "Repository configured! Open Canvas to design your "
                "requirements, entities, and workflows visually."
            )
        }
    }

    logger.info(f"🎣 Created canvas_open hook for conversation {conversation_id}")
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


def detect_canvas_resources(changed_files: list[str]) -> Optional[Dict[str, list[str]]]:
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
