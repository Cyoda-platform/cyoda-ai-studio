"""Tool for validating functional requirements consolidation.

This tool checks that consolidated FR documents match source documents.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from application.agents.shared.repository_tools.fr_validator import FRValidator

logger = logging.getLogger(__name__)


async def validate_fr_consolidation(
    source_documents_dir: Optional[str] = None,
    consolidated_fr_filename: Optional[str] = None,
    language: Optional[str] = None,
    repository_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Validate that consolidated functional requirements match source documents.

    This tool should be called after consolidating multiple requirement documents
    into a single functional requirements document. It verifies that key requirements
    from all source documents are present in the consolidated version.

    Use cases:
    - After consolidating multiple uploaded requirement documents
    - Before proceeding with code generation from consolidated FR
    - When user questions if their requirements were properly consolidated

    Args:
        source_documents_dir: Directory containing source requirement documents.
                            If not provided, looks for "uploaded_requirements" in repo.
        consolidated_fr_filename: Name of consolidated FR file (e.g., "functional_requirements.md").
                                If not provided, looks for any .md file in FR directory.
        language: Programming language ("python" or "java"). Auto-detected if not provided.
        repository_path: Path to local repository. Uses context if not provided.
        tool_context: ADK tool context for accessing state and LLM client

    Returns:
        Validation report showing which requirements were matched and which are missing
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

        # Determine FR directory based on language
        if language.lower() == "python":
            fr_dir = f"{repository_path}/application/resources/functional_requirements"
        elif language.lower() == "java":
            fr_dir = f"{repository_path}/src/main/resources/functional_requirements"
        else:
            return f"ERROR: Unsupported language: {language}"

        # Default source documents directory
        if not source_documents_dir:
            source_documents_dir = f"{repository_path}/uploaded_requirements"
            # Also check if it's in FR dir as a subdirectory
            if not os.path.exists(source_documents_dir):
                source_documents_dir = f"{fr_dir}/source_documents"

        # Find consolidated FR file
        if not consolidated_fr_filename:
            # Look for any .md file in FR directory (excluding source subdirs)
            import glob

            fr_files = glob.glob(f"{fr_dir}/*.md")
            if not fr_files:
                return (
                    f"⚠️ No consolidated FR file found in {fr_dir}.\n\n"
                    f"Please ensure a consolidated functional requirements document exists."
                )
            # Use the first one found
            consolidated_fr_path = fr_files[0]
            consolidated_fr_filename = os.path.basename(consolidated_fr_path)
        else:
            consolidated_fr_path = f"{fr_dir}/{consolidated_fr_filename}"

        if not os.path.exists(consolidated_fr_path):
            return (
                f"⚠️ Consolidated FR file not found: {consolidated_fr_path}\n\n"
                f"Please ensure the file exists before validating."
            )

        logger.info(
            f"🔍 Validating FR consolidation: {source_documents_dir} -> {consolidated_fr_filename}"
        )

        # Get LLM client from context for advanced validation
        llm_client = None
        if tool_context and hasattr(tool_context, "llm_client"):
            llm_client = tool_context.llm_client

        # Run validation
        validation_passed, report = await FRValidator.validate_fr_consolidation(
            source_documents_dir=source_documents_dir,
            consolidated_fr_path=consolidated_fr_path,
            llm_client=llm_client,
        )

        logger.info(
            f"📋 FR Validation {'passed' if validation_passed else 'needs review'}"
        )
        return report

    except Exception as e:
        logger.error(f"Error validating FR consolidation: {e}", exc_info=True)
        return f"ERROR: Failed to validate FR consolidation: {str(e)}"
