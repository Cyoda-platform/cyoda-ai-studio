"""
GitHub collaborator management operations.
"""

import logging
from typing import List, Optional

from common.config.config import GH_DEFAULT_REPOS
from application.services.github.api.client import GitHubAPIClient
from application.services.github.models.types import GitHubPermission, CollaboratorInfo

logger = logging.getLogger(__name__)


class CollaboratorOperations:
    """Handles GitHub collaborator operations."""
    
    def __init__(self, client: Optional[GitHubAPIClient] = None):
        """Initialize collaborator operations.
        
        Args:
            client: GitHub API client (creates new if not provided)
        """
        self.client = client or GitHubAPIClient()
    
    async def add_collaborator(
        self,
        username: str,
        repository_name: str,
        permission: GitHubPermission = GitHubPermission.PUSH,
        owner: Optional[str] = None
    ) -> CollaboratorInfo:
        """Add a collaborator to a repository.
        
        Args:
            username: GitHub username
            repository_name: Repository name
            permission: Permission level
            owner: Repository owner (defaults to client owner)
            
        Returns:
            CollaboratorInfo with details
            
        Raises:
            Exception: If request fails
        """
        owner = owner or self.client.owner
        
        response = await self.client.put(
            f"repos/{owner}/{repository_name}/collaborators/{username}",
            data={"permission": permission.value}
        )
        
        logger.info(f"Added collaborator {username} to {owner}/{repository_name} with {permission.value} permission")
        
        return CollaboratorInfo(
            username=username,
            permission=permission,
            repository=repository_name,
            owner=owner
        )
    
    async def add_collaborator_to_multiple_repos(
        self,
        username: str,
        repository_names: Optional[List[str]] = None,
        permission: GitHubPermission = GitHubPermission.PUSH,
        owner: Optional[str] = None
    ) -> List[CollaboratorInfo]:
        """Add a collaborator to multiple repositories.
        
        Args:
            username: GitHub username
            repository_names: List of repository names (defaults to config repos)
            permission: Permission level
            owner: Repository owner (defaults to client owner)
            
        Returns:
            List of CollaboratorInfo
        """
        owner = owner or self.client.owner
        repos = repository_names or GH_DEFAULT_REPOS
        
        results = []
        for repo in repos:
            try:
                info = await self.add_collaborator(username, repo, permission, owner)
                results.append(info)
            except Exception as e:
                logger.error(f"Failed to add {username} to {repo}: {e}")
                raise
        
        return results
    
    async def remove_collaborator(
        self,
        username: str,
        repository_name: str,
        owner: Optional[str] = None
    ) -> bool:
        """Remove a collaborator from a repository.
        
        Args:
            username: GitHub username
            repository_name: Repository name
            owner: Repository owner (defaults to client owner)
            
        Returns:
            True if successful
            
        Raises:
            Exception: If request fails
        """
        owner = owner or self.client.owner
        
        await self.client.delete(
            f"repos/{owner}/{repository_name}/collaborators/{username}"
        )
        
        logger.info(f"Removed collaborator {username} from {owner}/{repository_name}")
        return True
    
    async def list_collaborators(
        self,
        repository_name: str,
        owner: Optional[str] = None
    ) -> List[dict]:
        """List all collaborators for a repository.
        
        Args:
            repository_name: Repository name
            owner: Repository owner (defaults to client owner)
            
        Returns:
            List of collaborator data
        """
        owner = owner or self.client.owner
        
        response = await self.client.get(
            f"repos/{owner}/{repository_name}/collaborators"
        )
        
        return response or []
    
    async def check_collaborator_permission(
        self,
        username: str,
        repository_name: str,
        owner: Optional[str] = None
    ) -> Optional[str]:
        """Check a collaborator's permission level.
        
        Args:
            username: GitHub username
            repository_name: Repository name
            owner: Repository owner (defaults to client owner)
            
        Returns:
            Permission level or None if not a collaborator
        """
        owner = owner or self.client.owner
        
        try:
            response = await self.client.get(
                f"repos/{owner}/{repository_name}/collaborators/{username}/permission"
            )
            
            if response and "permission" in response:
                return response["permission"]
            return None
        
        except Exception as e:
            logger.warning(f"Could not check permission for {username}: {e}")
            return None

