"""Tools for GitHub agent - thin registry importing from tool_definitions/."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from google.adk.tools.tool_context import ToolContext

# Re-export shared utilities (for tests and backward compatibility)
from application.agents.shared.process_utils import _is_process_running
from application.agents.shared.repository_tools import _terminate_process
from application.agents.shared.prompt_loader import load_template
from services.services import get_entity_service
from common.config.config import CLI_PROVIDER, AUGMENT_MODEL, CLAUDE_MODEL, GEMINI_MODEL

# Re-export all public tools and constants
from application.agents.github.tool_definitions.common.constants import (
    STOP_ON_ERROR,
    PROJECT_TYPE_PYTHON,
    PROJECT_TYPE_JAVA,
    EXT_JSON,
    RESOURCE_TYPE_ENTITY,
    RESOURCE_TYPE_WORKFLOW,
    VERSION_DIR_PREFIX,
)
from application.agents.github.tool_definitions.common.utils import (
    is_textual_file,
    detect_project_type,
    get_cli_config,
    PYTHON_RESOURCES_PATH,
    JAVA_RESOURCES_PATH,
    AUGGIE_CLI_SCRIPT,
)
from application.agents.github.tool_definitions.repository.helpers import (
    scan_versioned_resources,
    get_github_service_from_context as _get_github_service_from_context,
)
from application.agents.github.tool_definitions.repository import (
    save_file_to_repository,
    get_repository_diff,
    search_repository_files,
    execute_unix_command,
    pull_repository_changes,
    analyze_repository_structure,
    analyze_repository_structure_agentic,
)
from application.agents.github.tool_definitions.git import (
    commit_and_push_changes,
    _commit_and_push_changes,
)
from application.agents.github.tool_definitions.code_generation import (
    generate_code_with_cli,
    generate_application,
    load_informational_prompt_template as _load_informational_prompt_template,
    monitor_code_generation_process as _monitor_code_generation_process,
    monitor_build_process as _monitor_build_process,
)
from application.agents.github.tool_definitions.code_generation.helpers import (
    monitor_cli_process as _monitor_cli_process,
    cleanup_temp_files as _cleanup_temp_files,
)
from application.agents.github.tool_definitions.workflow import (
    validate_workflow_against_schema,
    load_workflow_schema,
    load_workflow_example,
    load_workflow_prompt,
)
from application.agents.github.tool_definitions.canvas import open_canvas_tab
from application.agents.github.tool_definitions.security import validate_command_security


# ============================================================================
# BACKWARD COMPATIBILITY WRAPPERS
# ============================================================================

def _get_cli_config(provider: str = None) -> tuple[Path, str]:
    return get_cli_config(provider)


def _is_textual_file(filename: str) -> bool:
    return is_textual_file(filename)


def _detect_project_type(repo_path: str) -> Dict[str, str]:
    return detect_project_type(repo_path)


def _scan_versioned_resources(resources_dir: Path, resource_type: str, repo_path_obj: Path) -> List[Dict[str, Any]]:
    return scan_versioned_resources(resources_dir, resource_type, repo_path_obj)


async def get_entity_path(entity_name: str, version: int, project_type: str) -> str:
    from application.agents.github.tool_definitions.common.utils.path_utils import get_entity_path as _get_entity_path
    return _get_entity_path(entity_name, version, project_type)


async def get_workflow_path(workflow_name: str, project_type: str, version: int = 1) -> str:
    from application.agents.github.tool_definitions.common.utils.path_utils import (
        get_workflow_path as _get_workflow_path
    )
    return _get_workflow_path(workflow_name, project_type, version)


async def get_requirements_path(requirements_name: str, project_type: str) -> str:
    from application.agents.github.tool_definitions.common.utils.path_utils import (
        get_requirements_path as _get_requirements_path
    )
    return _get_requirements_path(requirements_name, project_type)


async def _validate_command_security(command: str, repo_path: str) -> Dict[str, Any]:
    return await validate_command_security(command, repo_path)


# Alias for backward compatibility
generate_code_with_auggie = generate_code_with_cli
