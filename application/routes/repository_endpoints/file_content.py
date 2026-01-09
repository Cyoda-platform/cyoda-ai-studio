"""Get file content endpoint."""

import logging

from quart import request
from quart.typing import ResponseReturnValue

from application.routes.common.response import APIResponse
from application.services import get_github_service_for_public_repo
from common.config.config import CLIENT_GIT_BRANCH

logger = logging.getLogger(__name__)


async def handle_get_file_content() -> ResponseReturnValue:
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
                details={"message": "repository_name and file_path are required"},
            )

        logger.info(
            f"Getting file content: {owner}/{repository_name}/{file_path} (branch: {branch})"
        )

        github_service = get_github_service_for_public_repo()

        content = await github_service.contents.get_file_content(
            repository_name, file_path, ref=branch
        )

        if content is None:
            return APIResponse.error(
                "File not found",
                404,
                details={"message": f"File {file_path} not found in repository"},
            )

        return APIResponse.success({"content": content, "file_path": file_path})

    except Exception as e:
        logger.error(f"Error getting file content: {e}", exc_info=True)
        return APIResponse.error(
            "Failed to get file content", 500, details={"message": str(e)}
        )
