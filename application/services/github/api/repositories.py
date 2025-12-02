"""
GitHub repository operations.
"""

import logging
from typing import Optional, List, Dict, Any

from application.services.github.api.client import GitHubAPIClient
from application.services.github.models.types import RepositoryInfo

logger = logging.getLogger(__name__)


class RepositoryOperations:
    """Handles GitHub repository operations."""
    
    def __init__(self, client: Optional[GitHubAPIClient] = None):
        """Initialize repository operations.
        
        Args:
            client: GitHub API client (creates new if not provided)
        """
        self.client = client or GitHubAPIClient()
    
    async def get_repository(
        self,
        repository_name: str,
        owner: Optional[str] = None
    ) -> RepositoryInfo:
        """Get repository information.
        
        Args:
            repository_name: Repository name
            owner: Repository owner (defaults to client owner)
            
        Returns:
            RepositoryInfo with repository details
            
        Raises:
            Exception: If request fails
        """
        owner = owner or self.client.owner
        
        response = await self.client.get(f"repos/{owner}/{repository_name}")
        
        if not response:
            raise Exception(f"Failed to get repository info for {owner}/{repository_name}")
        
        return RepositoryInfo(
            name=response["name"],
            owner=response["owner"]["login"],
            full_name=response["full_name"],
            url=response["html_url"],
            default_branch=response["default_branch"],
            private=response["private"],
            description=response.get("description")
        )
    
    async def list_repositories(
        self,
        owner: Optional[str] = None,
        repo_type: str = "all",
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """List repositories for an owner.
        
        Args:
            owner: Repository owner (defaults to client owner)
            repo_type: Type of repos (all, public, private)
            per_page: Results per page
            
        Returns:
            List of repository data
        """
        owner = owner or self.client.owner
        
        params = {
            "type": repo_type,
            "per_page": per_page
        }
        
        response = await self.client.get(f"users/{owner}/repos", params=params)
        
        return response or []
    
    async def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = False,
        auto_init: bool = False,
        owner: Optional[str] = None
    ) -> RepositoryInfo:
        """Create a new repository.
        
        Args:
            name: Repository name
            description: Repository description
            private: Whether repository is private
            auto_init: Initialize with README
            owner: Organization owner (None for user repos)
            
        Returns:
            RepositoryInfo for created repository
        """
        data = {
            "name": name,
            "private": private,
            "auto_init": auto_init
        }
        
        if description:
            data["description"] = description
        
        if owner:
            path = f"orgs/{owner}/repos"
        else:
            path = "user/repos"
        
        response = await self.client.post(path, data=data)
        
        if not response:
            raise Exception(f"Failed to create repository {name}")
        
        logger.info(f"Created repository {response['full_name']}")
        
        return RepositoryInfo(
            name=response["name"],
            owner=response["owner"]["login"],
            full_name=response["full_name"],
            url=response["html_url"],
            default_branch=response["default_branch"],
            private=response["private"],
            description=response.get("description")
        )
    
    async def delete_repository(
        self,
        repository_name: str,
        owner: Optional[str] = None
    ) -> bool:
        """Delete a repository.
        
        Args:
            repository_name: Repository name
            owner: Repository owner (defaults to client owner)
            
        Returns:
            True if successful
        """
        owner = owner or self.client.owner
        
        await self.client.delete(f"repos/{owner}/{repository_name}")
        
        logger.info(f"Deleted repository {owner}/{repository_name}")
        return True
    
    async def update_repository(
        self,
        repository_name: str,
        owner: Optional[str] = None,
        description: Optional[str] = None,
        private: Optional[bool] = None,
        default_branch: Optional[str] = None
    ) -> RepositoryInfo:
        """Update repository settings.
        
        Args:
            repository_name: Repository name
            owner: Repository owner (defaults to client owner)
            description: New description
            private: New private setting
            default_branch: New default branch
            
        Returns:
            Updated RepositoryInfo
        """
        owner = owner or self.client.owner
        
        data = {}
        if description is not None:
            data["description"] = description
        if private is not None:
            data["private"] = private
        if default_branch is not None:
            data["default_branch"] = default_branch
        
        response = await self.client.patch(f"repos/{owner}/{repository_name}", data=data)
        
        if not response:
            raise Exception(f"Failed to update repository {owner}/{repository_name}")
        
        logger.info(f"Updated repository {owner}/{repository_name}")
        
        return RepositoryInfo(
            name=response["name"],
            owner=response["owner"]["login"],
            full_name=response["full_name"],
            url=response["html_url"],
            default_branch=response["default_branch"],
            private=response["private"],
            description=response.get("description")
        )
    
    async def get_repository_topics(
        self,
        repository_name: str,
        owner: Optional[str] = None
    ) -> List[str]:
        """Get repository topics.
        
        Args:
            repository_name: Repository name
            owner: Repository owner (defaults to client owner)
            
        Returns:
            List of topic names
        """
        owner = owner or self.client.owner
        
        response = await self.client.get(f"repos/{owner}/{repository_name}/topics")
        
        return response.get("names", []) if response else []
    
    async def set_repository_topics(
        self,
        repository_name: str,
        topics: List[str],
        owner: Optional[str] = None
    ) -> List[str]:
        """Set repository topics.
        
        Args:
            repository_name: Repository name
            topics: List of topic names
            owner: Repository owner (defaults to client owner)
            
        Returns:
            Updated list of topics
        """
        owner = owner or self.client.owner
        
        response = await self.client.put(
            f"repos/{owner}/{repository_name}/topics",
            data={"names": topics}
        )
        
        logger.info(f"Updated topics for {owner}/{repository_name}")
        
        return response.get("names", []) if response else []

