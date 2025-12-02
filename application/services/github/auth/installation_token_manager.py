"""
GitHub App Installation Access Token Manager

Manages installation access tokens for GitHub App authentication.
Handles token generation, caching, and automatic refresh.
"""

import time
import logging
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import httpx

from application.services.github.auth.jwt_generator import GitHubAppJWTGenerator

logger = logging.getLogger(__name__)


@dataclass
class InstallationToken:
    """Represents a GitHub App installation access token."""
    
    token: str
    expires_at: str  # ISO 8601 format
    permissions: Dict[str, str]
    repository_selection: str
    
    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """
        Check if token is expired or will expire soon.
        
        Args:
            buffer_seconds: Consider token expired this many seconds before actual expiration
            
        Returns:
            True if token is expired or will expire within buffer
        """
        try:
            # Parse ISO 8601 timestamp
            from datetime import datetime
            expires_at = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            now = datetime.now(expires_at.tzinfo)
            
            # Calculate time until expiration
            time_until_expiry = (expires_at - now).total_seconds()
            
            return time_until_expiry <= buffer_seconds
            
        except Exception as e:
            logger.warning(f"Failed to parse token expiration: {e}")
            return True  # Consider invalid tokens as expired


class InstallationTokenManager:
    """Manages GitHub App installation access tokens with caching."""
    
    BASE_URL = "https://api.github.com"
    API_VERSION = "2022-11-28"
    
    def __init__(self, jwt_generator: Optional[GitHubAppJWTGenerator] = None):
        """
        Initialize installation token manager.
        
        Args:
            jwt_generator: JWT generator instance (creates new if not provided)
        """
        self.jwt_generator = jwt_generator or GitHubAppJWTGenerator()
        self._token_cache: Dict[int, InstallationToken] = {}
        self._cache_lock = asyncio.Lock()
    
    async def get_installation_token(
        self,
        installation_id: int,
        repositories: Optional[list] = None,
        permissions: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Get installation access token for a GitHub App installation.
        
        Uses cached token if available and not expired, otherwise requests new token.
        
        Args:
            installation_id: GitHub App installation ID
            repositories: Optional list of repository names to limit access
            permissions: Optional dict of permissions to request
            
        Returns:
            Installation access token as string
            
        Raises:
            Exception: If token request fails
        """
        async with self._cache_lock:
            # Check cache
            cached_token = self._token_cache.get(installation_id)
            
            if cached_token and not cached_token.is_expired():
                logger.debug(f"Using cached installation token for installation {installation_id}")
                return cached_token.token
            
            # Request new token
            logger.info(f"Requesting new installation token for installation {installation_id}")
            token = await self._request_installation_token(
                installation_id,
                repositories,
                permissions
            )
            
            # Cache token
            self._token_cache[installation_id] = token
            
            return token.token
    
    async def _request_installation_token(
        self,
        installation_id: int,
        repositories: Optional[list] = None,
        permissions: Optional[Dict[str, str]] = None
    ) -> InstallationToken:
        """
        Request a new installation access token from GitHub API.
        
        Args:
            installation_id: GitHub App installation ID
            repositories: Optional list of repository names
            permissions: Optional dict of permissions
            
        Returns:
            InstallationToken object
            
        Raises:
            Exception: If API request fails
        """
        # Generate JWT for authentication
        jwt_token = self.jwt_generator.generate_jwt()
        
        # Prepare request
        url = f"{self.BASE_URL}/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
            "Content-Type": "application/json"
        }
        
        # Build request body
        data = {}
        if repositories:
            data["repositories"] = repositories
        if permissions:
            data["permissions"] = permissions
        
        try:
            timeout_config = httpx.Timeout(30.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout_config, trust_env=False) as client:
                response = await client.post(url, json=data, headers=headers)
                
                if response.status_code == 201:
                    response_data = response.json()
                    
                    token = InstallationToken(
                        token=response_data["token"],
                        expires_at=response_data["expires_at"],
                        permissions=response_data.get("permissions", {}),
                        repository_selection=response_data.get("repository_selection", "all")
                    )
                    
                    logger.info(
                        f"Successfully obtained installation token for installation {installation_id} "
                        f"(expires at {token.expires_at}, permissions: {list(token.permissions.keys())})"
                    )
                    
                    return token
                    
                else:
                    error_msg = f"Failed to get installation token (status {response.status_code}): {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
        except httpx.RequestError as e:
            error_msg = f"Network error requesting installation token: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Unexpected error requesting installation token: {e}")
            raise
    
    def clear_cache(self, installation_id: Optional[int] = None):
        """
        Clear token cache.
        
        Args:
            installation_id: If provided, clear only this installation's token.
                           If None, clear all cached tokens.
        """
        if installation_id is not None:
            if installation_id in self._token_cache:
                del self._token_cache[installation_id]
                logger.info(f"Cleared cached token for installation {installation_id}")
        else:
            self._token_cache.clear()
            logger.info("Cleared all cached installation tokens")
    
    async def verify_installation_access(
        self,
        installation_id: int,
        repository_owner: str,
        repository_name: str
    ) -> bool:
        """
        Verify that an installation has access to a specific repository.
        
        Args:
            installation_id: GitHub App installation ID
            repository_owner: Repository owner (username or org)
            repository_name: Repository name
            
        Returns:
            True if installation has access, False otherwise
        """
        try:
            # Get installation token
            token = await self.get_installation_token(installation_id)
            
            # Check repository access
            url = f"{self.BASE_URL}/repos/{repository_owner}/{repository_name}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": self.API_VERSION
            }
            
            timeout_config = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout_config, trust_env=False) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    logger.info(
                        f"Installation {installation_id} has access to "
                        f"{repository_owner}/{repository_name}"
                    )
                    return True
                elif response.status_code == 404:
                    logger.warning(
                        f"Installation {installation_id} does not have access to "
                        f"{repository_owner}/{repository_name} (404)"
                    )
                    return False
                else:
                    logger.warning(
                        f"Unexpected status {response.status_code} checking repository access"
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Error verifying installation access: {e}")
            return False

