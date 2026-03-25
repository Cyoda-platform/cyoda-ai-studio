"""Tool for verifying repository integrity after pull or other operations.

This tool checks that the repository structure is complete and reports any issues.
"""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.repository.helpers import (
    get_github_service_from_context,
)
from application.agents.shared.repository_tools.generation_validator import (
    GenerationValidator,
)
from application.services.github.github_service import GitHubService
from application.services.repository_parser.service import RepositoryParser

logger = logging.getLogger(__name__)


async def verify_repository_integrity(
    language: Optional[str] = None,
    repository_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Verify repository integrity after pull or generation.

    This tool checks the repository structure and reports:
    - Total entities and workflows found
    - Any parsing errors encountered
    - Comparison with functional requirements (if available)

    Useful after:
    - Git pull operations
    - Code generation
    - Manual file modifications

    Args:
        language: Programming language ("python" or "java"). Auto-detected if not provided.
        repository_path: Path to local repository. Uses context if not provided.
        tool_context: ADK tool context for accessing state

    Returns:
        Detailed validation report with repository status
    """
    try:
        # Get parameters from context if not provided
        if tool_context:
            if not repository_path:
                repository_path = tool_context.state.get("repository_path")
            if not language:
                language = tool_context.state.get("language", "python")

        if not repository_path:
            return "ERROR: repository_path not found. Repository must be cloned first."

        if not tool_context:
            return "ERROR: tool_context is required for repository verification."

        # Get GitHub service from context
        github_service: GitHubService = await get_github_service_from_context(
            tool_context
        )

        # Get repository info from context
        repository_name = tool_context.state.get("repository_name")
        branch_name = tool_context.state.get("branch_name")

        if not repository_name or not branch_name:
            return "ERROR: repository_name or branch_name not found in context."

        logger.info(
            f"🔍 Verifying repository integrity: {repository_name} (branch: {branch_name})"
        )

        # Parse repository structure
        parser = RepositoryParser(github_service)
        repo_structure = await parser.parse_repository(repository_name, branch_name)

        # Count entities and workflows
        entity_count = len(repo_structure.entities)
        workflow_count = len(repo_structure.workflows)

        logger.info(f"📊 Found {entity_count} entities, {workflow_count} workflows")

        # Build basic report
        report_lines = [
            "✅ Repository Integrity Check Complete",
            "",
            "### Summary",
            f"- **App Type**: {repo_structure.app_type}",
            f"- **Entities Found**: {entity_count}",
            f"- **Workflows Found**: {workflow_count}",
            f"- **Requirements Found**: {len(repo_structure.requirements)}",
            "",
        ]

        # List entities
        if entity_count > 0:
            report_lines.append("### Entities")
            for entity in repo_structure.entities:
                report_lines.append(f"  ✅ {entity.name} (v{entity.version})")
            report_lines.append("")

        # List workflows
        if workflow_count > 0:
            report_lines.append("### Workflows")
            for workflow in repo_structure.workflows:
                report_lines.append(
                    f"  ✅ {workflow.entity_name} v{workflow.version} - {workflow.workflow_file}"
                )
            report_lines.append("")

        # Try to validate against functional requirements if available
        validation_attempted = False
        if len(repo_structure.requirements) > 0:
            logger.info("📋 Functional requirements found, running validation...")
            try:
                validation_passed, validation_report = (
                    await GenerationValidator.validate_generation(
                        language=language,
                        repository_path=repository_path,
                        tool_context=tool_context,
                    )
                )
                validation_attempted = True

                report_lines.append("### Validation Against Requirements")
                report_lines.append("")
                report_lines.append(validation_report)

            except Exception as e:
                logger.warning(f"⚠️ Could not validate against requirements: {e}")
                report_lines.append("### Validation Against Requirements")
                report_lines.append(f"⚠️ Could not validate: {e}")
                report_lines.append("")

        # Add recommendations
        report_lines.append("### Recommendations")
        if entity_count == 0 and workflow_count == 0:
            report_lines.append(
                "⚠️ No entities or workflows found. Repository may be empty or parsing failed."
            )
            report_lines.append(
                "   - Check that files are in the correct directory structure"
            )
            report_lines.append("   - Review backend logs for parsing errors")
        elif not validation_attempted and len(repo_structure.requirements) == 0:
            report_lines.append(
                "ℹ️ No functional requirements found. Cannot validate completeness."
            )
            report_lines.append(
                "   - If requirements exist, ensure they are in the correct path"
            )
        else:
            report_lines.append("✅ Repository structure looks good!")

        report = "\n".join(report_lines)
        logger.info(f"📋 Integrity check complete:\n{report}")
        return report

    except Exception as e:
        logger.error(f"Error verifying repository integrity: {e}", exc_info=True)
        return f"ERROR: Failed to verify repository integrity: {str(e)}"
