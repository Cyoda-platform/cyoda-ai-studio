"""Process monitoring and completion handling functions."""

import asyncio
import logging
from typing import Any, Dict, Optional

from services.services import get_task_service

logger = logging.getLogger(__name__)

# Constants for monitoring
PROCESS_CHECK_INTERVAL = 10     # seconds
PROGRESS_UPDATE_CAP = 95        # max progress before completion


async def _perform_initial_commit(
    git_service: Any,
    repository_path: str,
    branch_name: str,
    repo_auth_config: Dict[str, Any]
) -> float:
    """Perform initial commit and return current time.

    Args:
        git_service: Git service instance
        repository_path: Repository path
        branch_name: Branch name
        repo_auth_config: Repository auth config

    Returns:
        Current event loop time after commit
    """
    try:
        await asyncio.wait_for(
            git_service.commit_and_push(
                repository_path,
                f"Initial commit for {branch_name}",
                branch_name,
                repo_auth_config
            ),
            timeout=60.0
        )
        logger.info(f"✅ [{branch_name}] Initial commit completed")
    except asyncio.TimeoutError:
        logger.warning(f"⚠️ [{branch_name}] Initial commit timed out")
    except Exception as e:
        logger.warning(f"⚠️ [{branch_name}] Initial commit failed: {e}")

    return asyncio.get_event_loop().time()


async def _check_process_running(process: Any, pid: int) -> bool:
    """Check if process is still running.

    Args:
        process: Process instance
        pid: Process ID

    Returns:
        True if process is still running, False if completed
    """
    remaining_time = min(PROCESS_CHECK_INTERVAL, 10)
    try:
        await asyncio.wait_for(process.wait(), timeout=remaining_time)
        logger.info(f"✅ Process {pid} completed")
        return False
    except asyncio.TimeoutError:
        from application.agents.shared.process_utils import _is_process_running
        if not await _is_process_running(pid):
            logger.info(f"✅ Process {pid} exited silently")
            return False
        return True


async def _perform_periodic_commit(
    git_service: Any,
    repository_path: str,
    branch_name: str,
    repo_auth_config: Dict[str, Any],
    elapsed_time: int,
    task_id: str,
    task_service: Any,
    pid: int
) -> None:
    """Perform periodic commit and push changes.

    Args:
        git_service: Git service instance
        repository_path: Repository path
        branch_name: Branch name
        repo_auth_config: Repository auth config
        elapsed_time: Elapsed time in seconds
        task_id: Task ID
        task_service: Task service instance
        pid: Process ID
    """
    try:
        commit_result = await asyncio.wait_for(
            git_service.commit_and_push(
                repository_path,
                f"Progress on {branch_name} ({int(elapsed_time)}s)",
                branch_name,
                repo_auth_config
            ),
            timeout=120.0
        )

        if commit_result.get('success'):
            changed_files = commit_result.get('changed_files', [])
            canvas_resources = commit_result.get('canvas_resources', {})

            metadata = {
                "changed_files": changed_files[:20],
                "canvas_resources": canvas_resources,
                "elapsed_time": int(elapsed_time),
                "pid": pid
            }

            await task_service.add_progress_update(
                task_id=task_id,
                message=f"Progress committed ({len(changed_files)} files)",
                metadata=metadata
            )
            logger.info(f"📊 [{branch_name}] Progress committed: {len(changed_files)} files")
    except asyncio.TimeoutError:
        logger.warning(f"⚠️ [{branch_name}] Periodic commit timed out")
    except Exception as e:
        logger.warning(f"⚠️ [{branch_name}] Periodic commit failed: {e}")


async def _update_progress_status(
    task_id: str,
    elapsed_time: int,
    timeout_seconds: int,
    task_service: Any,
    pid: int
) -> None:
    """Update task progress status.

    Args:
        task_id: Task ID
        elapsed_time: Elapsed time in seconds
        timeout_seconds: Total timeout in seconds
        task_service: Task service instance
        pid: Process ID
    """
    progress = min(PROGRESS_UPDATE_CAP, int((elapsed_time / timeout_seconds) * 100))
    await task_service.update_task_status(
        task_id=task_id,
        status="running",
        message=f"Processing... ({int(elapsed_time)}s elapsed)",
        progress=progress,
        metadata={"elapsed_time": int(elapsed_time), "pid": pid}
    )
    logger.debug(f"🔍 Process {pid} still running: {progress}% ({int(elapsed_time)}s)")


async def _unregister_process(pid: int) -> None:
    """Unregister process from process manager.

    Args:
        pid: Process ID
    """
    try:
        from application.agents.shared.process_manager import get_process_manager
        await get_process_manager().unregister_process(pid)
        logger.info(f"✅ Unregistered process {pid}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to unregister process: {e}")


async def _perform_final_commit(
    git_service: Any,
    repository_path: str,
    branch_name: str,
    repo_auth_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Perform final commit and push.

    Args:
        git_service: Git service instance
        repository_path: Path to repository.
        branch_name: Branch name.
        repo_auth_config: Repository auth configuration.

    Returns:
        Final commit result with changed files and resources.
    """
    return await asyncio.wait_for(
        git_service.commit_and_push(
            repository_path,
            f"Final commit for {branch_name}",
            branch_name,
            repo_auth_config
        ),
        timeout=120.0
    )


def _build_completion_metadata(
    changed_files: list,
    canvas_resources: Dict,
    conversation_id: Optional[str],
    repository_name: Optional[str],
    repository_owner: Optional[str],
    branch_name: str
) -> Dict[str, Any]:
    """Build completion metadata with canvas info.

    Args:
        changed_files: List of changed files.
        canvas_resources: Canvas resources dictionary.
        conversation_id: Conversation ID.
        repository_name: Repository name.
        repository_owner: Repository owner.
        branch_name: Branch name.

    Returns:
        Formatted completion metadata.
    """
    metadata = {
        "changed_files": changed_files[:20],
        "canvas_resources": canvas_resources,
        "total_files": len(changed_files)
    }

    if conversation_id and repository_name and canvas_resources:
        metadata['hook_data'] = {
            "conversation_id": conversation_id,
            "repository_name": repository_name,
            "repository_owner": repository_owner,
            "branch_name": branch_name,
            "resources": canvas_resources
        }

    return metadata


async def _handle_success_completion(
    git_service: Any,
    task_id: str,
    repository_path: str,
    branch_name: str,
    repo_auth_config: Dict[str, Any],
    task_service: Any,
    conversation_id: Optional[str],
    repository_name: Optional[str],
    repository_owner: Optional[str]
) -> None:
    """Handle successful process completion with final commit and canvas update.

    Performs final commit, gathers completion metadata including canvas resources,
    and updates task status to completed.

    Args:
        git_service: Git service instance
        task_id: Task identifier.
        repository_path: Path to repository.
        branch_name: Git branch name.
        repo_auth_config: Repository authentication config.
        task_service: Task service instance.
        conversation_id: Conversation ID.
        repository_name: Repository name.
        repository_owner: Repository owner.
    """
    try:
        # Perform final commit
        final_result = await _perform_final_commit(
            git_service, repository_path, branch_name, repo_auth_config
        )

        # Extract results
        changed_files = final_result.get('changed_files', [])
        canvas_resources = final_result.get('canvas_resources', {})

        # Build metadata
        completion_metadata = _build_completion_metadata(
            changed_files, canvas_resources,
            conversation_id, repository_name, repository_owner, branch_name
        )

        # Update task
        files_summary = f"{len(changed_files)} files changed" if changed_files else "No files changed"
        await task_service.update_task_status(
            task_id=task_id,
            status="completed",
            message=f"Process completed - {files_summary}",
            progress=100,
            metadata=completion_metadata
        )
        logger.info(f"✅ Task {task_id} completed successfully")

    except asyncio.TimeoutError:
        logger.warning("⚠️ Final commit timed out, marking as completed anyway")
        await task_service.update_task_status(
            task_id=task_id,
            status="completed",
            message="Process completed (final commit timed out)",
            progress=100
        )
    except Exception as e:
        logger.error(f"❌ Final commit failed: {e}", exc_info=True)
        await task_service.update_task_status(
            task_id=task_id,
            status="completed",
            message="Process completed (final commit failed)",
            progress=100,
            metadata={"error": str(e)}
        )


async def _handle_failure_completion(
    task_id: str,
    return_code: Optional[int],
    elapsed_time: float,
    timeout_seconds: int,
    task_service: Any
) -> None:
    """Handle failed or timed-out process completion."""
    if elapsed_time >= timeout_seconds:
        error_msg = f"Timeout exceeded ({timeout_seconds}s)"
        logger.error(f"❌ Task {task_id} timed out")
    else:
        error_msg = f"Process failed with exit code {return_code}"
        logger.error(f"❌ Task {task_id} failed: {error_msg}")

    await task_service.update_task_status(
        task_id=task_id,
        status="failed",
        message=error_msg,
        progress=0,
        error=error_msg
    )


async def _determine_and_handle_process_result(
    process: Any,
    task_id: str,
    pid: int,
    elapsed_time: float,
    timeout_seconds: int,
    git_service: Any,
    repository_path: str,
    branch_name: str,
    repo_auth_config: dict,
    task_service: Any,
    conversation_id: Optional[str] = None,
    repository_name: Optional[str] = None,
    repository_owner: Optional[str] = None
) -> None:
    """Safely determine process result and handle completion.

    Args:
        process: The completed subprocess
        task_id: Task identifier
        pid: Process ID for logging
        elapsed_time: Time elapsed during execution
        timeout_seconds: Maximum timeout
        git_service: Git service instance
        repository_path: Repository path
        branch_name: Branch name
        repo_auth_config: Repository auth config
        task_service: Task service instance
        conversation_id: Conversation ID (optional)
        repository_name: Repository name (optional)
        repository_owner: Repository owner (optional)
    """
    returncode = getattr(process, 'returncode', None)
    logger.info(f"🔍 Process {pid} final returncode: {returncode}")

    # Treat None returncode as success (process completed normally)
    is_success = returncode == 0 or returncode is None

    try:
        if is_success:
            logger.info(f"✅ Treating process {pid} as successful (returncode={returncode})")
            await _handle_success_completion(
                git_service, task_id, repository_path, branch_name,
                repo_auth_config, task_service, conversation_id,
                repository_name, repository_owner
            )
        else:
            logger.warning(f"❌ Process {pid} failed with returncode: {returncode}")
            await _handle_failure_completion(
                task_id, returncode, elapsed_time,
                timeout_seconds, task_service
            )
    except Exception as e:
        logger.error(f"❌ Error handling process completion: {e}", exc_info=True)
        # Fallback: mark task as failed if handler fails
        try:
            await _handle_failure_completion(
                task_id, None, elapsed_time,
                timeout_seconds, task_service
            )
        except Exception as e2:
            logger.error(f"❌ Failed to mark task as failed: {e2}", exc_info=True)
