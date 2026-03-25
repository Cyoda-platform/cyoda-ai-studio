"""Post-generation validation for application builds.

Validates that all entities and workflows from requirements were actually generated.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools.requirements_parser import (
    RequirementsParser,
)

logger = logging.getLogger(__name__)


class GenerationValidator:
    """Validates generated code against functional requirements."""

    @staticmethod
    async def validate_generation(
        language: str,
        repository_path: str,
        llm_client: Optional[Any] = None,
        tool_context: Optional[ToolContext] = None,
    ) -> Tuple[bool, str]:
        """Validate that all entities and workflows from requirements were generated.

        Args:
            language: Programming language (java/python)
            repository_path: Path to generated repository
            llm_client: Optional LLM client for requirements parsing
            tool_context: Optional tool context

        Returns:
            Tuple of (validation_passed, report_message)
        """
        try:
            # Step 1: Load and parse requirements
            logger.info("📋 Loading functional requirements...")
            requirements_text, error = (
                RequirementsParser.load_requirements_from_directory(
                    language, repository_path
                )
            )

            if error:
                logger.warning(f"Could not load requirements: {error}")
                return True, f"⚠️ Validation skipped: {error}"

            # Step 2: Parse requirements to get expected items
            logger.info(
                "🔍 Parsing requirements to extract expected entities and workflows..."
            )
            expected_entities, expected_workflows, parse_error = (
                await RequirementsParser.parse_requirements_with_llm(
                    requirements_text, llm_client
                )
            )

            if parse_error:
                logger.warning(f"Requirements parsing incomplete: {parse_error}")

            expected_entity_count = len(expected_entities)
            expected_workflow_count = len(expected_workflows)

            logger.info(
                f"Expected: {expected_entity_count} entities, {expected_workflow_count} workflows"
            )

            # Step 3: Analyze generated repository
            logger.info("🔍 Analyzing generated repository...")
            actual_entities, actual_workflows = (
                GenerationValidator._analyze_generated_repository(
                    language, repository_path
                )
            )

            actual_entity_count = len(actual_entities)
            actual_workflow_count = len(actual_workflows)

            logger.info(
                f"Found: {actual_entity_count} entities, {actual_workflow_count} workflows"
            )

            # Step 4: Compare and generate report
            report = GenerationValidator._generate_validation_report(
                expected_entities,
                expected_workflows,
                actual_entities,
                actual_workflows,
            )

            # Determine if validation passed
            validation_passed = (
                actual_entity_count
                >= expected_entity_count * 0.8  # Allow 20% tolerance
                and actual_workflow_count >= expected_workflow_count * 0.8
            )

            if not validation_passed:
                logger.warning("❌ Validation failed: Some items may be missing")
            else:
                logger.info("✅ Validation passed")

            return validation_passed, report

        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return False, f"ERROR: Validation failed: {str(e)}"

    @staticmethod
    def _analyze_generated_repository(
        language: str, repository_path: str
    ) -> Tuple[List[str], List[str]]:
        """Analyze generated repository to count entities and workflows.

        Args:
            language: Programming language
            repository_path: Repository path

        Returns:
            Tuple of (entity_names, workflow_names)
        """
        entities = []
        workflows = []

        repo_path = Path(repository_path)

        try:
            if language.lower() == "python":
                # Python: Look for entity files in application/entity/
                entity_dir = repo_path / "application" / "entity"
                if entity_dir.exists():
                    for entity_file in entity_dir.glob("*.py"):
                        if entity_file.name != "__init__.py":
                            entities.append(entity_file.stem)

                # Python: Look for workflows in application/workflows/
                workflow_dir = repo_path / "application" / "workflows"
                if workflow_dir.exists():
                    for workflow_file in workflow_dir.glob("*.json"):
                        workflows.append(workflow_file.stem)

            elif language.lower() == "java":
                # Java: Look for entity classes in src/main/java/.../entity/
                src_main_java = repo_path / "src" / "main" / "java"
                if src_main_java.exists():
                    # Find entity directory (may be nested)
                    for entity_dir in src_main_java.rglob("entity"):
                        if entity_dir.is_dir():
                            for java_file in entity_dir.glob("*.java"):
                                entities.append(java_file.stem)

                    # Find workflow directory
                    for workflow_dir in src_main_java.rglob("workflow"):
                        if workflow_dir.is_dir():
                            for java_file in workflow_dir.glob("*.java"):
                                workflows.append(java_file.stem)

            logger.info(
                f"Found in repository: {len(entities)} entities, {len(workflows)} workflows"
            )
            logger.debug(f"Entities: {entities}")
            logger.debug(f"Workflows: {workflows}")

        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")

        return entities, workflows

    @staticmethod
    def _generate_validation_report(
        expected_entities: List[Dict[str, str]],
        expected_workflows: List[Dict[str, str]],
        actual_entities: List[str],
        actual_workflows: List[str],
    ) -> str:
        """Generate a human-readable validation report.

        Args:
            expected_entities: Expected entities from requirements
            expected_workflows: Expected workflows from requirements
            actual_entities: Actually generated entity names
            actual_workflows: Actually generated workflow names

        Returns:
            Formatted validation report
        """
        report_lines = []
        report_lines.append("\n## 📊 Generation Validation Report\n")

        # Summary
        report_lines.append("### Summary")
        report_lines.append(
            f"- **Expected**: {len(expected_entities)} entities, {len(expected_workflows)} workflows"
        )
        report_lines.append(
            f"- **Generated**: {len(actual_entities)} entities, {len(actual_workflows)} workflows"
        )

        # Entities validation
        if expected_entities:
            report_lines.append("\n### Entities")
            expected_names = {e["name"] for e in expected_entities}
            missing_entities = []
            generated_entities = []

            for expected in expected_entities:
                # Fuzzy match: check if entity name appears in any generated file
                found = any(
                    expected["name"].lower() in actual.lower()
                    for actual in actual_entities
                )
                if found:
                    generated_entities.append(expected["name"])
                else:
                    missing_entities.append(expected["name"])

            if generated_entities:
                report_lines.append(f"✅ **Generated** ({len(generated_entities)}):")
                for name in generated_entities:
                    report_lines.append(f"   - {name}")

            if missing_entities:
                report_lines.append(
                    f"\n⚠️ **Possibly Missing** ({len(missing_entities)}):"
                )
                for name in missing_entities:
                    report_lines.append(f"   - {name}")

        # Workflows validation
        if expected_workflows:
            report_lines.append("\n### Workflows")
            missing_workflows = []
            generated_workflows = []

            for expected in expected_workflows:
                # Fuzzy match: check if workflow name appears in any generated file
                found = any(
                    expected["name"].lower().replace(" ", "").replace("_", "")
                    in actual.lower().replace(" ", "").replace("_", "")
                    for actual in actual_workflows
                )
                if found:
                    generated_workflows.append(expected["name"])
                else:
                    missing_workflows.append(expected["name"])

            if generated_workflows:
                report_lines.append(f"✅ **Generated** ({len(generated_workflows)}):")
                for name in generated_workflows:
                    report_lines.append(f"   - {name}")

            if missing_workflows:
                report_lines.append(
                    f"\n⚠️ **Possibly Missing** ({len(missing_workflows)}):"
                )
                for name in missing_workflows:
                    report_lines.append(f"   - {name}")

        # Recommendations
        if missing_entities or missing_workflows:
            report_lines.append("\n### 💡 Recommendations")
            report_lines.append(
                "Some items from your requirements may not have been generated. This can happen because:"
            )
            report_lines.append(
                "1. **Large requirements**: The generation may have hit context/timeout limits"
            )
            report_lines.append(
                "2. **Name variations**: The items may exist with slightly different names"
            )
            report_lines.append(
                "3. **Merged items**: Some items may have been combined"
            )
            report_lines.append("\n**Next steps:**")
            report_lines.append(
                "- Review the generated code in the Canvas to verify what was created"
            )
            report_lines.append(
                "- If items are truly missing, you can ask me to generate them individually"
            )
            report_lines.append(
                "- Consider breaking large requirements into smaller sections for better results"
            )
        else:
            report_lines.append(
                "\n✅ All expected items appear to have been generated!"
            )

        return "\n".join(report_lines)


__all__ = ["GenerationValidator"]
