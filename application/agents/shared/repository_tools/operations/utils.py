"""Utility functions for build generation."""

import logging
from pathlib import Path
from typing import Optional

from application.agents.shared.prompt_loader import load_template

logger = logging.getLogger(__name__)

# Constants
DEFAULT_REPOSITORY_NAME = "mcp-cyoda-quart-app"
PYTHON_REPO_NAME = "mcp-cyoda-quart-app"
JAVA_REPO_NAME = "java-client-template"


def _get_requirements_directory_path(language: str, repository_path: str) -> str:
    """Get the requirements directory path for the given language.

    Args:
        language: Programming language.
        repository_path: Repository path.

    Returns:
        Path to requirements directory.
    """
    requirements_dir = Path(repository_path) / "requirements"
    if language.lower() == "java":
        requirements_dir = requirements_dir / "java"
    elif language.lower() == "python":
        requirements_dir = requirements_dir / "python"

    return str(requirements_dir)


async def _check_requirements_exist(language: str, repository_path: str) -> str:
    """Check if requirements files exist for the language.

    Args:
        language: Programming language.
        repository_path: Repository path.

    Returns:
        Empty string if requirements exist, error message otherwise.
    """
    requirements_dir = _get_requirements_directory_path(language, repository_path)
    requirements_path = Path(requirements_dir)

    logger.info(f"Checking for requirements in: {requirements_path}")

    if not requirements_path.exists():
        logger.error(f"Requirements directory not found: {requirements_path}")
        return (
            f"ERROR: Requirements directory not found at {requirements_path}. "
            f"Ensure you have requirements/{language.lower()}/ directory in your repository."
        )

    # Check for at least one requirements file
    if language.lower() == "python":
        requirements_file = requirements_path / "requirements.txt"
        if not requirements_file.exists():
            logger.warning(f"requirements.txt not found at {requirements_file}")
    elif language.lower() == "java":
        pom_file = requirements_path / "pom.xml"
        if not pom_file.exists():
            logger.warning(f"pom.xml not found at {pom_file}")

    logger.info(f"✅ Requirements directory verified at: {requirements_path}")
    return ""


def _build_augment_command(
    language: str,
    repository_path: str,
    branch_name: str,
    augment_model: str,
) -> list[str]:
    """Build the augment CLI command.

    Args:
        language: Programming language.
        repository_path: Repository path.
        branch_name: Branch name.
        augment_model: Augment model to use.

    Returns:
        List of command arguments.
    """
    # Get the requirements directory
    requirements_dir = _get_requirements_directory_path(language, repository_path)

    # Build command
    command = [
        "augment",
        "generate",
        f"--language={language}",
        f"--repo-path={repository_path}",
        f"--branch={branch_name}",
        f"--requirements-dir={requirements_dir}",
        f"--model={augment_model}",
    ]

    logger.info(f"Built augment command: {' '.join(command)}")
    return command


def _build_repository_url(
    repository_owner: Optional[str],
    repository_name: Optional[str],
    branch_name: Optional[str],
) -> str:
    """Build GitHub repository URL from components.

    Args:
        repository_owner: Repository owner.
        repository_name: Repository name.
        branch_name: Branch name.

    Returns:
        GitHub URL to the branch.
    """
    if not repository_owner or not repository_name or not branch_name:
        return ""

    return f"https://github.com/{repository_owner}/{repository_name}/tree/{branch_name}"


def _format_success_response(
    repository_owner: Optional[str],
    repository_name: Optional[str],
    branch_name: Optional[str],
    repository_path: str,
) -> str:
    """Format a success response message.

    Args:
        repository_owner: Repository owner.
        repository_name: Repository name.
        branch_name: Branch name.
        repository_path: Repository path.

    Returns:
        Formatted success message.
    """
    github_url = _build_repository_url(repository_owner, repository_name, branch_name)

    if github_url:
        return (
            f"✅ Application generated successfully!\n\n"
            f"📦 Repository: {repository_owner}/{repository_name}\n"
            f"🌿 Branch: {branch_name}\n"
            f"🔗 GitHub URL: {github_url}\n"
            f"📂 Local path: {repository_path}"
        )

    return f"✅ Application generated successfully at {repository_path}"


async def _load_prompt_template(language: str) -> str:
    """Load prompt template for the given language.

    Args:
        language: Programming language.

    Returns:
        Prompt template content.

    Raises:
        ValueError: If language is not supported.
    """
    if language.lower() == "python":
        return load_template("generation/python_generation_prompt")
    elif language.lower() == "java":
        return load_template("generation/java_generation_prompt")
    else:
        raise ValueError(f"Unsupported language: {language}")
