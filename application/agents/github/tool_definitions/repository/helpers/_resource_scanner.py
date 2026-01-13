"""Resource scanning utilities for repository analysis.

This module provides utilities for scanning versioned resources (entities, workflows, etc.)
in repository directories.
"""

from __future__ import annotations

from ._resource_scanner import create_resource_dict as _create_resource_dict
from ._resource_scanner import (
    extract_workflow_entity_name as _extract_workflow_entity_name,
)
from ._resource_scanner import (
    find_json_file_in_directory as _find_json_file_in_directory,  # Main scanner function; File operations; Resource builders; Directory scanner
)
from ._resource_scanner import get_version_sort_key as _get_version_sort_key
from ._resource_scanner import parse_direct_resource_file as _parse_direct_resource_file
from ._resource_scanner import parse_json_file as _parse_json_file
from ._resource_scanner import parse_versioned_resource as _parse_versioned_resource
from ._resource_scanner import scan_unversioned_directory as _scan_unversioned_directory
from ._resource_scanner import scan_versioned_directory as _scan_versioned_directory
from ._resource_scanner import (
    scan_versioned_resources,
)

__all__ = ["scan_versioned_resources"]
