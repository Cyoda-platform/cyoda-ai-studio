"""
GitHub repository contents operations.

Provides methods to read files and list directory contents from GitHub repositories.
"""

import logging
import base64
from typing import Optional, List, Dict, Any

from application.services.github.api.client import GitHubAPIClient

logger = logging.getLogger(__name__)


class FileInfo:
    """Information about a file or directory in a repository."""
    
    def __init__(self, data: Dict[str, Any]):
        self.name: str = data.get("name", "")
        self.path: str = data.get("path", "")
        self.type: str = data.get("type", "")  # "file" or "dir"
        self.size: int = data.get("size", 0)
        self.sha: str = data.get("sha", "")
        self.url: str = data.get("url", "")
        self.download_url: Optional[str] = data.get("download_url")
        self._content: Optional[str] = data.get("content")
        self._encoding: str = data.get("encoding", "base64")
    
    @property
    def is_file(self) -> bool:
        """Check if this is a file."""
        return self.type == "file"
    
    @property
    def is_directory(self) -> bool:
        """Check if this is a directory."""
        return self.type == "dir"
    
    def get_content(self) -> Optional[str]:
        """Get decoded file content."""
        if not self._content:
            return None
        
        if self._encoding == "base64":
            try:
                return base64.b64decode(self._content).decode("utf-8")
            except Exception as e:
                logger.error(f"Failed to decode content for {self.path}: {e}")
                return None
        
        return self._content
    
    def __repr__(self) -> str:
        return f"FileInfo(name='{self.name}', type='{self.type}', path='{self.path}')"


class ContentsOperations:
    """Handles GitHub repository contents operations."""
    
    def __init__(self, client: Optional[GitHubAPIClient] = None):
        """Initialize contents operations.
        
        Args:
            client: GitHub API client (creates new if not provided)
        """
        self.client = client or GitHubAPIClient()
    
    async def get_contents(
        self,
        repository_name: str,
        path: str = "",
        ref: Optional[str] = None,
        owner: Optional[str] = None
    ) -> List[FileInfo]:
        """Get contents of a directory or file.
        
        Args:
            repository_name: Repository name
            path: Path to directory or file (empty string for root)
            ref: Git reference (branch, tag, commit SHA)
            owner: Repository owner (defaults to client owner)
            
        Returns:
            List of FileInfo objects
            
        Raises:
            Exception: If request fails
        """
        owner = owner or self.client.owner
        
        params = {}
        if ref:
            params["ref"] = ref
        
        endpoint = f"repos/{owner}/{repository_name}/contents/{path}"
        response = await self.client.get(endpoint, params=params)
        
        if not response:
            raise Exception(f"Failed to get contents for {owner}/{repository_name}/{path}")
        
        # Response can be a single file or list of files
        if isinstance(response, list):
            return [FileInfo(item) for item in response]
        else:
            return [FileInfo(response)]
    
    async def get_file_content(
        self,
        repository_name: str,
        file_path: str,
        ref: Optional[str] = None,
        owner: Optional[str] = None
    ) -> Optional[str]:
        """Get content of a specific file.
        
        Args:
            repository_name: Repository name
            file_path: Path to file
            ref: Git reference (branch, tag, commit SHA)
            owner: Repository owner (defaults to client owner)
            
        Returns:
            Decoded file content as string, or None if not found
        """
        try:
            files = await self.get_contents(repository_name, file_path, ref, owner)
            if files and files[0].is_file:
                return files[0].get_content()
            return None
        except Exception as e:
            logger.error(f"Failed to get file content for {file_path}: {e}")
            return None
    
    async def list_directory(
        self,
        repository_name: str,
        directory_path: str = "",
        ref: Optional[str] = None,
        owner: Optional[str] = None
    ) -> List[FileInfo]:
        """List contents of a directory.
        
        Args:
            repository_name: Repository name
            directory_path: Path to directory (empty string for root)
            ref: Git reference (branch, tag, commit SHA)
            owner: Repository owner (defaults to client owner)
            
        Returns:
            List of FileInfo objects in the directory
        """
        return await self.get_contents(repository_name, directory_path, ref, owner)
    
    async def file_exists(
        self,
        repository_name: str,
        file_path: str,
        ref: Optional[str] = None,
        owner: Optional[str] = None
    ) -> bool:
        """Check if a file exists in the repository.
        
        Args:
            repository_name: Repository name
            file_path: Path to file
            ref: Git reference (branch, tag, commit SHA)
            owner: Repository owner (defaults to client owner)
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            files = await self.get_contents(repository_name, file_path, ref, owner)
            return len(files) > 0 and files[0].is_file
        except Exception:
            return False
    
    async def directory_exists(
        self,
        repository_name: str,
        directory_path: str,
        ref: Optional[str] = None,
        owner: Optional[str] = None
    ) -> bool:
        """Check if a directory exists in the repository.
        
        Args:
            repository_name: Repository name
            directory_path: Path to directory
            ref: Git reference (branch, tag, commit SHA)
            owner: Repository owner (defaults to client owner)
            
        Returns:
            True if directory exists, False otherwise
        """
        try:
            files = await self.get_contents(repository_name, directory_path, ref, owner)
            return len(files) > 0
        except Exception:
            return False

