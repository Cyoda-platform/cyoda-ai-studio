"""
Repository routes for analyzing GitHub repositories.

Provides endpoints to analyze Cyoda application repositories and extract
entities, workflows, and functional requirements.

REFACTORED: Uses APIResponse for consistent error handling.
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from quart import Blueprint, request
from quart.typing import ResponseReturnValue
from pydantic import BaseModel, Field, ConfigDict

# NEW: Use common infrastructure
from application.routes.common.response import APIResponse
from common.middleware.auth_middleware import require_auth

from application.services import (
    get_github_service_for_public_repo,
    get_github_service_for_private_repo,
)
from application.services.repository_parser import RepositoryParser
from application.services.github.auth.installation_token_manager import InstallationTokenManager
from common.config.config import CLIENT_GIT_BRANCH, GITHUB_PUBLIC_REPO_INSTALLATION_ID
from services.services import get_entity_service

logger = logging.getLogger(__name__)

repository_bp = Blueprint("repository", __name__, url_prefix="/api/v1/repository")


def _is_textual_file(filename: str) -> bool:
    """Check if a file is a textual format based on extension."""
    filename_lower = filename.lower()

    # Supported textual file extensions
    textual_extensions = {
        # Documents
        ".pdf", ".docx", ".xlsx", ".pptx", ".xml", ".json", ".txt",
        # Configuration
        ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".properties", ".env",
        # Documentation / Markup
        ".md", ".markdown", ".rst", ".tex", ".latex", ".sql",
        # System / Build
        ".dockerfile", ".gitignore", ".gitattributes",
        ".editorconfig", ".htaccess", ".robots",
        ".mk", ".cmake", ".gradle",
        # Programming Languages
        # Web
        ".js", ".ts", ".jsx", ".tsx",
        # Systems
        ".c", ".cpp", ".h", ".hpp", ".cs", ".rs", ".go",
        # Mobile
        ".swift", ".dart",
        # Functional
        ".hs", ".ml", ".fs", ".clj", ".elm",
        # Scientific
        ".r", ".jl", ".f90", ".f95",
        # Other
        ".php", ".rb", ".scala", ".lua", ".nim", ".zig", ".v",
        ".d", ".cr", ".ex", ".exs", ".erl", ".hrl"
    }

    # Files without extension (dockerfile, makefile, etc.)
    files_without_extension = {"dockerfile", "makefile"}

    # Check by extension
    for ext in textual_extensions:
        if filename_lower.endswith(ext):
            return True

    # Check files without extension
    if filename_lower in files_without_extension:
        return True

    return False


async def _ensure_repository_cloned(
    repository_url: str,
    repository_branch: str,
    installation_id: Optional[str] = None,
    repository_name: Optional[str] = None,
    repository_owner: Optional[str] = None,
    use_env_installation_id: bool = True,
) -> Tuple[bool, str, Optional[str]]:
    """
    Ensure repository is cloned. If not, clone it using installation_id and repository_url.

    Args:
        repository_url: GitHub repository URL (e.g., https://github.com/owner/repo)
        repository_branch: Branch name to checkout
        installation_id: GitHub App installation ID for authentication (optional)
        repository_name: Repository name (extracted from URL if not provided)
        repository_owner: Repository owner (extracted from URL if not provided)
        use_env_installation_id: If True and installation_id is None, use GITHUB_PUBLIC_REPO_INSTALLATION_ID from env

    Returns:
        Tuple of (success: bool, message: str, repository_path: Optional[str])
    """
    try:
        # Determine repository path
        if not repository_name:
            # Extract from URL
            import re
            match = re.search(r'/([^/]+?)(\.git)?$', repository_url)
            if match:
                repository_name = match.group(1)
            else:
                return False, "Could not extract repository name from URL", None

        # Use persistent location for cloned repositories
        builds_dir = Path("/tmp/cyoda_builds")
        builds_dir.mkdir(parents=True, exist_ok=True)
        repository_path = str(builds_dir / repository_branch)

        repo_path_obj = Path(repository_path)

        # Check if repository already exists and is valid
        if repo_path_obj.exists() and (repo_path_obj / ".git").exists():
            logger.info(f"✅ Repository already cloned at {repository_path}")
            return True, f"Repository already exists at {repository_path}", repository_path

        # Repository doesn't exist, need to clone it
        logger.info(f"📦 Repository not found at {repository_path}, cloning from {repository_url}")

        # Determine which installation_id to use
        effective_installation_id = installation_id
        if not effective_installation_id and use_env_installation_id and GITHUB_PUBLIC_REPO_INSTALLATION_ID:
            effective_installation_id = GITHUB_PUBLIC_REPO_INSTALLATION_ID
            logger.info(f"Using GITHUB_PUBLIC_REPO_INSTALLATION_ID from environment")

        # Get authenticated URL if installation_id is provided
        if effective_installation_id:
            try:
                token_manager = InstallationTokenManager()
                token = await token_manager.get_installation_token(int(effective_installation_id))
                # Create authenticated URL with token
                authenticated_url = repository_url.replace(
                    "https://github.com/",
                    f"https://x-access-token:{token}@github.com/"
                )
                clone_url = authenticated_url
                logger.info(f"🔐 Using authenticated URL for cloning")
            except Exception as e:
                logger.warning(f"Failed to get installation token: {e}, using public URL")
                clone_url = repository_url
        else:
            clone_url = repository_url
            logger.info(f"Using public URL for cloning (no installation_id provided)")

        # Create parent directory
        repo_path_obj.mkdir(parents=True, exist_ok=True)

        # Clone repository
        logger.info(f"🔄 Cloning repository from {repository_url}...")
        result = subprocess.run(
            ["git", "clone", clone_url, str(repo_path_obj)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            logger.error(f"❌ Git clone failed: {error_msg}")
            return False, f"Failed to clone repository: {error_msg}", None

        # Checkout the specified branch
        logger.info(f"🔄 Checking out branch {repository_branch}...")
        result = subprocess.run(
            ["git", "checkout", repository_branch],
            cwd=str(repo_path_obj),
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            # Try to fetch and checkout
            logger.warning(f"Branch {repository_branch} not found locally, fetching from remote...")
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=str(repo_path_obj),
                capture_output=True,
                timeout=300,
            )
            result = subprocess.run(
                ["git", "checkout", repository_branch],
                cwd=str(repo_path_obj),
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"❌ Failed to checkout branch {repository_branch}: {error_msg}")
                return False, f"Failed to checkout branch {repository_branch}: {error_msg}", None

        logger.info(f"✅ Repository cloned successfully at {repository_path}")
        return True, f"Repository cloned successfully at {repository_path}", repository_path

    except subprocess.TimeoutExpired:
        return False, "Repository clone operation timed out", None
    except Exception as e:
        logger.error(f"❌ Error ensuring repository is cloned: {e}", exc_info=True)
        return False, f"Error cloning repository: {str(e)}", None


class AnalyzeRepositoryRequest(BaseModel):
    """Request model for repository analysis."""

    repository_name: str = Field(
        ..., description="Repository name (e.g., 'mcp-cyoda-quart-app')"
    )
    branch: str = Field(default=CLIENT_GIT_BRANCH, description="Branch name to analyze")
    owner: str = Field(default="Cyoda-platform", description="Repository owner")
    installation_id: Optional[int] = Field(
        default=None,
        description="GitHub App installation ID (optional, uses env var if not provided)",
    )


class EntityResponse(BaseModel):
    """Response model for entity information."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    version: int
    file_path: str = Field(..., alias="filePath")
    class_name: str = Field(..., alias="className")
    fields: List[Dict[str, Any]]
    has_workflow: bool = Field(..., alias="hasWorkflow")


class WorkflowResponse(BaseModel):
    """Response model for workflow information."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    entity_name: str = Field(..., alias="entityName")
    file_path: str = Field(..., alias="filePath")
    content: Optional[Dict[str, Any]] = None


class RequirementResponse(BaseModel):
    """Response model for requirement information."""

    model_config = ConfigDict(populate_by_name=True)

    file_name: str = Field(..., alias="fileName")
    file_path: str = Field(..., alias="filePath")
    content: Optional[str] = None


class AnalyzeRepositoryResponse(BaseModel):
    """Response model for repository analysis."""

    model_config = ConfigDict(populate_by_name=True)

    repository_name: str = Field(..., alias="repositoryName")
    branch: str
    app_type: str = Field(..., alias="appType")
    entities: List[EntityResponse]
    workflows: List[WorkflowResponse]
    requirements: List[RequirementResponse]


@repository_bp.route("/analyze", methods=["POST"])
@require_auth
async def analyze_repository() -> ResponseReturnValue:
    """
    Analyze a GitHub repository to extract Cyoda application structure.

    Request Body:
        {
            "conversation_id": "b54b5f8e-78a8-11b2-92af-3a80f7a3e398"  # Required: Conversation with repository info
        }
        OR (legacy support):
        {
            "repository_name": "mcp-cyoda-quart-app",
            "branch": "main",
            "owner": "Cyoda-platform"
        }

    Returns:
        {
            "repository_name": "mcp-cyoda-quart-app",
            "branch": "main",
            "app_type": "python",
            "entities": [...],
            "workflows": [...],
            "requirements": [...]
        }
    """
    try:
        # Parse request
        data = await request.get_json()

        # Check if conversation_id is provided (new approach)
        conversation_id = data.get("conversation_id")

        if conversation_id:
            # Use local repository analysis (LLM-based via GitHub agent tools)
            from application.agents.github.tools import _detect_project_type, _scan_versioned_resources
            from application.entity.conversation.version_1.conversation import Conversation
            from pathlib import Path

            logger.info(f"Analyzing repository for conversation: {conversation_id}")

            # Get conversation entity
            entity_service = get_entity_service()
            conversation_response = await entity_service.get_by_id(
                entity_id=conversation_id,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            if not conversation_response or not conversation_response.data:
                return APIResponse.error("Conversation not found", 404)

            # Extract conversation data
            conversation_data = conversation_response.data
            if isinstance(conversation_data, dict):
                repository_path = conversation_data.get('workflow_cache', {}).get('adk_session_state', {}).get('repository_path')
                repository_name = conversation_data.get('repository_name')
                repository_branch = conversation_data.get('repository_branch')
                repository_owner = conversation_data.get('repository_owner')
                repository_url = conversation_data.get('repository_url')
                installation_id = conversation_data.get('installation_id')
            else:
                repository_path = getattr(conversation_data, 'workflow_cache', {}).get('adk_session_state', {}).get('repository_path')
                repository_name = getattr(conversation_data, 'repository_name', None)
                repository_branch = getattr(conversation_data, 'repository_branch', None)
                repository_owner = getattr(conversation_data, 'repository_owner', None)
                repository_url = getattr(conversation_data, 'repository_url', None)
                installation_id = getattr(conversation_data, 'installation_id', None)

            # Check if repository needs to be cloned (either not set or directory doesn't exist)
            repo_path_obj = Path(repository_path) if repository_path else None
            repo_exists = repo_path_obj and repo_path_obj.exists() and (repo_path_obj / ".git").exists()

            if not repo_exists:
                if repository_url and repository_branch:
                    logger.info(f"Repository not available at {repository_path}, attempting to clone from {repository_url}")
                    success, message, cloned_path = await _ensure_repository_cloned(
                        repository_url=repository_url,
                        repository_branch=repository_branch,
                        installation_id=installation_id,
                        repository_name=repository_name,
                        repository_owner=repository_owner,
                        use_env_installation_id=True,
                    )
                    if not success:
                        return APIResponse.error(f"Failed to clone repository: {message}", 400)
                    repository_path = cloned_path
                    logger.info(f"✅ Repository cloned successfully at {repository_path}")
                else:
                    return APIResponse.error(
                        "Repository not available and insufficient information to clone. "
                        "Please ensure the conversation has repository_url and repository_branch configured.",
                        400
                    )

            # Detect project type and scan resources
            try:
                paths = _detect_project_type(repository_path)
                repo_path_obj = Path(repository_path)

                # Scan entities
                entities_dir = repo_path_obj / paths["entities_path"]
                entities = _scan_versioned_resources(entities_dir, "entity", repo_path_obj)

                # Scan workflows
                workflows_dir = repo_path_obj / paths["workflows_path"]
                workflows = _scan_versioned_resources(workflows_dir, "workflow", repo_path_obj)

                # Scan requirements
                requirements = []
                requirements_dir = repo_path_obj / paths["requirements_path"]
                if requirements_dir.exists():
                    # Support all textual file formats for requirements
                    for req_file in sorted(requirements_dir.glob("*")):
                        if req_file.is_file() and _is_textual_file(req_file.name):
                            try:
                                with open(req_file, "r", encoding="utf-8") as f:
                                    content = f.read()
                                requirements.append({
                                    "name": req_file.stem,
                                    "path": str(req_file.relative_to(repo_path_obj)),
                                    "content": content,
                                })
                            except Exception as e:
                                logger.warning(f"Failed to read requirement {req_file}: {e}")

                # Convert workflows to response format with content
                workflows_with_content = [
                    {
                        "name": w.get("name", ""),
                        "entityName": w.get("entity_name", ""),
                        "filePath": w.get("path", ""),
                        "content": w.get("content", {})
                    }
                    for w in workflows
                ]

                # Convert to response format
                return APIResponse.success({
                    "repositoryName": repository_name,
                    "branch": repository_branch,
                    "appType": paths["type"],
                    "entities": entities,
                    "workflows": workflows_with_content,
                    "requirements": requirements
                })

            except ValueError as e:
                return APIResponse.error(str(e), 400)

        # Legacy support: use RepositoryParser for direct GitHub API analysis
        req = AnalyzeRepositoryRequest(**data)

        logger.info(
            f"Analyzing repository: {req.owner}/{req.repository_name} (branch: {req.branch})"
        )

        # Create GitHub service based on whether installation_id is provided
        if req.installation_id:
            # Use provided installation_id (for private repos or specific installations)
            repository_url = f"https://github.com/{req.owner}/{req.repository_name}"
            github_service = get_github_service_for_private_repo(
                installation_id=req.installation_id,
                repository_url=repository_url,
                owner=req.owner,
            )
            logger.info(f"Using provided installation_id: {req.installation_id}")
        else:
            # Use default public repo configuration from environment
            github_service = get_github_service_for_public_repo(owner=req.owner)
            logger.info("Using default public repo configuration")

        parser = RepositoryParser(github_service)

        # Parse repository
        structure = await parser.parse_repository(req.repository_name, req.branch)

        # Fetch content for each requirement
        requirements_with_content = []
        for r in structure.requirements:
            try:
                content = await github_service.contents.get_file_content(
                    req.repository_name, r.file_path, ref=req.branch
                )
                requirements_with_content.append(
                    RequirementResponse(
                        file_name=r.file_name, file_path=r.file_path, content=content
                    )
                )
            except Exception as e:
                logger.error(f"Error fetching content for {r.file_path}: {e}")
                # Add without content if fetch fails
                requirements_with_content.append(
                    RequirementResponse(file_name=r.file_name, file_path=r.file_path)
                )

        # Convert to response model
        response = AnalyzeRepositoryResponse(
            repository_name=structure.repository_name,
            branch=structure.branch,
            app_type=structure.app_type,
            entities=[
                EntityResponse(
                    name=e.name,
                    version=e.version,
                    file_path=e.file_path,
                    class_name=e.class_name,
                    fields=e.fields,
                    has_workflow=e.has_workflow,
                )
                for e in structure.entities
            ],
            workflows=[
                WorkflowResponse(
                    name=w.workflow_file or w.entity_name,
                    entity_name=w.entity_name,
                    file_path=w.file_path,
                    content=None  # Legacy mode doesn't load content from GitHub API
                )
                for w in structure.workflows
            ],
            requirements=requirements_with_content,
        )

        logger.info(
            f"Successfully analyzed repository: {len(structure.entities)} entities, "
            f"{len(structure.workflows)} workflows, {len(structure.requirements)} requirements"
        )

        return APIResponse.success(response.model_dump(by_alias=True))

    except Exception as e:
        logger.error(f"Error analyzing repository: {e}", exc_info=True)
        return APIResponse.error(
            "Failed to analyze repository",
            500,
            details={"message": str(e)}
        )


@repository_bp.route("/file-content", methods=["POST"])
@require_auth
async def get_file_content() -> ResponseReturnValue:
    """
    Get file content from GitHub repository.

    Request Body:
        {
            "repository_name": "mcp-cyoda-quart-app",
            "file_path": "application/entity/pet/version_1/pet.py",
            "branch": "main",
            "owner": "Cyoda-platform"
        }

    Returns:
        {
            "content": "file content as string",
            "file_path": "application/entity/pet/version_1/pet.py"
        }
    """
    try:
        data = await request.get_json()
        repository_name = data.get("repository_name")
        file_path = data.get("file_path")
        branch = data.get("branch", CLIENT_GIT_BRANCH)
        owner = data.get("owner", "Cyoda-platform")

        if not repository_name or not file_path:
            return APIResponse.error(
                "Missing required fields",
                400,
                details={"message": "repository_name and file_path are required"}
            )

        logger.info(
            f"Getting file content: {owner}/{repository_name}/{file_path} (branch: {branch})"
        )

        # Create GitHub service
        github_service = get_github_service_for_public_repo()

        # Get file content
        content = await github_service.contents.get_file_content(
            repository_name, file_path, ref=branch
        )

        if content is None:
            return APIResponse.error(
                "File not found",
                404,
                details={"message": f"File {file_path} not found in repository"}
            )

        return APIResponse.success({"content": content, "file_path": file_path})

    except Exception as e:
        logger.error(f"Error getting file content: {e}", exc_info=True)
        return APIResponse.error(
            "Failed to get file content",
            500,
            details={"message": str(e)}
        )


@repository_bp.route("/diff", methods=["POST"])
@require_auth
async def get_repository_diff() -> ResponseReturnValue:
    """
    Get diff of uncommitted changes in a repository.

    Request Body:
        {
            "repository_path": "/path/to/repository"
        }

    Returns:
        {
            "modified": ["file1.py", "file2.py"],
            "added": ["file3.py"],
            "deleted": ["file4.py"],
            "untracked": ["file5.py"]
        }
    """
    try:
        import subprocess

        data = await request.get_json()
        repository_path = data.get("repository_path")

        if not repository_path:
            return APIResponse.error(
                "Missing required field",
                400,
                details={"message": "repository_path is required"}
            )

        logger.info(f"Getting diff for repository: {repository_path}")

        # Use git to get status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

        changes: Dict[str, List[str]] = {
            "modified": [],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            status = line[:2]
            file_path = line[3:]

            if status.strip() == "M":
                changes["modified"].append(file_path)
            elif status.strip() == "A":
                changes["added"].append(file_path)
            elif status.strip() == "D":
                changes["deleted"].append(file_path)
            elif status.strip() == "??":
                changes["untracked"].append(file_path)

        total_changes = sum(len(v) for v in changes.values())
        logger.info(f"Repository has {total_changes} uncommitted changes")

        return APIResponse.success(changes)

    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e}", exc_info=True)
        return APIResponse.error("Git command failed", 500, details={"message": str(e)})
    except Exception as e:
        logger.error(f"Error getting repository diff: {e}", exc_info=True)
        return APIResponse.error(
            "Failed to get repository diff",
            500,
            details={"message": str(e)}
        )


@repository_bp.route("/pull", methods=["POST"])
@require_auth
async def pull_repository() -> ResponseReturnValue:
    """Pull latest changes from remote repository.

    Request body:
        {
            "conversation_id": "uuid-of-conversation"
        }

    Returns:
        Success message with pulled changes summary
    """
    try:
        data = await request.get_json()
        conversation_id = data.get("conversation_id")

        if not conversation_id:
            return APIResponse.error("conversation_id is required", 400)

        # Import here to avoid circular dependencies
        from application.agents.github.tools import pull_repository_changes
        from application.entity.conversation.version_1.conversation import Conversation
        from google.adk.tools import ToolContext

        logger.info(f"Pulling repository changes for conversation: {conversation_id}")

        # Get conversation entity to extract repository info
        entity_service = get_entity_service()
        conversation_response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not conversation_response or not conversation_response.data:
            return APIResponse.error("Conversation not found", 404)

        # Extract repository info from conversation
        conversation_data = conversation_response.data
        if isinstance(conversation_data, dict):
            repository_path = conversation_data.get('workflow_cache', {}).get('adk_session_state', {}).get('repository_path')
            repository_branch = conversation_data.get('repository_branch')
            repository_url = conversation_data.get('repository_url')
            installation_id = conversation_data.get('installation_id')
            repository_name = conversation_data.get('repository_name')
            repository_owner = conversation_data.get('repository_owner')
        else:
            repository_path = getattr(conversation_data, 'workflow_cache', {}).get('adk_session_state', {}).get('repository_path')
            repository_branch = getattr(conversation_data, 'repository_branch', None)
            repository_url = getattr(conversation_data, 'repository_url', None)
            installation_id = getattr(conversation_data, 'installation_id', None)
            repository_name = getattr(conversation_data, 'repository_name', None)
            repository_owner = getattr(conversation_data, 'repository_owner', None)

        if not repository_branch:
            return APIResponse.error("No branch configured for this conversation", 400)

        # Check if repository needs to be cloned (either not set or directory doesn't exist)
        repo_path_obj = Path(repository_path) if repository_path else None
        repo_exists = repo_path_obj and repo_path_obj.exists() and (repo_path_obj / ".git").exists()

        if not repo_exists:
            if repository_url:
                logger.info(f"Repository not available at {repository_path}, attempting to clone from {repository_url}")
                success, message, cloned_path = await _ensure_repository_cloned(
                    repository_url=repository_url,
                    repository_branch=repository_branch,
                    installation_id=installation_id,
                    repository_name=repository_name,
                    repository_owner=repository_owner,
                    use_env_installation_id=True,
                )
                if not success:
                    return APIResponse.error(f"Failed to clone repository: {message}", 400)
                repository_path = cloned_path
                logger.info(f"✅ Repository cloned successfully at {repository_path}")
            else:
                return APIResponse.error(
                    "Repository not available and repository_url not configured. "
                    "Please ensure the conversation has repository_url configured.",
                    400
                )

        # Create a minimal tool context with the required state
        class SimpleToolContext:
            """Minimal tool context for calling GitHub tools."""
            def __init__(self, state: dict):
                self.state = state

        tool_context = SimpleToolContext(state={
            "conversation_id": conversation_id,
            "repository_path": repository_path
        })

        # Call the pull tool
        result = await pull_repository_changes(tool_context)

        # Check if error
        if result.startswith("ERROR:"):
            return APIResponse.error(result, 500)

        return APIResponse.success({
            "success": True,
            "message": result,
            "branch": repository_branch
        })

    except Exception as e:
        logger.error(f"Error pulling repository: {e}", exc_info=True)
        return APIResponse.error(
            "Failed to pull repository",
            500,
            details={"message": str(e)}
        )


@repository_bp.route("/health", methods=["GET"])
async def health_check():
    """Health check endpoint for repository service."""
    return APIResponse.success({"status": "healthy", "service": "repository"})
