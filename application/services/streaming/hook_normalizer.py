"""Hook normalization to fix serialization issues."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def normalize_hook(hook: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize hook structure to fix serialization issues.

    Cyoda's JSON serialization sometimes wraps dict values in lists.
    This function fixes the repository_config_selection hook by unwrapping
    the options field if it was incorrectly wrapped in a list.

    Args:
        hook: Hook dictionary to normalize

    Returns:
        Normalized hook dictionary
    """
    if not isinstance(hook, dict):
        return hook

    if hook.get("type") != "repository_config_selection":
        return hook

    if "data" not in hook or not isinstance(hook["data"], dict):
        return hook

    options = hook["data"].get("options")
    if not isinstance(options, list) or len(options) != 1:
        return hook

    if not isinstance(options[0], dict):
        return hook

    logger.info("🎣 Normalizing hook: unwrapping options from list to dict")
    return {
        **hook,
        "data": {
            **hook["data"],
            "options": options[0]
        }
    }

