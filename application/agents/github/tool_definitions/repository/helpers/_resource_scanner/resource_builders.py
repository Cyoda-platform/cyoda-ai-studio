"""Resource dictionary builders for repository scanning.

This module provides utilities for building resource dictionaries with metadata.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ....common.constants import RESOURCE_TYPE_WORKFLOW

logger = logging.getLogger(__name__)


def extract_workflow_entity_name(content: dict) -> Optional[str]:
    """Extract entity name from workflow content.

    Args:
        content: Workflow JSON content

    Returns:
        Entity name if found, None otherwise
    """
    if not isinstance(content, dict):
        return None

    return content.get("entity_name") or content.get("entityName")


def create_resource_dict(
    name: str,
    version: Optional[str],
    file_path: Path,
    content: dict,
    repo_path: Path,
    resource_type: str,
) -> Dict[str, Any]:
    """Create resource dictionary with metadata.

    Args:
        name: Resource name
        version: Version string (or None for direct files)
        file_path: Path to resource file
        content: Parsed JSON content
        repo_path: Repository root path
        resource_type: Type of resource ("entity", "workflow", etc.)

    Returns:
        Resource dictionary with name, version, path, and content
    """
    resource_dict = {
        "name": name,
        "version": version,
        "path": str(file_path.relative_to(repo_path)),
        "content": content,
    }

    # Add entity_name for workflows
    if resource_type == RESOURCE_TYPE_WORKFLOW:
        entity_name = extract_workflow_entity_name(content)
        if entity_name:
            resource_dict["entity_name"] = entity_name
            logger.info(f"   - Workflow {name} associated with entity: {entity_name}")

    return resource_dict
