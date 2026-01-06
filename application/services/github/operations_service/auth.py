"""Authentication utilities for GitHub operations."""

import logging
from typing import Optional

from common.config.config import GITHUB_PUBLIC_REPO_INSTALLATION_ID
from application.services.github.auth.installation_token_manager import InstallationTokenManager

logger = logging.getLogger(__name__)


async def get_authenticated_clone_url(
    repository_url: str,
    installation_id: Optional[str],
    use_env_installation_id: bool,
) -> str:
    """Get authenticated clone URL with token if available.

    Args:
        repository_url: GitHub repository URL.
        installation_id: GitHub installation ID (optional).
        use_env_installation_id: Whether to use environment installation ID.

    Returns:
        Clone URL (with token if authenticated, otherwise original URL).
    """
    # Determine effective installation ID
    effective_installation_id = installation_id
    if not effective_installation_id and use_env_installation_id:
        if GITHUB_PUBLIC_REPO_INSTALLATION_ID:
            effective_installation_id = GITHUB_PUBLIC_REPO_INSTALLATION_ID
            logger.debug(f"Using public repo installation ID: {effective_installation_id}")

    clone_url = repository_url

    # Get token if installation ID available
    if effective_installation_id:
        try:
            token_manager = InstallationTokenManager()
            token = await token_manager.get_installation_token(int(effective_installation_id))
            if token:
                clone_url = repository_url.replace(
                    "https://github.com/",
                    f"https://x-access-token:{token}@github.com/"
                )
                logger.info("🔐 Using authenticated URL for cloning")
            else:
                logger.warning("Token retrieval returned None, falling back to public URL")
        except ValueError as e:
            logger.warning(f"Invalid installation ID format: {e}, using public URL")
        except Exception as e:
            logger.warning(f"Failed to get installation token: {e}, using public URL")
    else:
        logger.info("No installation ID available, using public repository URL")

    return clone_url
