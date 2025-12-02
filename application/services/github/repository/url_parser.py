"""
Repository URL parsing and construction utilities.

Handles parsing GitHub repository URLs and constructing authenticated URLs
for git operations with both personal access tokens and installation tokens.
"""

import logging
import re
from typing import Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RepositoryURLInfo:
    """Information extracted from a repository URL."""
    
    owner: str
    repo_name: str
    original_url: str
    is_ssh: bool
    
    def to_https_url(self) -> str:
        """Convert to HTTPS URL format.
        
        Returns:
            HTTPS URL (without authentication)
        """
        return f"https://github.com/{self.owner}/{self.repo_name}"
    
    def to_authenticated_url(self, token: str) -> str:
        """Convert to authenticated HTTPS URL for git operations.
        
        Args:
            token: Authentication token (personal access token or installation token)
            
        Returns:
            Authenticated HTTPS URL
        """
        return f"https://x-access-token:{token}@github.com/{self.owner}/{self.repo_name}.git"


def parse_repository_url(url: str) -> RepositoryURLInfo:
    """
    Parse a GitHub repository URL and extract owner and repository name.
    
    Supports multiple URL formats:
    - HTTPS: https://github.com/owner/repo
    - HTTPS with .git: https://github.com/owner/repo.git
    - SSH: git@github.com:owner/repo.git
    - Short: owner/repo
    
    Args:
        url: GitHub repository URL
        
    Returns:
        RepositoryURLInfo with parsed information
        
    Raises:
        ValueError: If URL format is invalid
    """
    if not url:
        raise ValueError("Repository URL cannot be empty")
    
    # Remove trailing .git if present
    url_clean = url.rstrip('.git').rstrip('/')
    
    # Pattern 1: HTTPS URL (https://github.com/owner/repo)
    https_pattern = r'https?://github\.com/([^/]+)/([^/]+)'
    match = re.match(https_pattern, url_clean)
    if match:
        owner, repo = match.groups()
        return RepositoryURLInfo(
            owner=owner,
            repo_name=repo,
            original_url=url,
            is_ssh=False
        )
    
    # Pattern 2: SSH URL (git@github.com:owner/repo)
    ssh_pattern = r'git@github\.com:([^/]+)/([^/]+)'
    match = re.match(ssh_pattern, url_clean)
    if match:
        owner, repo = match.groups()
        return RepositoryURLInfo(
            owner=owner,
            repo_name=repo,
            original_url=url,
            is_ssh=True
        )
    
    # Pattern 3: Short format (owner/repo)
    short_pattern = r'^([^/]+)/([^/]+)$'
    match = re.match(short_pattern, url_clean)
    if match:
        owner, repo = match.groups()
        return RepositoryURLInfo(
            owner=owner,
            repo_name=repo,
            original_url=url,
            is_ssh=False
        )
    
    raise ValueError(
        f"Invalid GitHub repository URL format: {url}. "
        f"Supported formats: https://github.com/owner/repo, git@github.com:owner/repo, owner/repo"
    )


def construct_repository_url(
    repository_name: str,
    owner: Optional[str] = None,
    token: Optional[str] = None
) -> str:
    """
    Construct a repository URL from components.
    
    Args:
        repository_name: Repository name
        owner: Repository owner (if None, uses repository_name as-is)
        token: Optional authentication token
        
    Returns:
        Repository URL (authenticated if token provided)
    """
    from common.config.config import GH_DEFAULT_OWNER

    # If repository_name contains '/', treat it as owner/repo
    if '/' in repository_name:
        url_info = parse_repository_url(repository_name)
        if token:
            return url_info.to_authenticated_url(token)
        return url_info.to_https_url()

    # Use provided owner or default
    repo_owner = owner or GH_DEFAULT_OWNER
    
    if token:
        return f"https://x-access-token:{token}@github.com/{repo_owner}/{repository_name}.git"
    else:
        return f"https://github.com/{repo_owner}/{repository_name}"


def is_custom_repository_url(url: str) -> bool:
    """
    Check if a URL is a custom repository URL (not a template repository).
    
    Args:
        url: Repository URL
        
    Returns:
        True if URL is custom (not a template)
    """
    from common.config.config import (
        GH_DEFAULT_OWNER,
        PYTHON_REPOSITORY_NAME,
        JAVA_REPOSITORY_NAME,
    )

    try:
        url_info = parse_repository_url(url)

        # Check if it's one of the template repositories
        template_repos = [
            PYTHON_REPOSITORY_NAME,
            JAVA_REPOSITORY_NAME
        ]

        # Check if owner is the default owner and repo is a template
        if url_info.owner == GH_DEFAULT_OWNER and url_info.repo_name in template_repos:
            return False
        
        return True
        
    except ValueError:
        return False


def extract_owner_and_repo(url: str) -> Tuple[str, str]:
    """
    Extract owner and repository name from URL.
    
    Args:
        url: Repository URL
        
    Returns:
        Tuple of (owner, repo_name)
        
    Raises:
        ValueError: If URL format is invalid
    """
    url_info = parse_repository_url(url)
    return url_info.owner, url_info.repo_name

