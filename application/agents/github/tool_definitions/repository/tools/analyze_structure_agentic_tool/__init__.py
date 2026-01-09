"""Tool for agentic repository analysis using Unix commands.

This module demonstrates intelligent repository analysis using Unix commands,
allowing the AI to create custom analysis strategies.

Internal organization:
- validation.py: Context and path validation, result initialization
- analysis.py: Entity, workflow, and requirements analysis
- command_execution.py: Command execution and tracking
"""

from __future__ import annotations

import json
import logging

from google.adk.tools.tool_context import ToolContext

from .analysis import (
    _analyze_directory_structure,
    _analyze_entity_files,
    _analyze_requirement_files,
    _analyze_workflow_files,
)
from .command_execution import (
    _execute_and_track_command,
)
from .validation import (
    _generate_analysis_summary,
    _initialize_results,
    _validate_context_and_path,
)

logger = logging.getLogger(__name__)


async def analyze_repository_structure_agentic(tool_context: ToolContext) -> str:
    """Analyze repository structure using Unix commands.

    Demonstrates intelligent repository analysis by executing Unix commands
    to discover and analyze entities, workflows, and requirements.

    Args:
        tool_context: Execution context.

    Returns:
        JSON string with comprehensive repository analysis.
    """
    try:
        repository_path = _validate_context_and_path(tool_context)
        logger.info("🤖 Starting agentic repository analysis using Unix commands...")

        # Initialize results container
        commands_executed = []
        analysis_results = _initialize_results(repository_path)

        # Analyze JSON files (entities and workflows)
        json_data, json_cmd = await _execute_and_track_command(
            "find . -name '*.json' -type f | sort", "Find all JSON files", tool_context
        )
        commands_executed.append(json_cmd)

        if json_data.get("success"):
            json_files = [
                f.strip() for f in json_data["stdout"].split("\n") if f.strip()
            ]

            # Analyze entities
            entity_files = [f for f in json_files if "/entity/" in f]
            analysis_results["entities"] = await _analyze_entity_files(
                entity_files, tool_context
            )

            # Analyze workflows
            workflow_files = [f for f in json_files if "/workflow" in f]
            analysis_results["workflows"] = await _analyze_workflow_files(
                workflow_files, tool_context
            )

        # Analyze requirements files
        req_data, req_cmd = await _execute_and_track_command(
            "find . -path '*/functional_requirements/*' -type f | sort",
            "Find requirements files (all textual formats)",
            tool_context,
        )
        commands_executed.append(req_cmd)

        if req_data.get("success"):
            req_files = [f.strip() for f in req_data["stdout"].split("\n") if f.strip()]
            analysis_results["requirements"] = await _analyze_requirement_files(
                req_files, tool_context
            )

        # Analyze directory structure
        directories = await _analyze_directory_structure(tool_context)
        analysis_results["structure"]["directories"] = directories

        # Generate summary
        analysis_results["commands_executed"] = commands_executed
        analysis_results["summary"] = _generate_analysis_summary(
            analysis_results["entities"],
            analysis_results["workflows"],
            analysis_results["requirements"],
            commands_executed,
        )

        # Log results
        summary = analysis_results["summary"]
        logger.info(
            f"🤖 Agentic analysis complete: {summary['unique_entities']} entities, "
            f"{summary['unique_workflows']} workflows, {summary['requirements_files']} requirements"
        )

        return json.dumps(analysis_results, indent=2)

    except ValueError as e:
        error_response = {"error": str(e)}
        logger.error(f"Validation error in repository analysis: {e}")
        return json.dumps(error_response)
    except Exception as e:
        error_response = {"error": str(e)}
        logger.error(f"Error in agentic repository analysis: {e}", exc_info=True)
        return json.dumps(error_response)


__all__ = [
    "analyze_repository_structure_agentic",
    # Re-export from submodules
    "_validate_context_and_path",
    "_initialize_results",
    "_generate_analysis_summary",
    "_analyze_entity_files",
    "_analyze_workflow_files",
    "_analyze_requirement_files",
    "_analyze_directory_structure",
    "_execute_and_track_command",
]
