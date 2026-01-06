"""Get repository diff endpoint."""

import logging
import subprocess
from typing import Dict, List

from quart import request
from quart.typing import ResponseReturnValue

from application.routes.common.response import APIResponse

logger = logging.getLogger(__name__)


def parse_git_status(output: str) -> Dict[str, List[str]]:
    """Parse git status output into categorized changes."""
    changes: Dict[str, List[str]] = {
        "modified": [],
        "added": [],
        "deleted": [],
        "untracked": [],
    }

    for line in output.strip().split("\n"):
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

    return changes


async def handle_get_repository_diff() -> ResponseReturnValue:
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
        data = await request.get_json()
        repository_path = data.get("repository_path")

        if not repository_path:
            return APIResponse.error(
                "Missing required field",
                400,
                details={"message": "repository_path is required"}
            )

        logger.info(f"Getting diff for repository: {repository_path}")

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

        changes = parse_git_status(result.stdout)

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

