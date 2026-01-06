"""Formatters for setup tools."""

from __future__ import annotations


def format_setup_context(
    programming_language: str,
    git_branch: str,
    repository_name: str,
    entity_name: str | None = None,
) -> str:
    """Format setup context confirmation message.

    Args:
        programming_language: Programming language
        git_branch: Git branch
        repository_name: Repository name
        entity_name: Optional entity name

    Returns:
        Formatted confirmation message
    """
    entity_line = f"\n- Entity Name: {entity_name}" if entity_name else ""

    return f"""Setup context configured:
- Programming Language: {programming_language}
- Git Branch: {git_branch}
- Repository: {repository_name}{entity_line}

Now I'll provide you with detailed step-by-step setup instructions."""
