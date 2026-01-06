"""Entity parsing utilities."""

import logging
import re
from typing import Any, Dict, List, Optional

from application.services.github.github_service import GitHubService
from .models import EntityInfo

logger = logging.getLogger(__name__)


class EntityParser:
    """Parser for entity files."""

    def __init__(self, github_service: GitHubService, python_entity_path: str, python_workflow_path: str):
        self.github_service = github_service
        self.python_entity_path = python_entity_path
        self.python_workflow_path = python_workflow_path

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

    async def _parse_entity_version(
        self,
        repository_name: str,
        branch: str,
        entity_name: str,
        version_item: Any,
    ) -> Optional[EntityInfo]:
        """Parse a single entity version.

        Args:
            repository_name: Repository name
            branch: Branch name
            entity_name: Entity name
            version_item: Version directory item

        Returns:
            EntityInfo or None if parsing fails
        """
        version_match = re.match(r'version_(\d+)', version_item.name)
        if not version_match:
            return None

        version = int(version_match.group(1))
        entity_file_path = f"{version_item.path}/{entity_name}.py"

        file_exists = await self.github_service.contents.file_exists(
            repository_name, entity_file_path, ref=branch
        )

        if not file_exists:
            return None

        content = await self.github_service.contents.get_file_content(
            repository_name, entity_file_path, ref=branch
        )

        class_name = self._extract_class_name(content)
        fields = self._extract_fields(content)

        workflow_path = f"{self.python_workflow_path}/{entity_name}"
        has_workflow = await self.github_service.contents.directory_exists(
            repository_name, workflow_path, ref=branch
        )

        logger.info(f"    ✅ Parsed {entity_name} v{version} (class: {class_name})")

        return EntityInfo(
            name=entity_name,
            version=version,
            file_path=entity_file_path,
            class_name=class_name,
            fields=fields,
            has_workflow=has_workflow,
        )

    async def parse_python_entities(
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
            entity_items = await self.github_service.contents.list_directory(
                repository_name, self.python_entity_path, ref=branch
            )

            for item in entity_items:
                if not item.is_directory or item.name.startswith('_'):
                    continue

                entity_name = item.name
                logger.info(f"  Found entity: {entity_name}")

                version_items = await self.github_service.contents.list_directory(
                    repository_name, item.path, ref=branch
                )

                for version_item in version_items:
                    if not version_item.is_directory or not version_item.name.startswith('version_'):
                        continue

                    entity_info = await self._parse_entity_version(
                        repository_name, branch, entity_name, version_item
                    )

                    if entity_info:
                        entities.append(entity_info)

        except Exception as e:
            logger.error(f"Error parsing Python entities: {e}")

        return entities

    async def parse_java_entities(
        self,
        repository_name: str,
        branch: str
    ) -> List[EntityInfo]:
        """Parse Java entities from repository."""
        # TODO: Implement Java entity parsing
        logger.warning("Java entity parsing not yet implemented")
        return []
