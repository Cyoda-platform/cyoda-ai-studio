"""Repository parser for Cyoda applications."""

import logging
import os
from typing import List

from application.services.github.github_service import GitHubService
from common.config.config import CLIENT_GIT_BRANCH

from .entity_parser import EntityParser
from .models import EntityInfo, RepositoryStructure, RequirementInfo, WorkflowInfo
from .workflow_parser import WorkflowParser

logger = logging.getLogger(__name__)


class RepositoryParser:
    """Parser for Cyoda application repositories."""

    # Default paths (fallback if env vars not set)
    DEFAULT_PYTHON_RESOURCES_PATH = "application/resources"
    DEFAULT_JAVA_RESOURCES_PATH = "src/main/resources"

    def __init__(self, github_service: GitHubService):
        """Initialize repository parser.

        Args:
            github_service: GitHub service instance
        """
        self.github_service = github_service

        # Get resource paths from environment variables
        python_resources = os.getenv(
            "PYTHON_RESOURCES_PATH", self.DEFAULT_PYTHON_RESOURCES_PATH
        )
        java_resources = os.getenv(
            "JAVA_RESOURCES_PATH", self.DEFAULT_JAVA_RESOURCES_PATH
        )

        # Construct full paths for entities, workflows and requirements
        self.PYTHON_ENTITY_PATH = f"{python_resources}/entity"
        self.PYTHON_WORKFLOW_PATH = f"{python_resources}/workflow"
        self.PYTHON_REQUIREMENTS_PATH = f"{python_resources}/functional_requirements"

        self.JAVA_ENTITY_PATH = f"{java_resources}/entity"
        self.JAVA_WORKFLOW_PATH = f"{java_resources}/workflow"
        self.JAVA_REQUIREMENTS_PATH = f"{java_resources}/functional_requirements"

        # Initialize parsers
        self.entity_parser = EntityParser(
            github_service, self.PYTHON_ENTITY_PATH, self.PYTHON_WORKFLOW_PATH
        )
        self.workflow_parser = WorkflowParser(github_service)

        logger.info(f"Initialized RepositoryParser with paths:")
        logger.info(f"  Python entities: {self.PYTHON_ENTITY_PATH}")
        logger.info(f"  Python workflows: {self.PYTHON_WORKFLOW_PATH}")
        logger.info(f"  Python requirements: {self.PYTHON_REQUIREMENTS_PATH}")
        logger.info(f"  Java entities: {self.JAVA_ENTITY_PATH}")
        logger.info(f"  Java workflows: {self.JAVA_WORKFLOW_PATH}")
        logger.info(f"  Java requirements: {self.JAVA_REQUIREMENTS_PATH}")

    async def _parse_python_entities(
        self, repository_name: str, branch: str = CLIENT_GIT_BRANCH
    ) -> List[EntityInfo]:
        """Wrapper for entity_parser.parse_python_entities (for test compatibility)."""
        return await self.entity_parser.parse_python_entities(repository_name, branch)

    async def detect_app_type(
        self, repository_name: str, branch: str = CLIENT_GIT_BRANCH
    ) -> str:
        """Detect if repository is Python or Java application.

        Args:
            repository_name: Repository name
            branch: Branch name

        Returns:
            "python" or "java"
        """
        # Check for Python structure
        python_exists = await self.github_service.contents.directory_exists(
            repository_name, self.PYTHON_ENTITY_PATH, ref=branch
        )

        if python_exists:
            return "python"

        # Check for Java structure
        java_exists = await self.github_service.contents.directory_exists(
            repository_name, self.JAVA_ENTITY_PATH, ref=branch
        )

        if java_exists:
            return "java"

        # Default to Python
        logger.warning(
            f"Could not detect app type for {repository_name}, defaulting to Python"
        )
        return "python"

    async def parse_repository(
        self, repository_name: str, branch: str = CLIENT_GIT_BRANCH
    ) -> RepositoryStructure:
        """Parse complete repository structure.

        Args:
            repository_name: Repository name
            branch: Branch name

        Returns:
            RepositoryStructure with all parsed information
        """
        logger.info(f"Parsing repository {repository_name} (branch: {branch})")

        # Detect app type
        app_type = await self.detect_app_type(repository_name, branch)
        logger.info(f"Detected app type: {app_type}")

        # Parse based on app type
        if app_type == "python":
            entities = await self.entity_parser.parse_python_entities(
                repository_name, branch
            )
            workflows = await self.workflow_parser.parse_workflows(
                repository_name, branch, self.PYTHON_WORKFLOW_PATH
            )
            requirements = await self._parse_requirements(
                repository_name, branch, self.PYTHON_REQUIREMENTS_PATH
            )
        else:
            entities = await self.entity_parser.parse_java_entities(
                repository_name, branch
            )
            workflows = await self.workflow_parser.parse_workflows(
                repository_name, branch, self.JAVA_WORKFLOW_PATH
            )
            requirements = await self._parse_requirements(
                repository_name, branch, self.JAVA_REQUIREMENTS_PATH
            )

        return RepositoryStructure(
            app_type=app_type,
            entities=entities,
            workflows=workflows,
            requirements=requirements,
            branch=branch,
            repository_name=repository_name,
        )

    async def _parse_requirements(
        self, repository_name: str, branch: str, requirements_path: str
    ) -> List[RequirementInfo]:
        """Parse functional requirement files recursively."""
        requirements = []

        async def scan_directory(path: str):
            """Recursively scan directory for requirement files."""
            try:
                items = await self.github_service.contents.list_directory(
                    repository_name, path, ref=branch
                )

                for item in items:
                    if item.is_file and not item.name.startswith("_"):
                        # Accept markdown, text, and other common doc formats
                        if any(
                            item.name.endswith(ext)
                            for ext in [".md", ".txt", ".rst", ".adoc"]
                        ):
                            requirements.append(
                                RequirementInfo(
                                    file_name=item.name, file_path=item.path
                                )
                            )
                            logger.info(f"  Found requirement: {item.path}")
                    elif item.is_directory and not item.name.startswith("."):
                        # Recursively scan subdirectories
                        await scan_directory(item.path)
            except Exception as e:
                logger.error(f"Error scanning directory {path}: {e}")

        try:
            req_exists = await self.github_service.contents.directory_exists(
                repository_name, requirements_path, ref=branch
            )

            if not req_exists:
                logger.info(f"  No requirements found at {requirements_path}")
                return requirements

            await scan_directory(requirements_path)

        except Exception as e:
            logger.error(f"Error parsing requirements: {e}")

        return requirements
