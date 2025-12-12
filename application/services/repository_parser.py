"""
Repository parser for Cyoda applications.

Parses repository structure to extract entities, workflows, and functional requirements.
"""

import logging
import os
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from application.services.github.github_service import GitHubService
from common.config.config import CLIENT_GIT_BRANCH

logger = logging.getLogger(__name__)


@dataclass
class EntityInfo:
    """Information about an entity in the repository."""
    name: str
    version: int
    file_path: str
    class_name: str
    fields: List[Dict[str, Any]]
    has_workflow: bool = False


@dataclass
class WorkflowInfo:
    """Information about a workflow in the repository."""
    entity_name: str
    file_path: str
    version: Optional[int] = None
    workflow_file: Optional[str] = None


@dataclass
class RequirementInfo:
    """Information about a functional requirement."""
    file_name: str
    file_path: str
    content: Optional[str] = None


@dataclass
class RepositoryStructure:
    """Complete repository structure."""
    app_type: str  # "python" or "java"
    entities: List[EntityInfo]
    workflows: List[WorkflowInfo]
    requirements: List[RequirementInfo]
    branch: str
    repository_name: str


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
        python_resources = os.getenv("PYTHON_RESOURCES_PATH", self.DEFAULT_PYTHON_RESOURCES_PATH)
        java_resources = os.getenv("JAVA_RESOURCES_PATH", self.DEFAULT_JAVA_RESOURCES_PATH)

        # Construct full paths for entities, workflows and requirements
        self.PYTHON_ENTITY_PATH = f"{python_resources}/entity"
        self.PYTHON_WORKFLOW_PATH = f"{python_resources}/workflow"
        self.PYTHON_REQUIREMENTS_PATH = f"{python_resources}/functional_requirements"

        self.JAVA_ENTITY_PATH = f"{java_resources}/entity"
        self.JAVA_WORKFLOW_PATH = f"{java_resources}/workflow"
        self.JAVA_REQUIREMENTS_PATH = f"{java_resources}/functional_requirements"

        logger.info(f"Initialized RepositoryParser with paths:")
        logger.info(f"  Python entities: {self.PYTHON_ENTITY_PATH}")
        logger.info(f"  Python workflows: {self.PYTHON_WORKFLOW_PATH}")
        logger.info(f"  Python requirements: {self.PYTHON_REQUIREMENTS_PATH}")
        logger.info(f"  Java entities: {self.JAVA_ENTITY_PATH}")
        logger.info(f"  Java workflows: {self.JAVA_WORKFLOW_PATH}")
        logger.info(f"  Java requirements: {self.JAVA_REQUIREMENTS_PATH}")
    
    async def detect_app_type(self, repository_name: str, branch: str = CLIENT_GIT_BRANCH) -> str:
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
        logger.warning(f"Could not detect app type for {repository_name}, defaulting to Python")
        return "python"
    
    async def parse_repository(
        self,
        repository_name: str,
        branch: str = CLIENT_GIT_BRANCH
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
            entities = await self._parse_python_entities(repository_name, branch)
            workflows = await self._parse_workflows(repository_name, branch, self.PYTHON_WORKFLOW_PATH)
            requirements = await self._parse_requirements(repository_name, branch, self.PYTHON_REQUIREMENTS_PATH)
        else:
            entities = await self._parse_java_entities(repository_name, branch)
            workflows = await self._parse_workflows(repository_name, branch, self.JAVA_WORKFLOW_PATH)
            requirements = await self._parse_requirements(repository_name, branch, self.JAVA_REQUIREMENTS_PATH)
        
        return RepositoryStructure(
            app_type=app_type,
            entities=entities,
            workflows=workflows,
            requirements=requirements,
            branch=branch,
            repository_name=repository_name
        )
    
    async def _parse_python_entities(
        self,
        repository_name: str,
        branch: str
    ) -> List[EntityInfo]:
        """Parse Python entities from repository.
        
        Args:
            repository_name: Repository name
            branch: Branch name
            
        Returns:
            List of EntityInfo objects
        """
        entities = []
        
        try:
            # List entity directories
            entity_items = await self.github_service.contents.list_directory(
                repository_name, self.PYTHON_ENTITY_PATH, ref=branch
            )
            
            for item in entity_items:
                if not item.is_directory or item.name.startswith('_'):
                    continue
                
                entity_name = item.name
                logger.info(f"  Found entity: {entity_name}")
                
                # List version directories
                version_items = await self.github_service.contents.list_directory(
                    repository_name, item.path, ref=branch
                )
                
                for version_item in version_items:
                    if not version_item.is_directory or not version_item.name.startswith('version_'):
                        continue
                    
                    # Extract version number
                    version_match = re.match(r'version_(\d+)', version_item.name)
                    if not version_match:
                        continue
                    
                    version = int(version_match.group(1))
                    
                    # Find the entity Python file
                    entity_file_path = f"{version_item.path}/{entity_name}.py"
                    file_exists = await self.github_service.contents.file_exists(
                        repository_name, entity_file_path, ref=branch
                    )
                    
                    if file_exists:
                        # Read file content to extract class name and fields
                        content = await self.github_service.contents.get_file_content(
                            repository_name, entity_file_path, ref=branch
                        )
                        
                        class_name = self._extract_class_name(content)
                        fields = self._extract_fields(content)
                        
                        # Check if workflow exists
                        workflow_path = f"{self.PYTHON_WORKFLOW_PATH}/{entity_name}"
                        has_workflow = await self.github_service.contents.directory_exists(
                            repository_name, workflow_path, ref=branch
                        )
                        
                        entities.append(EntityInfo(
                            name=entity_name,
                            version=version,
                            file_path=entity_file_path,
                            class_name=class_name,
                            fields=fields,
                            has_workflow=has_workflow
                        ))
                        
                        logger.info(f"    ✅ Parsed {entity_name} v{version} (class: {class_name})")
        
        except Exception as e:
            logger.error(f"Error parsing Python entities: {e}")
        
        return entities
    
    async def _parse_java_entities(
        self,
        repository_name: str,
        branch: str
    ) -> List[EntityInfo]:
        """Parse Java entities from repository."""
        # TODO: Implement Java entity parsing
        logger.warning("Java entity parsing not yet implemented")
        return []
    
    async def _parse_workflows(
        self,
        repository_name: str,
        branch: str,
        workflow_path: str
    ) -> List[WorkflowInfo]:
        """Parse workflow files."""
        workflows = []

        try:
            workflow_exists = await self.github_service.contents.directory_exists(
                repository_name, workflow_path, ref=branch
            )

            if not workflow_exists:
                logger.info(f"  No workflows found at {workflow_path}")
                return workflows

            workflow_items = await self.github_service.contents.list_directory(
                repository_name, workflow_path, ref=branch
            )

            for item in workflow_items:
                if item.is_directory:
                    # Look for version directories inside entity workflow directory
                    version_items = await self.github_service.contents.list_directory(
                        repository_name, item.path, ref=branch
                    )

                    for version_item in version_items:
                        if version_item.is_directory and version_item.name.startswith('version_'):
                            # Extract version number
                            version_match = re.search(r'version_(\d+)', version_item.name)
                            version = int(version_match.group(1)) if version_match else None

                            # Look for workflow JSON file
                            workflow_files = await self.github_service.contents.list_directory(
                                repository_name, version_item.path, ref=branch
                            )

                            for wf_file in workflow_files:
                                if wf_file.is_file and wf_file.name.endswith('.json'):
                                    workflows.append(WorkflowInfo(
                                        entity_name=item.name,
                                        file_path=wf_file.path,
                                        version=version,
                                        workflow_file=wf_file.name
                                    ))
                                    logger.info(f"  Found workflow: {item.name} v{version} ({wf_file.name})")

        except Exception as e:
            logger.error(f"Error parsing workflows: {e}")

        return workflows
    
    async def _parse_requirements(
        self,
        repository_name: str,
        branch: str,
        requirements_path: str
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
                    if item.is_file and not item.name.startswith('_'):
                        # Accept markdown, text, and other common doc formats
                        if any(item.name.endswith(ext) for ext in ['.md', '.txt', '.rst', '.adoc']):
                            requirements.append(RequirementInfo(
                                file_name=item.name,
                                file_path=item.path
                            ))
                            logger.info(f"  Found requirement: {item.path}")
                    elif item.is_directory and not item.name.startswith('.'):
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
    
    def _extract_class_name(self, content: Optional[str]) -> str:
        """Extract class name from Python file content."""
        if not content:
            return "Unknown"
        
        # Look for class definition
        match = re.search(r'class\s+(\w+)\s*\(', content)
        if match:
            return match.group(1)
        
        return "Unknown"
    
    def _extract_fields(self, content: Optional[str]) -> List[Dict[str, Any]]:
        """Extract field definitions from Python file content."""
        if not content:
            return []
        
        fields = []
        
        # Look for Field definitions
        field_pattern = r'(\w+):\s*(?:Optional\[)?(\w+)(?:\])?\s*=\s*Field\('
        for match in re.finditer(field_pattern, content):
            field_name = match.group(1)
            field_type = match.group(2)
            
            fields.append({
                "name": field_name,
                "type": field_type
            })
        
        return fields

