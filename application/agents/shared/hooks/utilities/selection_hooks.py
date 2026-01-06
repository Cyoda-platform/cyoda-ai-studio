"""Selection and configuration hook utilities.

This module contains hook functions for:
- Option selection UI
- Repository configuration
- Resource links
- Technical user credentials
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _create_branch_choice_options() -> Dict[str, Any]:
    """Create branch choice options for repository setup.

    Returns:
        Branch choice option dictionary
    """
    return {
        "label": "Branch",
        "choices": [
            {
                "value": "new_branch",
                "label": "Create New Branch",
                "description": "Start fresh with a new branch"
            },
            {
                "value": "existing_branch",
                "label": "Use Existing Branch",
                "description": "Continue on existing branch"
            }
        ],
        "default": "new_branch"
    }


def _create_repository_type_options() -> Dict[str, Any]:
    """Create repository type options for repository setup.

    Returns:
        Repository type option dictionary
    """
    return {
        "label": "Repository Type",
        "choices": [
            {
                "value": "public",
                "label": "Public",
                "description": "Visible to everyone"
            },
            {
                "value": "private",
                "label": "Private",
                "description": "Only visible to you"
            }
        ],
        "default": "public"
    }


def _create_language_options() -> Dict[str, Any]:
    """Create programming language options for repository setup.

    Returns:
        Language option dictionary
    """
    return {
        "label": "Programming Language",
        "choices": [
            {
                "value": "python",
                "label": "Python",
                "description": "Python-based application"
            },
            {
                "value": "java",
                "label": "Java",
                "description": "Java-based application"
            }
        ],
        "default": "python"
    }


def _build_repository_config_options() -> Dict[str, Any]:
    """Build all repository configuration options.

    Returns:
        Complete options dictionary
    """
    return {
        "branch_choice": _create_branch_choice_options(),
        "repository_type": _create_repository_type_options(),
        "language": _create_language_options(),
    }


def create_repository_config_selection_hook(
    conversation_id: str,
    question: str = "Let's start by setting up the repository for your application.",
) -> Dict[str, Any]:
    """Create a comprehensive hook for complete repository setup with all options.

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
            "options": _build_repository_config_options(),
        }
    }

    logger.info(
        f"🎣 Created repository_config_selection hook for conversation {conversation_id}"
    )
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
    # Validate required parameters
    if not conversation_id:
        raise ValueError("conversation_id parameter is required and cannot be empty")
    if not question:
        raise ValueError("question parameter is required and cannot be empty")

    # Validate options
    if not options or len(options) == 0:
        raise ValueError("At least one option must be provided")

    for i, option in enumerate(options):
        if "value" not in option:
            raise ValueError(f"Option at index {i} is missing required 'value' field")
        if "label" not in option:
            raise ValueError(f"Option at index {i} is missing required 'label' field")

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
