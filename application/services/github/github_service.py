"""
Main GitHub Service - Unified facade for all GitHub and Git operations.

This service provides a single entry point for:
- GitHub API operations (workflows, collaborators, repositories)
- Local git operations (clone, pull, push, commit)
- Repository resolution and configuration
- Branch management
- Credential management
"""

from typing import Any, Dict, List, Optional

from application.services.github.api.client import GitHubAPIClient
from application.services.github.api.collaborators import CollaboratorOperations
from application.services.github.api.contents import ContentsOperations
from application.services.github.api.repositories import RepositoryOperations
from application.services.github.api.workflows import WorkflowOperations
from application.services.github.git.branch_manager import BranchManager
from application.services.github.git.credentials import CredentialManager
from application.services.github.git.operations import GitOperations
from application.services.github.models.types import (
    BranchInfo,
    GitHubPermission,
    GitOperationResult,
    RepositoryInfo,
    WorkflowConclusion,
    WorkflowRunInfo,
    WorkflowStatus,
)
from application.services.github.repository.config import RepositoryConfig
from application.services.github.repository.resolver import (
    RepositoryResolverFactory,
    resolve_repository_name,
    resolve_repository_name_with_language_param,
)
from common.config.config import CLIENT_GIT_BRANCH


class GitHubService:
    """
    Unified GitHub service providing all GitHub and Git functionality.

    This is the main entry point for all GitHub-related operations in the application.
    Supports both public repositories (personal access token) and private repositories (GitHub App).
    """

    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        installation_id: Optional[int] = None,
    ):
        """Initialize GitHub service.

        Args:
            token: GitHub API token (defaults to config)
            owner: Default repository owner (defaults to config)
            installation_id: GitHub App installation ID (for private repos)
        """
        self.installation_id = installation_id
        self.api_client = GitHubAPIClient(
            token=token, owner=owner, installation_id=installation_id
        )

        self.workflows = WorkflowOperations(client=self.api_client)
        self.repositories = RepositoryOperations(client=self.api_client)
        self.collaborators = CollaboratorOperations(client=self.api_client)
        self.contents = ContentsOperations(client=self.api_client)

        self.git = GitOperations(installation_id=installation_id)
        self.branches = BranchManager()
        self.credentials = CredentialManager()

        self.resolver_factory = RepositoryResolverFactory()

    async def clone_repository(
        self,
        git_branch_id: str,
        repository_name: str,
        base_branch: Optional[str] = None,
        repository_url: Optional[str] = None,
    ) -> GitOperationResult:
        """Clone repository and create new branch.

        Args:
            git_branch_id: Branch ID to create
            repository_name: Repository name
            base_branch: Base branch to checkout
            repository_url: Custom repository URL (for private repos)

        Returns:
            GitOperationResult with success status
        """
        return await self.git.clone_repository(
            git_branch_id, repository_name, base_branch, repository_url
        )

    async def pull_changes(
        self,
        git_branch_id: str,
        repository_name: str,
        merge_strategy: str = "recursive",
        repository_url: Optional[str] = None,
    ) -> GitOperationResult:
        """Pull latest changes from remote.

        Args:
            git_branch_id: Branch ID
            repository_name: Repository name
            merge_strategy: Git merge strategy
            repository_url: Custom repository URL (for private repos)

        Returns:
            GitOperationResult with diff information
        """
        return await self.git.pull(
            git_branch_id, repository_name, merge_strategy, repository_url
        )

    async def push_changes(
        self,
        git_branch_id: str,
        repository_name: str,
        file_paths: List[str],
        commit_message: str,
        repository_url: Optional[str] = None,
    ) -> GitOperationResult:
        """Push changes to remote repository.

        Args:
            git_branch_id: Branch ID
            repository_name: Repository name
            file_paths: List of file paths to add
            commit_message: Commit message
            repository_url: Custom repository URL (for private repos)

        Returns:
            GitOperationResult with success status
        """
        return await self.git.push(
            git_branch_id, repository_name, file_paths, commit_message, repository_url
        )

    async def repository_exists(self, git_branch_id: str, repository_name: str) -> bool:
        """Check if repository directory exists locally.

        Args:
            git_branch_id: Branch ID
            repository_name: Repository name

        Returns:
            True if repository exists
        """
        return await self.git.repository_exists(git_branch_id, repository_name)

    async def trigger_workflow(
        self,
        repository_name: str,
        workflow_id: str,
        ref: str = CLIENT_GIT_BRANCH,
        inputs: Optional[Dict[str, Any]] = None,
        owner: Optional[str] = None,
        tracker_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger a GitHub Actions workflow.

        Args:
            repository_name: Repository name
            workflow_id: Workflow ID or filename
            ref: Git reference (branch/tag)
            inputs: Workflow inputs
            owner: Repository owner
            tracker_id: Unique tracker ID

        Returns:
            Dict with run_id, tracker_id, and status
        """
        return await self.workflows.trigger_workflow(
            repository_name, workflow_id, ref, inputs, owner, tracker_id
        )

    async def monitor_workflow(
        self,
        repository_name: str,
        run_id: int,
        owner: Optional[str] = None,
        poll_interval: int = 30,
        timeout_minutes: int = 60,
    ) -> WorkflowRunInfo:
        """Monitor a workflow run until completion.

        Args:
            repository_name: Repository name
            run_id: Workflow run ID
            owner: Repository owner
            poll_interval: Seconds between checks
            timeout_minutes: Maximum wait time

        Returns:
            Final WorkflowRunInfo
        """
        return await self.workflows.monitor_workflow_run(
            repository_name, run_id, owner, poll_interval, timeout_minutes
        )

    async def run_workflow_and_wait(
        self,
        repository_name: str,
        workflow_id: str,
        ref: str = CLIENT_GIT_BRANCH,
        inputs: Optional[Dict[str, Any]] = None,
        owner: Optional[str] = None,
        timeout_minutes: int = 60,
    ) -> WorkflowRunInfo:
        """Trigger workflow and wait for completion.

        Args:
            repository_name: Repository name
            workflow_id: Workflow ID or filename
            ref: Git reference
            inputs: Workflow inputs
            owner: Repository owner
            timeout_minutes: Maximum wait time

        Returns:
            Final WorkflowRunInfo
        """
        return await self.workflows.run_workflow_and_wait(
            repository_name, workflow_id, ref, inputs, owner, timeout_minutes
        )

    async def get_workflow_logs(
        self, repository_name: str, run_id: int, owner: Optional[str] = None
    ) -> Dict[str, str]:
        """Get logs from a workflow run.

        Args:
            repository_name: Repository name
            run_id: Workflow run ID
            owner: Repository owner

        Returns:
            Dict mapping job names to log content
        """
        return await self.workflows.get_workflow_logs(repository_name, run_id, owner)

    async def add_collaborator(
        self,
        username: str,
        repository_name: str,
        permission: GitHubPermission = GitHubPermission.PUSH,
        owner: Optional[str] = None,
    ):
        """Add a collaborator to a repository.

        Args:
            username: GitHub username
            repository_name: Repository name
            permission: Permission level
            owner: Repository owner

        Returns:
            CollaboratorInfo
        """
        return await self.collaborators.add_collaborator(
            username, repository_name, permission, owner
        )

    async def add_collaborator_to_multiple_repos(
        self,
        username: str,
        repository_names: Optional[List[str]] = None,
        permission: GitHubPermission = GitHubPermission.PUSH,
        owner: Optional[str] = None,
    ):
        """Add a collaborator to multiple repositories.

        Args:
            username: GitHub username
            repository_names: List of repository names
            permission: Permission level
            owner: Repository owner

        Returns:
            List of CollaboratorInfo
        """
        return await self.collaborators.add_collaborator_to_multiple_repos(
            username, repository_names, permission, owner
        )

    async def get_repository_info(
        self, repository_name: str, owner: Optional[str] = None
    ) -> RepositoryInfo:
        """Get repository information.

        Args:
            repository_name: Repository name
            owner: Repository owner

        Returns:
            RepositoryInfo
        """
        return await self.repositories.get_repository(repository_name, owner)

    def resolve_repository_name(
        self, programming_language: Optional[str] = None
    ) -> str:
        """Resolve repository name based on programming language.

        Args:
            programming_language: Programming language

        Returns:
            Repository name
        """
        return resolve_repository_name(programming_language)

    def resolve_repository_name_with_language(
        self, programming_language: Optional[str] = None
    ) -> str:
        """Resolve repository name with language priority.

        Args:
            programming_language: Programming language

        Returns:
            Repository name
        """
        return resolve_repository_name_with_language_param(programming_language)

    def get_repository_config(
        self, repository_name: str, owner: Optional[str] = None
    ) -> RepositoryConfig:
        """Get repository configuration.

        Args:
            repository_name: Repository name
            owner: Repository owner

        Returns:
            RepositoryConfig
        """
        return RepositoryConfig.from_name(repository_name, owner)
