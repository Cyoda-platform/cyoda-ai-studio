"""File operations for repository management - saving files to branches and repositories."""

import logging
from pathlib import Path
from typing import Optional

from google.adk.tools.tool_context import ToolContext

# Re-export dependencies (for test mocking)
from application.agents.shared.repository_tools.git_operations import _get_authenticated_repo_url_sync

# Re-export all components
from .validation import (
    _validate_files_input,
    _validate_tool_context_state,
    _determine_functional_requirements_dir,
)
from .file_operations import (
    _save_file_to_disk,
    _log_directory_debug_info,
    _save_all_files,
)
from .git_workflow import (
    _configure_git_user,
    _add_files_to_git,
    _check_git_status,
    _commit_files_to_git,
    _update_remote_authentication,
    _push_to_remote,
    _commit_and_push_files,
)

__all__ = [
    # Dependencies (for test mocking)
    "_get_authenticated_repo_url_sync",
    # Validation
    "_validate_files_input",
    "_validate_tool_context_state",
    "_determine_functional_requirements_dir",
    # File operations
    "_save_file_to_disk",
    "_log_directory_debug_info",
    "_save_all_files",
    # Git workflow
    "_configure_git_user",
    "_add_files_to_git",
    "_check_git_status",
    "_commit_files_to_git",
    "_update_remote_authentication",
    "_push_to_remote",
    "_commit_and_push_files",
    # Public API
    "save_files_to_branch",
]

logger = logging.getLogger(__name__)


async def save_files_to_branch(
    files: list[dict[str, str]],
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Save files to functional requirements directory and push to branch.

    Files are saved to language-specific directories:
    - Java: src/main/resources/functional_requirements/
    - Python: application/resources/functional_requirements/

    After saving, files are committed and pushed to the specified branch.

    Args:
        files: List of file dictionaries with 'filename' and 'content' keys.
        tool_context: Execution context (auto-injected).

    Returns:
        Status message indicating success or error.
    """
    # Validate inputs upfront (fail fast principle)
    _validate_files_input(files)

    try:
        # Extract and validate context state
        state = _validate_tool_context_state(tool_context)

        repo_path = Path(state["repository_path"])
        branch_name = state["branch_name"]
        language = state["language"]
        repository_type = state["repository_type"]
        user_repository_url = state["user_repository_url"]
        installation_id = state["installation_id"]

        # Validate repository exists
        if not repo_path.exists():
            return f"ERROR: Repository directory does not exist: {repo_path}"

        # Determine target directory and save files
        func_req_dir = _determine_functional_requirements_dir(repo_path, language)
        func_req_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created/verified functional requirements directory: {func_req_dir}")

        saved_files = await _save_all_files(files, func_req_dir)
        if not saved_files:
            return "ERROR: No valid files were provided to save"

        # Commit and push to repository
        return await _commit_and_push_files(
            repo_path=repo_path,
            branch_name=branch_name,
            func_req_dir=func_req_dir,
            saved_files=saved_files,
            repository_type=repository_type,
            language=language,
            user_repository_url=user_repository_url,
            installation_id=installation_id,
        )

    except ValueError as e:
        return f"ERROR: {str(e)}"
    except Exception as e:
        logger.error(f"❌ Failed to save files to branch: {e}", exc_info=True)
        return f"ERROR: Failed to save files to branch: {str(e)}"
