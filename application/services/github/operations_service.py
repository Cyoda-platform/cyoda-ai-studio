"""Service for GitHub repository operations.

This module provides a backward-compatible wrapper for the refactored operations_service package.
All functionality has been split into focused modules within operations_service/.
"""

# Re-export all public APIs from the package
from .operations_service import (
    GitHubOperationsService,
    extract_repository_name_from_url,
    determine_repository_path,
    verify_repository_exists,
    get_authenticated_clone_url,
    BUILDS_DIR,
)

# Maintain backward compatibility with underscore-prefixed names
_extract_repository_name_from_url = extract_repository_name_from_url
_determine_repository_path = determine_repository_path
_verify_repository_exists = verify_repository_exists
_get_authenticated_clone_url = get_authenticated_clone_url

__all__ = [
    "GitHubOperationsService",
    "extract_repository_name_from_url",
    "determine_repository_path",
    "verify_repository_exists",
    "get_authenticated_clone_url",
    "BUILDS_DIR",
]
