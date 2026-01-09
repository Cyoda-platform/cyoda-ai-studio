"""Resource scanning utilities for repository analysis.

This module provides utilities for scanning versioned resources (entities, workflows, etc.)
in repository directories.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from ....common.constants import EXT_JSON
from .directory_scanner import (
    get_version_sort_key,
    parse_direct_resource_file,
    parse_versioned_resource,
    scan_unversioned_directory,
    scan_versioned_directory,
)
from .file_operations import find_json_file_in_directory, parse_json_file
from .resource_builders import (
    create_resource_dict,
    extract_workflow_entity_name,
)

logger = logging.getLogger(__name__)


def scan_versioned_resources(
    resources_dir: Path, resource_type: str, repo_path_obj: Path
) -> List[Dict[str, Any]]:
    """Generic scanner for versioned resources (entities, workflows, etc.).

    This function automatically detects the structure and scans for:
    1. Direct files: resource_name.json
    2. Versioned directories: resource_name/version_N/resource_name.json

    Args:
        resources_dir: Path to the resource directory (e.g., .../entity, .../workflow)
        resource_type: Type of resource for logging ("entity", "workflow", etc.)
        repo_path_obj: Repository root path for relative path calculation

    Returns:
        List of resource dictionaries with name, version, path, and content
    """
    resources = []

    if not resources_dir.exists():
        logger.info(f"📁 {resource_type.title()} directory not found: {resources_dir}")
        return resources

    logger.info(f"📁 Scanning {resource_type} directory: {resources_dir}")

    for item in sorted(resources_dir.iterdir()):
        # Skip hidden/private directories
        if item.name.startswith("_"):
            continue

        # Handle direct JSON files
        if item.is_file() and item.suffix == EXT_JSON:
            resource_dict = parse_direct_resource_file(
                item, repo_path_obj, resource_type
            )
            if resource_dict:
                resources.append(resource_dict)

        # Handle directories
        elif item.is_dir():
            resource_name = item.name
            logger.info(f"🔍 Found {resource_type} directory: {resource_name}")

            # Check for versioned structure
            versioned_resources = scan_versioned_directory(
                item, resource_name, repo_path_obj, resource_type
            )

            if versioned_resources:
                resources.extend(versioned_resources)
            else:
                # Try unversioned directory structure
                unversioned_resource = scan_unversioned_directory(
                    item, resource_name, repo_path_obj, resource_type
                )
                if unversioned_resource:
                    resources.append(unversioned_resource)

    return resources


__all__ = [
    # Main scanner function
    "scan_versioned_resources",
    # File operations
    "find_json_file_in_directory",
    "parse_json_file",
    # Resource builders
    "extract_workflow_entity_name",
    "create_resource_dict",
    # Directory scanner
    "get_version_sort_key",
    "parse_direct_resource_file",
    "parse_versioned_resource",
    "scan_versioned_directory",
    "scan_unversioned_directory",
]
