"""Requirements parser for extracting entities and workflows.

This module analyzes functional requirements to extract:
- Expected entities (data models)
- Expected workflows (business processes)
- Dependencies between them

Used for incremental generation and post-generation validation.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RequirementsParser:
    """Parser for extracting structured information from functional requirements."""

    @staticmethod
    async def parse_requirements_with_llm(
        requirements_text: str, llm_client: Optional[Any] = None
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Optional[str]]:
        """Parse requirements using LLM to extract entities and workflows.

        Args:
            requirements_text: The functional requirements text
            llm_client: Optional LLM client (if None, uses simple regex parsing)

        Returns:
            Tuple of (entities_list, workflows_list, error_message)
            Each entity/workflow is a dict with 'name' and 'description'
        """
        if llm_client:
            return await RequirementsParser._parse_with_llm(
                requirements_text, llm_client
            )
        else:
            return RequirementsParser._parse_with_regex(requirements_text)

    @staticmethod
    async def _parse_with_llm(
        requirements_text: str, llm_client: Any
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Optional[str]]:
        """Use LLM to extract entities and workflows from requirements.

        Args:
            requirements_text: Requirements text
            llm_client: LLM client instance

        Returns:
            Tuple of (entities, workflows, error)
        """
        try:
            prompt = f"""Analyze the following functional requirements and extract:
1. All data entities/models that need to be created
2. All workflows/business processes that need to be implemented

Return your answer ONLY as valid JSON in this exact format:
{{
  "entities": [
    {{"name": "EntityName", "description": "Brief description"}},
    ...
  ],
  "workflows": [
    {{"name": "WorkflowName", "description": "Brief description"}},
    ...
  ]
}}

Functional Requirements:
{requirements_text}

JSON Output:"""

            response = await llm_client.generate_content(prompt)
            response_text = response.text.strip()

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(
                r"```(?:json)?\s*(\{{.*?\}})\s*```", response_text, re.DOTALL
            )
            if json_match:
                json_text = json_match.group(1)
            else:
                json_text = response_text

            parsed = json.loads(json_text)
            entities = parsed.get("entities", [])
            workflows = parsed.get("workflows", [])

            logger.info(
                f"✅ LLM parsed requirements: {len(entities)} entities, {len(workflows)} workflows"
            )
            return entities, workflows, None

        except Exception as e:
            logger.error(f"❌ LLM parsing failed: {e}")
            # Fallback to regex parsing
            logger.info("Falling back to regex parsing")
            return RequirementsParser._parse_with_regex(requirements_text)

    @staticmethod
    def _parse_with_regex(
        requirements_text: str,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Optional[str]]:
        """Fallback: Use regex patterns to extract entities and workflows.

        Args:
            requirements_text: Requirements text

        Returns:
            Tuple of (entities, workflows, error)
        """
        entities = []
        workflows = []

        # Pattern 1: "Entity: Name - Description" or "## Entity: Name"
        entity_pattern = r"(?:##\s*)?(?:Entity|Data Model|Model):\s*([A-Z][A-Za-z0-9_]+)(?:\s*-\s*(.+?))?$"
        entity_matches = re.finditer(
            entity_pattern, requirements_text, re.MULTILINE | re.IGNORECASE
        )

        for match in entity_matches:
            name = match.group(1).strip()
            description = (
                match.group(2).strip() if match.group(2) else f"Entity: {name}"
            )
            entities.append({"name": name, "description": description})

        # Pattern 2: "Workflow: Name - Description" or "## Workflow: Name"
        workflow_pattern = r"(?:##\s*)?(?:Workflow|Process|Business Process):\s*([A-Z][A-Za-z0-9_\s]+)(?:\s*-\s*(.+?))?$"
        workflow_matches = re.finditer(
            workflow_pattern, requirements_text, re.MULTILINE | re.IGNORECASE
        )

        for match in workflow_matches:
            name = match.group(1).strip()
            description = (
                match.group(2).strip() if match.group(2) else f"Workflow: {name}"
            )
            workflows.append({"name": name, "description": description})

        # Pattern 3: Numbered entities/workflows
        # "1. Entity Name - description"
        numbered_entity_pattern = (
            r"^\d+\.\s+(?:Entity|Model):\s*([A-Z][A-Za-z0-9_]+)(?:\s*-\s*(.+?))?$"
        )
        numbered_matches = re.finditer(
            numbered_entity_pattern, requirements_text, re.MULTILINE | re.IGNORECASE
        )

        for match in numbered_matches:
            name = match.group(1).strip()
            description = (
                match.group(2).strip() if match.group(2) else f"Entity: {name}"
            )
            if not any(e["name"] == name for e in entities):
                entities.append({"name": name, "description": description})

        logger.info(
            f"📝 Regex parsed requirements: {len(entities)} entities, {len(workflows)} workflows"
        )

        if not entities and not workflows:
            return (
                entities,
                workflows,
                "No entities or workflows found in requirements. Requirements may need better structure.",
            )

        return entities, workflows, None

    @staticmethod
    def load_requirements_from_directory(
        language: str, repository_path: str
    ) -> Tuple[str, Optional[str]]:
        """Load all functional requirements files from directory.

        Args:
            language: Programming language
            repository_path: Repository path

        Returns:
            Tuple of (concatenated_requirements_text, error_message)
        """
        try:
            if language.lower() == "python":
                requirements_dir = (
                    Path(repository_path)
                    / "application"
                    / "resources"
                    / "functional_requirements"
                )
            elif language.lower() == "java":
                requirements_dir = (
                    Path(repository_path)
                    / "src"
                    / "main"
                    / "resources"
                    / "functional_requirements"
                )
            else:
                return "", f"Unsupported language: {language}"

            if not requirements_dir.exists():
                return "", f"Requirements directory not found: {requirements_dir}"

            all_requirements = []
            requirement_files = sorted(requirements_dir.glob("*.md")) + sorted(
                requirements_dir.glob("*.txt")
            )

            if not requirement_files:
                return "", f"No requirement files found in {requirements_dir}"

            for req_file in requirement_files:
                logger.info(f"Loading requirement file: {req_file.name}")
                content = req_file.read_text(encoding="utf-8")
                all_requirements.append(f"\n\n--- File: {req_file.name} ---\n{content}")

            combined_text = "\n".join(all_requirements)
            logger.info(
                f"✅ Loaded {len(requirement_files)} requirement files ({len(combined_text)} chars)"
            )
            return combined_text, None

        except Exception as e:
            logger.error(f"Failed to load requirements: {e}")
            return "", f"Failed to load requirements: {str(e)}"


__all__ = ["RequirementsParser"]
