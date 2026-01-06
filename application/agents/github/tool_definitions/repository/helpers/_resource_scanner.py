"""Resource scanning utilities for repository analysis.

This module provides utilities for scanning versioned resources (entities, workflows, etc.)
in repository directories.
"""

from __future__ import annotations

from ._resource_scanner import (
    # Main scanner function
    scan_versioned_resources,
    # File operations
    find_json_file_in_directory as _find_json_file_in_directory,
    parse_json_file as _parse_json_file,
    # Resource builders
    extract_workflow_entity_name as _extract_workflow_entity_name,
    create_resource_dict as _create_resource_dict,
    # Directory scanner
    get_version_sort_key as _get_version_sort_key,
    parse_direct_resource_file as _parse_direct_resource_file,
    parse_versioned_resource as _parse_versioned_resource,
    scan_versioned_directory as _scan_versioned_directory,
    scan_unversioned_directory as _scan_unversioned_directory,
)

__all__ = ["scan_versioned_resources"]
