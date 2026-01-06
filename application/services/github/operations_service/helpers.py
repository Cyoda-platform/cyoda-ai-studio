"""Helper functions for GitHub operations."""

import logging
import re
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Constants
BUILDS_DIR = Path("/tmp/cyoda_builds")


def extract_repository_name_from_url(repository_url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract repository name from GitHub URL.

    Args:
        repository_url: GitHub repository URL.

    Returns:
        Tuple of (repository_name, error_message). Name is None if extraction fails.
    """
    match = re.search(r'/([^/]+?)(\?.git)?$', repository_url)
    if match:
        return match.group(1), None
    return None, "Could not extract repository name from URL"


def determine_repository_path(repository_branch: str) -> Path:
    """Determine local path for repository.

    Args:
        repository_branch: Git branch name.

    Returns:
        Path object for repository location.
    """
    BUILDS_DIR.mkdir(parents=True, exist_ok=True)
    return BUILDS_DIR / repository_branch


def verify_repository_exists(repository_path: Path) -> bool:
    """Verify repository exists and is a git repository.

    Args:
        repository_path: Path to repository.

    Returns:
        True if repository exists and is valid.
    """
    return repository_path.exists() and (repository_path / ".git").exists()
