"""Input and context validation for file operations."""

import logging
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def _validate_files_input(files: list[dict[str, str]]) -> None:
    """Validate that files list has required format.

    Args:
        files: List of file dictionaries to validate.

    Raises:
        ValueError: If files list is invalid or missing required fields.
    """
    if not files or len(files) == 0:
        raise ValueError(
            "files parameter is required and must contain at least one file"
        )

    for i, file_dict in enumerate(files):
        if "filename" not in file_dict:
            raise ValueError(f"File at index {i} is missing required 'filename' field")
        if "content" not in file_dict:
            raise ValueError(f"File at index {i} is missing required 'content' field")


def _validate_tool_context_state(tool_context: ToolContext) -> dict[str, str]:
    """Validate tool context and extract required state values.

    Args:
        tool_context: Execution context containing repository configuration.

    Returns:
        Dictionary with validated state values.

    Raises:
        ValueError: If required state values are missing or invalid.
    """
    if not tool_context:
        raise ValueError("tool_context not available")

    repository_path = tool_context.state.get("repository_path")
    branch_name = tool_context.state.get("branch_name")
    language = tool_context.state.get("language")
    repository_type = tool_context.state.get("repository_type")
    user_repository_url = tool_context.state.get("user_repository_url")
    installation_id = tool_context.state.get("installation_id")

    # Require explicit repository type configuration
    if repository_type is None:
        error_msg = (
            f"❌ Repository type not configured.\n\n"
            f"This usually means the repository was not properly cloned with `clone_repository()` "
            f"or the repository configuration was not set with `set_repository_config()`.\n\n"
            f"Please ensure you have called `set_repository_config()` with either:\n"
            f"- `repository_type='public'` for Cyoda public repositories\n"
            f"- `repository_type='private'` with your installation_id and repository_url"
        )
        logger.error("⚠️ No repository type found in context for commit/push operation")
        raise ValueError(error_msg)

    if not repository_path:
        raise ValueError(
            "Repository path not found in context. Please call clone_repository first."
        )
    if not branch_name:
        raise ValueError(
            "Branch name not found in context. Please call clone_repository first."
        )
    if not language:
        raise ValueError(
            "Language not found in context. Please call clone_repository first."
        )

    return {
        "repository_path": repository_path,
        "branch_name": branch_name,
        "language": language,
        "repository_type": repository_type,
        "user_repository_url": user_repository_url,
        "installation_id": installation_id,
    }


def _determine_functional_requirements_dir(repo_path: Path, language: str) -> Path:
    """Determine the functional requirements directory based on language.

    Args:
        repo_path: Root path of the repository.
        language: Programming language (java or python).

    Returns:
        Path to the functional requirements directory.

    Raises:
        ValueError: If language is not supported.
    """
    if language.lower() == "java":
        return repo_path / "src" / "main" / "resources" / "functional_requirements"
    elif language.lower() == "python":
        return repo_path / "application" / "resources" / "functional_requirements"
    else:
        raise ValueError(f"Unsupported language '{language}'. Supported: java, python")
