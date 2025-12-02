"""
Git credential management.
"""

import asyncio
import logging
import os
from typing import Optional

from common.config.config import GH_DEFAULT_USERNAME
from application.services.github.models.types import GitConfig, GitOperationResult

logger = logging.getLogger(__name__)


class CredentialManager:
    """Manages git credentials and configuration."""
    
    async def configure_git_user(
        self,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        global_config: bool = True
    ) -> GitOperationResult:
        """Configure git user name and email.
        
        Args:
            user_name: Git user name
            user_email: Git user email
            global_config: Whether to set globally
            
        Returns:
            GitOperationResult with success status
        """
        scope = "--global" if global_config else "--local"
        
        if user_name:
            name_process = await asyncio.create_subprocess_exec(
                "git", "config", scope, "user.name", user_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await name_process.communicate()
            
            if name_process.returncode != 0:
                error_msg = f"Error setting git user.name: {stderr.decode()}"
                logger.error(error_msg)
                return GitOperationResult(success=False, message="User name config failed", error=error_msg)
        
        if user_email:
            email_process = await asyncio.create_subprocess_exec(
                "git", "config", scope, "user.email", user_email,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await email_process.communicate()
            
            if email_process.returncode != 0:
                error_msg = f"Error setting git user.email: {stderr.decode()}"
                logger.error(error_msg)
                return GitOperationResult(success=False, message="User email config failed", error=error_msg)
        
        logger.info(f"Git user configured: {user_name} <{user_email}>")
        return GitOperationResult(success=True, message="Git user configured")
    
    async def configure_credential_helper(
        self,
        helper: str = "store",
        global_config: bool = True
    ) -> GitOperationResult:
        """Configure git credential helper.
        
        Args:
            helper: Credential helper type
            global_config: Whether to set globally
            
        Returns:
            GitOperationResult with success status
        """
        scope = "--global" if global_config else "--local"
        
        process = await asyncio.create_subprocess_exec(
            "git", "config", scope, "credential.helper", helper,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = f"Error setting credential helper: {stderr.decode()}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message="Credential helper config failed", error=error_msg)
        
        logger.info(f"Git credential helper set to: {helper}")
        return GitOperationResult(success=True, message=f"Credential helper set to {helper}")
    
    async def store_credentials(
        self,
        username: Optional[str] = None,
        token: Optional[str] = None,
        credentials_file: str = "~/.git-credentials"
    ) -> GitOperationResult:
        """Store git credentials in file.

        Note: This method is deprecated. GitHub App authentication is now used instead.

        Args:
            username: GitHub username
            token: GitHub token (must be provided)
            credentials_file: Path to credentials file

        Returns:
            GitOperationResult with success status
        """
        username = username or GH_DEFAULT_USERNAME

        if not token:
            return GitOperationResult(
                success=False,
                message="No GitHub token provided",
                error="Token parameter is required for credential storage"
            )

        credentials_path = os.path.expanduser(credentials_file)
        credential_line = f"https://{username}:{token}@github.com\n"

        try:
            with open(credentials_path, 'w') as f:
                f.write(credential_line)

            os.chmod(credentials_path, 0o600)

            logger.info(f"Credentials stored in {credentials_path}")
            return GitOperationResult(success=True, message="Credentials stored")

        except Exception as e:
            error_msg = f"Error storing credentials: {e}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message="Credential storage failed", error=error_msg)
    
    async def configure_pull_strategy(
        self,
        rebase: bool = False,
        global_config: bool = True
    ) -> GitOperationResult:
        """Configure git pull strategy.
        
        Args:
            rebase: Whether to use rebase
            global_config: Whether to set globally
            
        Returns:
            GitOperationResult with success status
        """
        scope = "--global" if global_config else "--local"
        value = "true" if rebase else "false"
        
        process = await asyncio.create_subprocess_exec(
            "git", "config", scope, "pull.rebase", value,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = f"Error setting pull.rebase: {stderr.decode()}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message="Pull strategy config failed", error=error_msg)
        
        logger.info(f"Git pull.rebase set to: {value}")
        return GitOperationResult(success=True, message=f"Pull rebase set to {value}")
    
    async def get_git_config(self, key: str, global_config: bool = True) -> Optional[str]:
        """Get git configuration value.
        
        Args:
            key: Configuration key
            global_config: Whether to get global config
            
        Returns:
            Configuration value or None
        """
        scope = "--global" if global_config else "--local"
        
        process = await asyncio.create_subprocess_exec(
            "git", "config", scope, key,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return None
        
        return stdout.decode().strip()

