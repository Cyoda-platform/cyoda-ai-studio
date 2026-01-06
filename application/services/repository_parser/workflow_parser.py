"""Workflow parsing utilities."""

import logging
import re
from typing import Any, List, Optional

from application.services.github.github_service import GitHubService
from .models import WorkflowInfo

logger = logging.getLogger(__name__)


class WorkflowParser:
    """Parser for workflow files."""

    def __init__(self, github_service: GitHubService):
        self.github_service = github_service

    def _extract_version_number(self, version_dir_name: str) -> Optional[int]:
        """Extract version number from version directory name.

        Args:
            version_dir_name: Directory name (e.g., 'version_1')

        Returns:
            Version number or None if not found
        """
        version_match = re.search(r'version_(\d+)', version_dir_name)
        return int(version_match.group(1)) if version_match else None

    def _is_workflow_file(self, file_item: Any) -> bool:
        """Check if file is a workflow JSON file.

        Args:
            file_item: File item from directory listing

        Returns:
            True if file is a workflow JSON file
        """
        return file_item.is_file and file_item.name.endswith('.json')

    def _create_workflow_info(
        self,
        entity_name: str,
        version: Optional[int],
        workflow_file: Any,
    ) -> WorkflowInfo:
        """Create WorkflowInfo object.

        Args:
            entity_name: Entity name
            version: Version number
            workflow_file: Workflow file item

        Returns:
            WorkflowInfo object
        """
        return WorkflowInfo(
            entity_name=entity_name,
            file_path=workflow_file.path,
            version=version,
            workflow_file=workflow_file.name
        )

    async def _process_version_directory(
        self,
        repository_name: str,
        branch: str,
        entity_name: str,
        version_item: Any,
    ) -> List[WorkflowInfo]:
        """Process a single version directory for workflows.

        Args:
            repository_name: Repository name
            branch: Branch name
            entity_name: Entity name
            version_item: Version directory item

        Returns:
            List of WorkflowInfo objects found
        """
        workflows = []

        if not version_item.is_directory or not version_item.name.startswith('version_'):
            return workflows

        # Extract version number
        version = self._extract_version_number(version_item.name)

        # List workflow files
        workflow_files = await self.github_service.contents.list_directory(
            repository_name, version_item.path, ref=branch
        )

        # Process each workflow file
        for wf_file in workflow_files:
            if self._is_workflow_file(wf_file):
                workflow_info = self._create_workflow_info(
                    entity_name, version, wf_file
                )
                workflows.append(workflow_info)
                logger.info(
                    f"  Found workflow: {entity_name} v{version} ({wf_file.name})"
                )

        return workflows

    async def parse_workflows(
        self,
        repository_name: str,
        branch: str,
        workflow_path: str
    ) -> List[WorkflowInfo]:
        """Parse workflow files from repository.

        Args:
            repository_name: Repository name
            branch: Branch name
            workflow_path: Path to workflows directory

        Returns:
            List of WorkflowInfo objects
        """
        workflows = []

        try:
            # Check if workflow directory exists
            workflow_exists = await self.github_service.contents.directory_exists(
                repository_name, workflow_path, ref=branch
            )

            if not workflow_exists:
                logger.info(f"  No workflows found at {workflow_path}")
                return workflows

            # List entity workflow directories
            workflow_items = await self.github_service.contents.list_directory(
                repository_name, workflow_path, ref=branch
            )

            # Process each entity directory
            for item in workflow_items:
                if not item.is_directory:
                    continue

                # List version directories
                version_items = await self.github_service.contents.list_directory(
                    repository_name, item.path, ref=branch
                )

                # Process each version directory
                for version_item in version_items:
                    version_workflows = await self._process_version_directory(
                        repository_name, branch, item.name, version_item
                    )
                    workflows.extend(version_workflows)

        except Exception as e:
            logger.error(f"Error parsing workflows: {e}")

        return workflows
