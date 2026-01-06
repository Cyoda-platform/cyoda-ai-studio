"""Tool for agentic repository analysis using Unix commands.

This module demonstrates intelligent repository analysis using Unix commands,
allowing the AI to create custom analysis strategies.
"""

from __future__ import annotations

# Re-export from analyze_structure_agentic_tool package for backward compatibility
from .analyze_structure_agentic_tool import (
    analyze_repository_structure_agentic,
    _validate_context_and_path,
    _initialize_results,
    _generate_analysis_summary,
    _analyze_entity_files,
    _analyze_workflow_files,
    _analyze_requirement_files,
    _analyze_directory_structure,
    _execute_and_track_command,
)

__all__ = [
    "analyze_repository_structure_agentic",
    "_validate_context_and_path",
    "_initialize_results",
    "_generate_analysis_summary",
    "_analyze_entity_files",
    "_analyze_workflow_files",
    "_analyze_requirement_files",
    "_analyze_directory_structure",
    "_execute_and_track_command",
]
