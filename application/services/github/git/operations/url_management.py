"""URL handling and authentication for git operations.

This module contains functions for:
- Repository URL construction with authentication
- Installation token management
- URL parsing and transformation
"""

import logging
from typing import Optional

from application.services.github.repository.url_parser import construct_repository_url, parse_repository_url
from application.services.github.auth.installation_token_manager import InstallationTokenManager
from common.config.config import REPOSITORY_URL

logger = logging.getLogger(__name__)


async def get_repository_url(
    installation_id: Optional[int],
    installation_token_manager: Optional[InstallationTokenManager],
    repository_name: str,
    repository_url: Optional[str] = None
) -> str:
    """Get repository URL with authentication.

    Args:
        installation_id: GitHub App installation ID (for private repos)
        installation_token_manager: Token manager instance
        repository_name: Repository name (used for public repos)
        repository_url: Custom repository URL (used for private repos)

    Returns:
        Authenticated repository URL
    """
    # If custom URL provided (private repo), use installation token
    if repository_url:
        if installation_id and installation_token_manager:
            token = await installation_token_manager.get_installation_token(installation_id)
            url_info = parse_repository_url(repository_url)
            return url_info.to_authenticated_url(token)
        else:
            # Custom URL without installation ID - use as-is (might fail if private)
            logger.warning(f"Custom repository URL provided without installation ID: {repository_url}")
            return repository_url

    # Public repo - use config URL template
    return REPOSITORY_URL.format(repository_name=repository_name)
