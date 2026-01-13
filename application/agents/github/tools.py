"""Tools for GitHub agent - thin registry importing from tool_definitions/."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from google.adk.tools.tool_context import ToolContext

from application.agents.github.tool_definitions.code_generation import (
    generate_application,
    generate_code_with_cli,
)
from application.agents.github.tool_definitions.code_generation import (
    load_informational_prompt_template as _load_informational_prompt_template,
)
from application.agents.github.tool_definitions.code_generation import (
    monitor_build_process as _monitor_build_process,
)
from application.agents.github.tool_definitions.code_generation import (
    monitor_code_generation_process as _monitor_code_generation_process,
)
from application.agents.github.tool_definitions.code_generation.helpers import (
    cleanup_temp_files as _cleanup_temp_files,
)
from application.agents.github.tool_definitions.code_generation.helpers import (
    monitor_cli_process as _monitor_cli_process,
)

# Re-export all public tools and constants
from application.agents.github.tool_definitions.common.constants import (
    EXT_JSON,
    PROJECT_TYPE_JAVA,
    PROJECT_TYPE_PYTHON,
    RESOURCE_TYPE_ENTITY,
    RESOURCE_TYPE_WORKFLOW,
    STOP_ON_ERROR,
    VERSION_DIR_PREFIX,
)
from application.agents.github.tool_definitions.common.utils import (
    AUGGIE_CLI_SCRIPT,
    JAVA_RESOURCES_PATH,
    PYTHON_RESOURCES_PATH,
    detect_project_type,
    get_cli_config,
    is_textual_file,
)
from application.agents.github.tool_definitions.git import (
    _commit_and_push_changes,
    commit_and_push_changes,
)
from application.agents.github.tool_definitions.repository import (
    analyze_repository_structure,
    analyze_repository_structure_agentic,
    execute_unix_command,
    get_repository_diff,
    pull_repository_changes,
    save_file_to_repository,
    search_repository_files,
)
from application.agents.github.tool_definitions.repository.helpers import (
    get_github_service_from_context as _get_github_service_from_context,
)
from application.agents.github.tool_definitions.repository.helpers import (
    scan_versioned_resources,
)

# open_canvas_tab removed - UI auto-detects canvas resources
from application.agents.github.tool_definitions.security import (
    validate_command_security,
)
from application.agents.github.tool_definitions.workflow import (
    load_workflow_example,
    load_workflow_prompt,
    load_workflow_schema,
    validate_workflow_against_schema,
)

# Re-export shared utilities (for tests and backward compatibility)
from application.agents.shared.process_utils import _is_process_running
from application.agents.shared.prompt_loader import load_template
from application.agents.shared.repository_tools import _terminate_process
from common.config.config import AUGMENT_MODEL, CLAUDE_MODEL, CLI_PROVIDER, GEMINI_MODEL
from services.services import get_entity_service

# ============================================================================
# BACKWARD COMPATIBILITY WRAPPERS
# ============================================================================


def _get_cli_config(provider: str = None) -> tuple[Path, str]:
    return get_cli_config(provider)


def _is_textual_file(filename: str) -> bool:
    return is_textual_file(filename)


def _detect_project_type(repo_path: str) -> Dict[str, str]:
    return detect_project_type(repo_path)


def _scan_versioned_resources(
    resources_dir: Path, resource_type: str, repo_path_obj: Path
) -> List[Dict[str, Any]]:
    return scan_versioned_resources(resources_dir, resource_type, repo_path_obj)


async def get_entity_path(entity_name: str, version: int, project_type: str) -> str:
    from application.agents.github.tool_definitions.common.utils.path_utils import (
        get_entity_path as _get_entity_path,
    )

    return _get_entity_path(entity_name, version, project_type)


async def get_workflow_path(
    workflow_name: str, project_type: str, version: int = 1
) -> str:
    from application.agents.github.tool_definitions.common.utils.path_utils import (
        get_workflow_path as _get_workflow_path,
    )

    return _get_workflow_path(workflow_name, project_type, version)


async def get_requirements_path(requirements_name: str, project_type: str) -> str:
    from application.agents.github.tool_definitions.common.utils.path_utils import (
        get_requirements_path as _get_requirements_path,
    )

    return _get_requirements_path(requirements_name, project_type)


async def _validate_command_security(command: str, repo_path: str) -> Dict[str, Any]:
    return await validate_command_security(command, repo_path)


# Alias for backward compatibility
generate_code_with_auggie = generate_code_with_cli
