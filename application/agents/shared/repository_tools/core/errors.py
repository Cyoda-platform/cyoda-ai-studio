"""Error message builders for repository operations."""


def _build_missing_context_error() -> str:
    """Build error message for missing tool context."""
    return (
        "❌ Repository configuration required before cloning.\n\n"
        "Tool context is not available. Please ensure you're using this tool within a proper "
        "conversation context and have configured your repository settings using `set_repository_config()`."
    )


def _build_no_config_error() -> str:
    """Build error message for missing repository configuration."""
    return (
        "❌ Repository configuration required before cloning.\n\n"
        "Please specify your repository type first:\n\n"
        "**For Public Repositories (Cyoda templates):**\n"
        "Use: `set_repository_config(repository_type='public')`\n"
        "This will use Cyoda's public templates and push to the public repository.\n\n"
        "**For Private Repositories:**\n"
        "Use: `set_repository_config(repository_type='private', "
        "installation_id='YOUR_ID', repository_url='YOUR_REPO_URL')`\n"
        "This requires your GitHub App to be installed on your private repository.\n\n"
        "💡 **Need help?** The repository type determines where your code will be stored and pushed."
    )


def _build_invalid_repo_type_error(repo_type: str) -> str:
    """Build error message for invalid repository type.

    Args:
        repo_type: Invalid repository type value

    Returns:
        Error message string
    """
    return f"Invalid repository_type '{repo_type}'. Must be 'public' or 'private'."
