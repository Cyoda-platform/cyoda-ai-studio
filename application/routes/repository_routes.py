"""
Repository routes for analyzing GitHub repositories.

Provides endpoints to analyze Cyoda application repositories and extract
entities, workflows, and functional requirements.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from quart import Blueprint, request, jsonify
from quart.typing import ResponseReturnValue
from pydantic import BaseModel, Field, ConfigDict

from application.services import (
    get_github_service_for_public_repo,
    get_github_service_for_private_repo,
)
from application.services.repository_parser import RepositoryParser
from services.services import get_entity_service

logger = logging.getLogger(__name__)

repository_bp = Blueprint("repository", __name__, url_prefix="/api/v1/repository")


class AnalyzeRepositoryRequest(BaseModel):
    """Request model for repository analysis."""

    repository_name: str = Field(
        ..., description="Repository name (e.g., 'mcp-cyoda-quart-app')"
    )
    branch: str = Field(default="main", description="Branch name to analyze")
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

    entity_name: str = Field(..., alias="entityName")
    file_path: str = Field(..., alias="filePath")


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
                return jsonify({"error": "Conversation not found"}), 404

            # Extract conversation data
            conversation_data = conversation_response.data
            if isinstance(conversation_data, dict):
                repository_path = conversation_data.get('workflow_cache', {}).get('adk_session_state', {}).get('repository_path')
                repository_name = conversation_data.get('repository_name')
                repository_branch = conversation_data.get('repository_branch')
                repository_owner = conversation_data.get('repository_owner')
            else:
                repository_path = getattr(conversation_data, 'workflow_cache', {}).get('adk_session_state', {}).get('repository_path')
                repository_name = getattr(conversation_data, 'repository_name', None)
                repository_branch = getattr(conversation_data, 'repository_branch', None)
                repository_owner = getattr(conversation_data, 'repository_owner', None)

            if not repository_path:
                return jsonify({"error": "Repository not cloned yet. Please clone the repository first."}), 400

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
                    for req_file in requirements_dir.glob("*.md"):
                        try:
                            with open(req_file, "r") as f:
                                content = f.read()
                            requirements.append({
                                "name": req_file.stem,
                                "path": str(req_file.relative_to(repo_path_obj)),
                                "content": content,
                            })
                        except Exception as e:
                            logger.warning(f"Failed to read requirement {req_file}: {e}")

                # Convert to response format
                return jsonify({
                    "repositoryName": repository_name,
                    "branch": repository_branch,
                    "appType": paths["type"],
                    "entities": entities,
                    "workflows": workflows,
                    "requirements": requirements
                }), 200

            except ValueError as e:
                return jsonify({"error": str(e)}), 400

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
                WorkflowResponse(entity_name=w.entity_name, file_path=w.file_path)
                for w in structure.workflows
            ],
            requirements=requirements_with_content,
        )

        logger.info(
            f"Successfully analyzed repository: {len(structure.entities)} entities, "
            f"{len(structure.workflows)} workflows, {len(structure.requirements)} requirements"
        )

        return jsonify(response.model_dump(by_alias=True)), 200

    except Exception as e:
        logger.error(f"Error analyzing repository: {e}", exc_info=True)
        return (
            jsonify({"error": "Failed to analyze repository", "message": str(e)}),
            500,
        )


@repository_bp.route("/file-content", methods=["POST"])
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
        branch = data.get("branch", "main")
        owner = data.get("owner", "Cyoda-platform")

        if not repository_name or not file_path:
            return (
                jsonify(
                    {
                        "error": "Missing required fields",
                        "message": "repository_name and file_path are required",
                    }
                ),
                400,
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
            return (
                jsonify(
                    {
                        "error": "File not found",
                        "message": f"File {file_path} not found in repository",
                    }
                ),
                404,
            )

        return jsonify({"content": content, "file_path": file_path}), 200

    except Exception as e:
        logger.error(f"Error getting file content: {e}", exc_info=True)
        return jsonify({"error": "Failed to get file content", "message": str(e)}), 500


@repository_bp.route("/diff", methods=["POST"])
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
            return (
                jsonify(
                    {
                        "error": "Missing required field",
                        "message": "repository_path is required",
                    }
                ),
                400,
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

        return jsonify(changes), 200

    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e}", exc_info=True)
        return jsonify({"error": "Git command failed", "message": str(e)}), 500
    except Exception as e:
        logger.error(f"Error getting repository diff: {e}", exc_info=True)
        return (
            jsonify({"error": "Failed to get repository diff", "message": str(e)}),
            500,
        )


@repository_bp.route("/pull", methods=["POST"])
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
            return jsonify({"error": "conversation_id is required"}), 400

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
            return jsonify({"error": "Conversation not found"}), 404

        # Extract repository path and branch
        conversation_data = conversation_response.data
        if isinstance(conversation_data, dict):
            repository_path = conversation_data.get('workflow_cache', {}).get('adk_session_state', {}).get('repository_path')
            repository_branch = conversation_data.get('repository_branch')
        else:
            repository_path = getattr(conversation_data, 'workflow_cache', {}).get('adk_session_state', {}).get('repository_path')
            repository_branch = getattr(conversation_data, 'repository_branch', None)

        if not repository_path:
            return jsonify({"error": "Repository not cloned yet. Please clone the repository first."}), 400

        if not repository_branch:
            return jsonify({"error": "No branch configured for this conversation"}), 400

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
            return jsonify({"error": result}), 500

        return jsonify({
            "success": True,
            "message": result,
            "branch": repository_branch
        }), 200

    except Exception as e:
        logger.error(f"Error pulling repository: {e}", exc_info=True)
        return jsonify({"error": "Failed to pull repository", "message": str(e)}), 500


@repository_bp.route("/health", methods=["GET"])
async def health_check() -> ResponseReturnValue:
    """Health check endpoint for repository service."""
    return jsonify({"status": "healthy", "service": "repository"}), 200
