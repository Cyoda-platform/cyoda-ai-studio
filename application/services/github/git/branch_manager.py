"""
Branch management operations.
"""

import asyncio
import logging
from typing import Optional, List

from common.config.config import CLIENT_GIT_BRANCH
from application.services.github.models.types import BranchInfo, GitOperationResult

logger = logging.getLogger(__name__)


class BranchManager:
    """Manages git branch operations."""
    
    async def create_branch(
        self,
        clone_dir: str,
        branch_name: str,
        base_branch: Optional[str] = None
    ) -> GitOperationResult:
        """Create a new branch.
        
        Args:
            clone_dir: Repository directory
            branch_name: Name of new branch
            base_branch: Base branch to create from
            
        Returns:
            GitOperationResult with success status
        """
        base_branch = base_branch or CLIENT_GIT_BRANCH
        
        checkout_base_process = await asyncio.create_subprocess_exec(
            'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
            'checkout', base_branch,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await checkout_base_process.communicate()
        
        if checkout_base_process.returncode != 0:
            error_msg = f"Error checking out base branch {base_branch}: {stderr.decode()}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message="Base checkout failed", error=error_msg)
        
        create_process = await asyncio.create_subprocess_exec(
            'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
            'checkout', '-b', branch_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await create_process.communicate()
        
        if create_process.returncode != 0:
            error_msg = f"Error creating branch {branch_name}: {stderr.decode()}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message="Branch creation failed", error=error_msg)
        
        logger.info(f"Branch {branch_name} created successfully")
        return GitOperationResult(success=True, message=f"Branch {branch_name} created")
    
    async def checkout_branch(self, clone_dir: str, branch_name: str) -> GitOperationResult:
        """Checkout a branch.
        
        Args:
            clone_dir: Repository directory
            branch_name: Branch to checkout
            
        Returns:
            GitOperationResult with success status
        """
        process = await asyncio.create_subprocess_exec(
            'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
            'checkout', branch_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = f"Error checking out branch {branch_name}: {stderr.decode()}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message="Checkout failed", error=error_msg)
        
        logger.info(f"Checked out branch {branch_name}")
        return GitOperationResult(success=True, message=f"Checked out {branch_name}")
    
    async def delete_branch(self, clone_dir: str, branch_name: str, force: bool = False) -> GitOperationResult:
        """Delete a branch.
        
        Args:
            clone_dir: Repository directory
            branch_name: Branch to delete
            force: Force deletion
            
        Returns:
            GitOperationResult with success status
        """
        flag = '-D' if force else '-d'
        
        process = await asyncio.create_subprocess_exec(
            'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
            'branch', flag, branch_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = f"Error deleting branch {branch_name}: {stderr.decode()}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message="Branch deletion failed", error=error_msg)
        
        logger.info(f"Branch {branch_name} deleted")
        return GitOperationResult(success=True, message=f"Branch {branch_name} deleted")
    
    async def list_branches(self, clone_dir: str) -> List[str]:
        """List all branches.
        
        Args:
            clone_dir: Repository directory
            
        Returns:
            List of branch names
        """
        process = await asyncio.create_subprocess_exec(
            'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
            'branch', '--list',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Error listing branches: {stderr.decode()}")
            return []
        
        branches = []
        for line in stdout.decode().split('\n'):
            line = line.strip()
            if line:
                branch = line.lstrip('* ')
                branches.append(branch)
        
        return branches
    
    async def get_current_branch(self, clone_dir: str) -> Optional[str]:
        """Get current branch name.
        
        Args:
            clone_dir: Repository directory
            
        Returns:
            Current branch name or None
        """
        process = await asyncio.create_subprocess_exec(
            'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
            'rev-parse', '--abbrev-ref', 'HEAD',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Error getting current branch: {stderr.decode()}")
            return None
        
        return stdout.decode().strip()
    
    async def set_upstream(self, clone_dir: str, branch_name: str, remote: str = "origin") -> GitOperationResult:
        """Set upstream tracking for branch.
        
        Args:
            clone_dir: Repository directory
            branch_name: Branch name
            remote: Remote name
            
        Returns:
            GitOperationResult with success status
        """
        process = await asyncio.create_subprocess_exec(
            'git', '--git-dir', f"{clone_dir}/.git", '--work-tree', clone_dir,
            'branch', '--set-upstream-to', f"{remote}/{branch_name}", branch_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = f"Error setting upstream: {stderr.decode()}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message="Set upstream failed", error=error_msg)
        
        logger.info(f"Upstream set for branch {branch_name}")
        return GitOperationResult(success=True, message=f"Upstream set for {branch_name}")

