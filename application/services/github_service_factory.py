"""
GitHub Service Factory

Creates GitHubService instances with appropriate configuration for public and private repositories.

Public repositories use GitHub App credentials from .env file.
Private repositories require user-provided credentials (installation_id, repository_url).
"""

import logging
from typing import Optional

from application.services.github.github_service import GitHubService
from common.config.config import (
    GH_DEFAULT_OWNER,
    GITHUB_APP_ID,
    GITHUB_APP_PRIVATE_KEY_PATH,
    GITHUB_PUBLIC_REPO_INSTALLATION_ID,
)

logger = logging.getLogger(__name__)


class GitHubServiceFactory:
    """
    Factory for creating GitHubService instances.

    Handles differentiation between public and private repositories:
    - Public repos: Use GitHub App configuration from .env
    - Private repos: Require user-provided credentials
    """

    @staticmethod
    def create_for_public_repo(
        owner: Optional[str] = None, token: Optional[str] = None
    ) -> GitHubService:
        """
        Create GitHubService for public repositories.

        Uses GitHub App configuration from environment variables:
        - GITHUB_APP_ID
        - GITHUB_APP_PRIVATE_KEY_PATH
        - GITHUB_PUBLIC_REPO_INSTALLATION_ID
        - GH_DEFAULT_OWNER

        Args:
            owner: Repository owner (defaults to GH_DEFAULT_OWNER from config)
            token: Optional personal access token (if not using GitHub App)

        Returns:
            GitHubService configured for public repositories

        Raises:
            ValueError: If required GitHub App configuration is missing
        """
        if token:
            # Use personal access token
            logger.info(
                f"Creating GitHub service for public repo with personal access token"
            )
            return GitHubService(token=token, owner=owner or GH_DEFAULT_OWNER)

        # Use GitHub App
        if not GITHUB_APP_ID or not GITHUB_APP_PRIVATE_KEY_PATH:
            raise ValueError(
                "GitHub App configuration missing. "
                "Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY_PATH in .env file."
            )

        if not GITHUB_PUBLIC_REPO_INSTALLATION_ID:
            raise ValueError(
                "Public repository installation ID missing. "
                "Set GITHUB_PUBLIC_REPO_INSTALLATION_ID in .env file."
            )

        installation_id = int(GITHUB_PUBLIC_REPO_INSTALLATION_ID)

        logger.info(
            f"Creating GitHub service for public repo with GitHub App "
            f"(installation_id={installation_id}, owner={owner or GH_DEFAULT_OWNER})"
        )

        return GitHubService(
            owner=owner or GH_DEFAULT_OWNER, installation_id=installation_id
        )

    @staticmethod
    def create_for_private_repo(
        installation_id: int, repository_url: str, owner: Optional[str] = None
    ) -> GitHubService:
        """
        Create GitHubService for private repositories.

        Requires user-provided credentials:
        - installation_id: GitHub App installation ID for the private repo
        - repository_url: Full repository URL

        Args:
            installation_id: GitHub App installation ID
            repository_url: Repository URL (e.g., https://github.com/owner/repo)
            owner: Repository owner (extracted from URL if not provided)

        Returns:
            GitHubService configured for private repository

        Raises:
            ValueError: If required parameters are missing
        """
        if not installation_id:
            raise ValueError("installation_id is required for private repositories")

        if not repository_url:
            raise ValueError("repository_url is required for private repositories")

        # Extract owner from URL if not provided
        if not owner:
            from application.services.github.repository.url_parser import (
                parse_repository_url,
            )

            url_info = parse_repository_url(repository_url)
            owner = url_info.owner

        logger.info(
            f"Creating GitHub service for private repo "
            f"(installation_id={installation_id}, owner={owner}, url={repository_url})"
        )

        return GitHubService(owner=owner, installation_id=installation_id)

    @staticmethod
    def create_with_token(token: str, owner: Optional[str] = None) -> GitHubService:
        """
        Create GitHubService with personal access token.

        This can be used for both public and private repositories
        if the user has a personal access token with appropriate permissions.

        Args:
            token: GitHub personal access token
            owner: Repository owner (defaults to GH_DEFAULT_OWNER)

        Returns:
            GitHubService configured with personal access token
        """
        logger.info(
            f"Creating GitHub service with personal access token (owner={owner or GH_DEFAULT_OWNER})"
        )

        return GitHubService(token=token, owner=owner or GH_DEFAULT_OWNER)


def get_github_service_for_public_repo(
    owner: Optional[str] = None, token: Optional[str] = None
) -> GitHubService:
    """
    Convenience function to get GitHubService for public repositories.

    Args:
        owner: Repository owner (defaults to config)
        token: Optional personal access token

    Returns:
        GitHubService instance
    """
    return GitHubServiceFactory.create_for_public_repo(owner=owner, token=token)


def get_github_service_for_private_repo(
    installation_id: int, repository_url: str, owner: Optional[str] = None
) -> GitHubService:
    """
    Convenience function to get GitHubService for private repositories.

    Args:
        installation_id: GitHub App installation ID
        repository_url: Repository URL
        owner: Repository owner (optional, extracted from URL if not provided)

    Returns:
        GitHubService instance
    """
    return GitHubServiceFactory.create_for_private_repo(
        installation_id=installation_id, repository_url=repository_url, owner=owner
    )


def get_github_service_with_token(
    token: str, owner: Optional[str] = None
) -> GitHubService:
    """
    Convenience function to get GitHubService with personal access token.

    Args:
        token: GitHub personal access token
        owner: Repository owner

    Returns:
        GitHubService instance
    """
    return GitHubServiceFactory.create_with_token(token=token, owner=owner)
