"""Helpers specific to application build operations."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

# NOTE: load_template import kept local to functions for test mocking compatibility

logger = logging.getLogger(__name__)


def _get_requirements_path(language: str, repository_path: str) -> str:
    """Get functional requirements directory path for language.

    Args:
        language: Programming language
        repository_path: Repository path

    Returns:
        Requirements directory path
    """
    if language.lower() == "python":
        return f"{repository_path}/application/resources/functional_requirements"
    elif language.lower() == "java":
        return f"{repository_path}/src/main/resources/functional_requirements"
    else:
        raise ValueError(f"Unsupported language: {language}")


def _check_functional_requirements_exist(
    language: str, repository_path: str
) -> tuple[bool, int, Optional[str]]:
    """Check if functional requirements exist in repository.

    Args:
        language: Programming language
        repository_path: Repository path

    Returns:
        Tuple of (has_requirements, file_count, error_message)
    """
    try:
        requirements_path = _get_requirements_path(language, repository_path)
    except ValueError as e:
        return False, 0, str(e)

    requirements_dir = Path(requirements_path)

    if not requirements_dir.exists() or not requirements_dir.is_dir():
        return False, 0, None

    requirement_files = list(requirements_dir.glob("*"))
    file_count = len(requirement_files)

    if file_count > 0:
        logger.info(f"✅ Found {file_count} functional requirement file(s)")
        return True, file_count, None

    return False, 0, None


def _create_missing_requirements_message(requirements_path: str) -> str:
    """Create message for missing functional requirements.

    Args:
        requirements_path: Path where requirements should be

    Returns:
        Formatted error message
    """
    return (
        f"⚠️ No functional requirements found in {requirements_path}\n\n"
        f"Before we can build your application, we need to create functional requirements together. "
        f"Functional requirements describe what your application should do.\n\n"
        f"**Next steps:**\n"
        f"1. Let's design your application requirements together\n"
        f"2. I'll help you create a comprehensive requirements document\n"
        f"3. Then we can generate the application code\n\n"
        f"Would you like to start building requirements together?"
    )


def _load_build_prompt_template(language: str) -> tuple[bool, str, Optional[str]]:
    """Load build prompt template for language.

    Args:
        language: Programming language

    Returns:
        Tuple of (success, template_content, error_message)
    """
    # Local import for test mocking compatibility
    from application.agents.github.prompts import load_template

    # Try optimized template first
    template_name = f"build_{language.lower()}_instructions_optimized"
    try:
        prompt_template = load_template(template_name)
        logger.info(
            f"Loaded optimized prompt template for {language} ({len(prompt_template)} chars)"
        )
        return True, prompt_template, None
    except FileNotFoundError:
        logger.debug(f"Optimized template not found, trying standard template")
    except Exception as e:
        logger.warning(
            f"Failed to load optimized template: {e}, trying standard template"
        )

    # Fallback to standard template
    template_name = f"build_{language.lower()}_instructions"
    try:
        prompt_template = load_template(template_name)
        logger.info(
            f"Loaded standard prompt template for {language} ({len(prompt_template)} chars)"
        )
        return True, prompt_template, None
    except Exception as e:
        logger.error(f"Failed to load prompt template '{template_name}': {e}")
        error_msg = f"ERROR: Failed to load prompt template for {language}: {str(e)}"
        return False, "", error_msg


def _load_pattern_catalog(language: str) -> str:
    """Load pattern catalog for language.

    Args:
        language: Programming language

    Returns:
        Pattern catalog content (empty string if not found)
    """
    if language.lower() != "python":
        return ""

    # Local import for test mocking compatibility
    from application.agents.github.prompts import load_template

    try:
        pattern_catalog = load_template("python_patterns")
        logger.info(f"Loaded pattern catalog ({len(pattern_catalog)} chars)")
        return pattern_catalog
    except FileNotFoundError:
        logger.warning("Pattern catalog not found, proceeding without it")
        return ""
    except Exception as e:
        logger.warning(f"Failed to load pattern catalog: {e}")
        return ""


def _build_full_prompt(template: str, pattern_catalog: str, requirements: str) -> str:
    """Build full prompt from template, catalog, and requirements.

    Args:
        template: Prompt template
        pattern_catalog: Pattern catalog (optional)
        requirements: User requirements

    Returns:
        Complete prompt
    """
    if pattern_catalog:
        return (
            f"{template}\n\n---\n\n{pattern_catalog}\n\n"
            f"## User Requirements:\n{requirements}"
        )
    else:
        return f"{template}\n\n## User Requirements:\n{requirements}"
