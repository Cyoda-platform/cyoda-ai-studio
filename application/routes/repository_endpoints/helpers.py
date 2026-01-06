"""Helper functions for repository endpoints."""

import logging
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from pydantic import BaseModel

from application.services.github.auth.installation_token_manager import InstallationTokenManager
from common.config.config import GITHUB_PUBLIC_REPO_INSTALLATION_ID

logger = logging.getLogger(__name__)

# Configuration constants
BUILDS_DIR = Path("/tmp/cyoda_builds")
GIT_CLONE_TIMEOUT_SECONDS = 300
GIT_CHECKOUT_TIMEOUT_SECONDS = 60
GIT_FETCH_TIMEOUT_SECONDS = 300
GITHUB_URL_PATTERN = r'/([^/]+?)(\.git)?$'


class CloneResult(BaseModel):
    """Result of repository clone operation."""

    success: bool
    message: str
    repository_path: Optional[str] = None


def is_textual_file(filename: str) -> bool:
    """Check if a file is a textual format based on extension."""
    filename_lower = filename.lower()

    textual_extensions = {
        ".pdf", ".docx", ".xlsx", ".pptx", ".xml", ".json", ".txt",
        ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".properties", ".env",
        ".md", ".markdown", ".rst", ".tex", ".latex", ".sql",
        ".dockerfile", ".gitignore", ".gitattributes",
        ".editorconfig", ".htaccess", ".robots",
        ".mk", ".cmake", ".gradle",
        ".js", ".ts", ".jsx", ".tsx",
        ".c", ".cpp", ".h", ".hpp", ".cs", ".rs", ".go",
        ".swift", ".dart",
        ".hs", ".ml", ".fs", ".clj", ".elm",
        ".r", ".jl", ".f90", ".f95",
        ".php", ".rb", ".scala", ".lua", ".nim", ".zig", ".v",
        ".d", ".cr", ".ex", ".exs", ".erl", ".hrl"
    }

    files_without_extension = {"dockerfile", "makefile"}

    for ext in textual_extensions:
        if filename_lower.endswith(ext):
            return True

    if filename_lower in files_without_extension:
        return True

    return False


def _extract_repo_name_from_url(repository_url: str) -> Optional[str]:
    """Extract repository name from GitHub URL.

    Args:
        repository_url: GitHub repository URL

    Returns:
        Repository name or None if extraction fails
    """
    match = re.search(GITHUB_URL_PATTERN, repository_url)
    return match.group(1) if match else None


def _setup_repository_path(repository_branch: str) -> Path:
    """Setup repository directory path.

    Args:
        repository_branch: Branch name used as directory name

    Returns:
        Path object to repository location
    """
    BUILDS_DIR.mkdir(parents=True, exist_ok=True)
    return BUILDS_DIR / repository_branch


def _is_repository_already_cloned(repo_path: Path) -> bool:
    """Check if repository already exists and is valid.

    Args:
        repo_path: Path to check for repository

    Returns:
        True if repository exists with .git directory
    """
    return repo_path.exists() and (repo_path / ".git").exists()


async def _get_clone_url(
    repository_url: str, installation_id: Optional[str] = None
) -> str:
    """Determine clone URL with authentication if available.

    Args:
        repository_url: Original repository URL
        installation_id: GitHub App installation ID (optional)

    Returns:
        Clone URL (authenticated or public)
    """
    effective_installation_id = installation_id
    if not effective_installation_id and GITHUB_PUBLIC_REPO_INSTALLATION_ID:
        effective_installation_id = GITHUB_PUBLIC_REPO_INSTALLATION_ID
        logger.info("Using GITHUB_PUBLIC_REPO_INSTALLATION_ID from environment")

    if effective_installation_id:
        try:
            token_manager = InstallationTokenManager()
            token = await token_manager.get_installation_token(int(effective_installation_id))
            authenticated_url = repository_url.replace(
                "https://github.com/",
                f"https://x-access-token:{token}@github.com/",
            )
            logger.info("🔐 Using authenticated URL for cloning")
            return authenticated_url
        except Exception as e:
            logger.warning(f"Failed to get installation token: {e}, using public URL")
            return repository_url
    else:
        logger.info("Using public URL for cloning (no installation_id provided)")
        return repository_url


def _run_git_clone(clone_url: str, repo_path: Path) -> Tuple[bool, Optional[str]]:
    """Execute git clone command.

    Args:
        clone_url: URL to clone from (authenticated or public)
        repo_path: Target directory path

    Returns:
        Tuple of (success, error_message)
    """
    logger.info(f"🔄 Cloning repository from {clone_url.split('@')[-1]}...")
    result = subprocess.run(
        ["git", "clone", clone_url, str(repo_path)],
        capture_output=True,
        text=True,
        timeout=GIT_CLONE_TIMEOUT_SECONDS,
    )

    if result.returncode != 0:
        error_msg = result.stderr or result.stdout
        logger.error(f"❌ Git clone failed: {error_msg}")
        return False, error_msg

    return True, None


def _run_git_checkout(repo_path: Path, branch_name: str) -> Tuple[bool, Optional[str]]:
    """Execute git checkout command for a branch.

    Args:
        repo_path: Repository directory path
        branch_name: Branch to checkout

    Returns:
        Tuple of (success, error_message)
    """
    logger.info(f"🔄 Checking out branch {branch_name}...")
    result = subprocess.run(
        ["git", "checkout", branch_name],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        timeout=GIT_CHECKOUT_TIMEOUT_SECONDS,
    )

    if result.returncode != 0:
        return False, result.stderr or result.stdout

    return True, None


def _run_git_fetch(repo_path: Path) -> bool:
    """Execute git fetch command.

    Args:
        repo_path: Repository directory path

    Returns:
        True if fetch succeeds
    """
    result = subprocess.run(
        ["git", "fetch", "origin"],
        cwd=str(repo_path),
        capture_output=True,
        timeout=GIT_FETCH_TIMEOUT_SECONDS,
    )
    return result.returncode == 0


async def _checkout_branch_with_retry(
    repo_path: Path, branch_name: str
) -> Tuple[bool, Optional[str]]:
    """Attempt to checkout branch, fetching from remote if needed.

    Args:
        repo_path: Repository directory path
        branch_name: Branch to checkout

    Returns:
        Tuple of (success, error_message)
    """
    success, error_msg = _run_git_checkout(repo_path, branch_name)
    if success:
        return True, None

    # Branch not found locally, try fetching from remote
    logger.warning(f"Branch {branch_name} not found locally, fetching from remote...")
    if not _run_git_fetch(repo_path):
        logger.warning("Git fetch failed, attempting checkout anyway")

    # Try checkout again after fetch
    success, error_msg = _run_git_checkout(repo_path, branch_name)
    if not success:
        logger.error(f"❌ Failed to checkout branch {branch_name}: {error_msg}")

    return success, error_msg


async def ensure_repository_cloned(
    repository_url: str,
    repository_branch: str,
    installation_id: Optional[str] = None,
    repository_name: Optional[str] = None,
    repository_owner: Optional[str] = None,
    use_env_installation_id: bool = True,
) -> Tuple[bool, str, Optional[str]]:
    """Ensure repository is cloned. If not, clone it using installation_id and repository_url.

    Args:
        repository_url: GitHub repository URL
        repository_branch: Branch name to checkout
        installation_id: GitHub App installation ID (optional)
        repository_name: Repository name (extracted from URL if not provided)
        repository_owner: Repository owner (extracted from URL if not provided)
        use_env_installation_id: If True, use GITHUB_PUBLIC_REPO_INSTALLATION_ID from env

    Returns:
        Tuple of (success: bool, message: str, repository_path: Optional[str])
    """
    try:
        # Step 1: Extract repository name if not provided
        if not repository_name:
            repository_name = _extract_repo_name_from_url(repository_url)
            if not repository_name:
                return False, "Could not extract repository name from URL", None

        # Step 2: Setup repository path
        repo_path_obj = _setup_repository_path(repository_branch)
        repository_path = str(repo_path_obj)

        # Step 3: Check if already cloned
        if _is_repository_already_cloned(repo_path_obj):
            logger.info(f"✅ Repository already cloned at {repository_path}")
            return True, f"Repository already exists at {repository_path}", repository_path

        logger.info(f"📦 Repository not found at {repository_path}, cloning from {repository_url}")

        # Step 4: Determine clone URL (with auth if available)
        effective_installation_id = installation_id
        if not effective_installation_id and use_env_installation_id:
            effective_installation_id = None  # Let _get_clone_url handle env var

        clone_url = await _get_clone_url(repository_url, effective_installation_id)

        # Step 5: Create repository directory and clone
        repo_path_obj.mkdir(parents=True, exist_ok=True)
        success, error_msg = _run_git_clone(clone_url, repo_path_obj)
        if not success:
            return False, f"Failed to clone repository: {error_msg}", None

        # Step 6: Checkout branch with retry logic
        success, error_msg = await _checkout_branch_with_retry(repo_path_obj, repository_branch)
        if not success:
            return False, f"Failed to checkout branch {repository_branch}: {error_msg}", None

        logger.info(f"✅ Repository cloned successfully at {repository_path}")
        return True, f"Repository cloned successfully at {repository_path}", repository_path

    except subprocess.TimeoutExpired:
        return False, "Repository clone operation timed out", None
    except Exception as e:
        logger.error(f"❌ Error ensuring repository is cloned: {e}", exc_info=True)
        return False, f"Error cloning repository: {str(e)}", None

