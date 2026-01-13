"""Directory scanning utilities for versioned resources.

This module provides utilities for scanning directories with versioned structure.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ....common.constants import VERSION_DIR_PREFIX
from .file_operations import find_json_file_in_directory, parse_json_file
from .resource_builders import create_resource_dict

logger = logging.getLogger(__name__)


def get_version_sort_key(version_dir: Path) -> int:
    """Extract version number for sorting.

    Args:
        version_dir: Version directory path

    Returns:
        Version number as integer (0 if parsing fails)
    """
    try:
        return int(version_dir.name.split("_")[1])
    except (IndexError, ValueError):
        return 0


def parse_direct_resource_file(
    file_path: Path, repo_path: Path, resource_type: str
) -> Optional[Dict[str, Any]]:
    """Parse a direct resource file (not versioned).

    Args:
        file_path: Path to resource file
        repo_path: Repository root path
        resource_type: Type of resource

    Returns:
        Resource dictionary or None if parsing fails
    """
    content = parse_json_file(file_path)
    if not content:
        return None

    resource_dict = create_resource_dict(
        name=file_path.stem,
        version=None,
        file_path=file_path,
        content=content,
        repo_path=repo_path,
        resource_type=resource_type,
    )

    logger.info(f"✅ Parsed {resource_type}: {file_path.stem} (direct file)")
    return resource_dict


def parse_versioned_resource(
    version_dir: Path,
    resource_name: str,
    repo_path: Path,
    resource_type: str,
) -> Optional[Dict[str, Any]]:
    """Parse a versioned resource from version directory.

    Args:
        version_dir: Version directory path
        resource_name: Name of the resource
        repo_path: Repository root path
        resource_type: Type of resource

    Returns:
        Resource dictionary or None if file not found
    """
    version_name = version_dir.name

    # Find JSON file in version directory
    resource_file = find_json_file_in_directory(version_dir, resource_name)

    if not resource_file:
        logger.warning(f"{resource_type.title()} file not found in {version_dir}")
        return None

    content = parse_json_file(resource_file)
    if not content:
        return None

    resource_dict = create_resource_dict(
        name=resource_name,
        version=version_name,
        file_path=resource_file,
        content=content,
        repo_path=repo_path,
        resource_type=resource_type,
    )

    logger.info(f"✅ Parsed {resource_type}: {resource_name} {version_name}")
    return resource_dict


def scan_versioned_directory(
    directory: Path, resource_name: str, repo_path: Path, resource_type: str
) -> List[Dict[str, Any]]:
    """Scan directory with versioned structure.

    Args:
        directory: Resource directory
        resource_name: Name of the resource
        repo_path: Repository root path
        resource_type: Type of resource

    Returns:
        List of resource dictionaries (one per version)
    """
    resources = []

    # Find version directories
    version_dirs = [
        d
        for d in directory.iterdir()
        if d.is_dir() and d.name.startswith(VERSION_DIR_PREFIX)
    ]

    if not version_dirs:
        return resources

    # Sort and scan each version
    for version_dir in sorted(version_dirs, key=get_version_sort_key):
        resource_dict = parse_versioned_resource(
            version_dir, resource_name, repo_path, resource_type
        )
        if resource_dict:
            resources.append(resource_dict)

    return resources


def scan_unversioned_directory(
    directory: Path, resource_name: str, repo_path: Path, resource_type: str
) -> Optional[Dict[str, Any]]:
    """Scan directory without version structure.

    Args:
        directory: Resource directory
        resource_name: Name of the resource
        repo_path: Repository root path
        resource_type: Type of resource

    Returns:
        Resource dictionary or None if file not found
    """
    # Find JSON file in directory
    direct_file = find_json_file_in_directory(directory, resource_name)

    if not direct_file:
        logger.warning(f"No {resource_type} files found in directory: {directory}")
        return None

    content = parse_json_file(direct_file)
    if not content:
        return None

    resource_dict = create_resource_dict(
        name=resource_name,
        version=None,
        file_path=direct_file,
        content=content,
        repo_path=repo_path,
        resource_type=resource_type,
    )

    logger.info(f"✅ Parsed {resource_type}: {resource_name} (directory file)")
    return resource_dict
