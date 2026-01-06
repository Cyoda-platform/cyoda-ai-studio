"""
Task Routes for AI Assistant Application

Manages background task tracking API endpoints.
Includes SSE streaming for real-time task progress updates.

REFACTORED: Uses common infrastructure (auth, rate limiting, responses).
"""

import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from quart import Blueprint, Response, request
from quart_rate_limiter import rate_limit

from application.services.streaming_service import StreamingService
from common.utils.jwt_utils import TokenExpiredError, TokenValidationError

# NEW: Use common infrastructure
from application.routes.common.auth import get_authenticated_user
from application.routes.common.rate_limiting import default_rate_limit_key
from application.routes.common.response import APIResponse

from services.services import get_entity_service, get_task_service

logger = logging.getLogger(__name__)

tasks_bp = Blueprint("tasks", __name__)


# Service proxy to avoid repeated lookups
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


@tasks_bp.route("/<task_id>", methods=["GET"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def get_task(task_id: str):
    """
    Get background task status and progress.

    Returns task information including:
    - status (pending, running, completed, failed)
    - progress (0-100)
    - progress_messages (list of progress updates)
    - result (if completed)
    - error (if failed)
    """
    try:
        user_id, is_superuser = await get_authenticated_user()

        # Get task from service
        task_service = get_task_service()
        task = await task_service.get_task(task_id)

        if not task:
            return APIResponse.error("Task not found", 404)

        # Validate ownership (unless superuser)
        if not is_superuser and task.user_id != user_id:
            return APIResponse.error("Access denied", 403)

        # Return task data in API format
        task_data = task.to_api_response()

        # Build entities_data with workflow information (for UI compatibility)
        entities_data = {}
        if task.technical_id and task.workflow_name:
            entities_data[task.technical_id] = {
                "workflow_name": task.workflow_name,
                "entity_versions": [
                    {
                        "date": task.date,
                        "state": task.state or task.current_state,
                    }
                ],
                "next_transitions": [],
            }

        response_body = {
            **task_data,
            "entities_data": entities_data,
        }

        return APIResponse.success(response_body)

    except TokenExpiredError:
        return APIResponse.error("Token expired", 401)
    except TokenValidationError:
        return APIResponse.error("Invalid token", 401)
    except Exception as e:
        logger.exception(f"Error getting task: {e}")
        return APIResponse.error(str(e), 500)


async def _fetch_conversation_for_tasks(
    conversation_id: str,
    service_proxy: Any,
) -> Optional[Any]:
    """Fetch conversation entity for task listing.

    Args:
        conversation_id: Conversation ID
        service_proxy: Entity service proxy

    Returns:
        Conversation object or None
    """
    from application.entity.conversation import Conversation

    response = await service_proxy.get_by_id(
        entity_id=conversation_id,
        entity_class=Conversation.ENTITY_NAME,
        entity_version=str(Conversation.ENTITY_VERSION),
    )

    if not response:
        return None

    conversation_data = response.data if hasattr(response, "data") else response
    return Conversation(**conversation_data)


def _validate_conversation_ownership(
    conversation: Any,
    user_id: str,
    is_superuser: bool,
) -> Optional[str]:
    """Validate user owns the conversation.

    Args:
        conversation: Conversation object
        user_id: User ID
        is_superuser: Whether user is superuser

    Returns:
        Error message if access denied, None otherwise
    """
    if not is_superuser and conversation.user_id != user_id:
        return "Access denied"
    return None


async def _check_and_fix_stuck_task(task: Any, task_service: Any) -> None:
    """Check if a task is stuck (process exited but status still 'running') and fix it.

    Args:
        task: Task object
        task_service: Task service
    """
    logger.info(f"🔍 Checking task {task.technical_id} - status: {task.status}")

    if task.status != "running":
        logger.info(f"Task {task.technical_id} is not running, skipping check")
        return

    # Get PID from task field (not metadata!)
    pid = task.process_pid
    logger.info(f"🔍 Task {task.technical_id} has PID: {pid}")

    if not pid:
        logger.warning(f"Task {task.technical_id} has no PID stored")
        return

    # Check if process is still running
    from application.agents.shared.process_utils import _is_process_running

    try:
        is_running = await _is_process_running(pid)
        logger.info(f"🔍 PID {pid} is_running: {is_running}")

        if not is_running:
            logger.warning(
                f"⚠️  Task {task.technical_id} is stuck in 'running' but process {pid} has exited. "
                f"Marking as failed."
            )

            await task_service.update_task_status(
                task_id=task.technical_id,
                status="failed",
                message=f"Build process (PID {pid}) exited unexpectedly",
                progress=0,
                error="Process terminated without updating task status. "
                      "This likely indicates the build failed. Check build logs for details.",
            )
            logger.info(f"✅ Updated task {task.technical_id} to failed status")
    except Exception as e:
        logger.exception(f"❌ Failed to check process status for task {task.technical_id}: {e}")


async def _fetch_tasks_by_ids(
    task_ids: List[str],
    task_service: Any,
) -> List[Dict[str, Any]]:
    """Fetch multiple tasks by their IDs.

    Args:
        task_ids: List of task IDs
        task_service: Task service

    Returns:
        List of task data dictionaries
    """
    logger.info(f"🔍 _fetch_tasks_by_ids called with {len(task_ids)} task IDs: {task_ids}")
    tasks_data = []

    for task_id in task_ids:
        logger.info(f"🔍 Processing task {task_id}")
        try:
            task = await task_service.get_task(task_id)
            if task:
                logger.info(f"🔍 Task {task_id} retrieved, calling _check_and_fix_stuck_task")
                # Auto-fix stuck tasks
                await _check_and_fix_stuck_task(task, task_service)
                logger.info(f"🔍 _check_and_fix_stuck_task completed for {task_id}")

                # Get updated task after potential fix
                task = await task_service.get_task(task_id)
                if task:
                    tasks_data.append(task.to_api_response())
            else:
                logger.warning(f"Task {task_id} not found")
        except Exception as e:
            logger.warning(f"Failed to get task {task_id}: {e}")
            # Continue with other tasks

    return tasks_data


@tasks_bp.route("", methods=["GET"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def list_tasks():
    """List all background tasks for a conversation.

    Query params:
        - conversation_id: str (required) - Conversation ID to get tasks for
    """
    try:
        user_id, is_superuser = await get_authenticated_user()

        # Validate conversation_id parameter
        conversation_id = request.args.get("conversation_id")
        if not conversation_id:
            return APIResponse.error("conversation_id is required", 400)

        # Fetch conversation
        conversation = await _fetch_conversation_for_tasks(conversation_id, service)
        if not conversation:
            return APIResponse.error("Conversation not found", 404)

        # Validate ownership
        error_msg = _validate_conversation_ownership(conversation, user_id, is_superuser)
        if error_msg:
            return APIResponse.error(error_msg, 403)

        # Get task IDs from conversation
        task_ids = conversation.background_task_ids or []
        logger.info(
            f"Found {len(task_ids)} task IDs for conversation {conversation_id}: {task_ids}"
        )

        # Fetch all tasks
        task_service = get_task_service()
        tasks_data = await _fetch_tasks_by_ids(task_ids, task_service)

        return APIResponse.success({"tasks": tasks_data, "count": len(tasks_data)})

    except TokenExpiredError:
        return APIResponse.error("Token expired", 401)
    except TokenValidationError:
        return APIResponse.error("Invalid token", 401)
    except Exception as e:
        logger.exception(f"Error listing tasks: {e}")
        return APIResponse.error(str(e), 500)


@tasks_bp.route("/<task_id>", methods=["PATCH"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def update_task_status(task_id: str):
    """
    Manually update a task's status (admin endpoint).

    Useful for fixing stuck tasks where the process exited but didn't update status.

    Request body:
        - status: str (required) - New status (pending, running, completed, failed)
        - message: str (optional) - Status message
        - error: str (optional) - Error message (for failed status)
        - progress: int (optional) - Progress percentage
    """
    try:
        user_id, is_superuser = await get_authenticated_user()

        # Only superusers can manually update tasks
        if not is_superuser:
            return APIResponse.error("Admin access required", 403)

        # Get request data
        data = await request.get_json()
        if not data:
            return APIResponse.error("Request body required", 400)

        new_status = data.get("status")
        if not new_status:
            return APIResponse.error("status field is required", 400)

        if new_status not in ["pending", "running", "completed", "failed"]:
            return APIResponse.error(
                "Invalid status. Must be: pending, running, completed, failed", 400
            )

        # Get task
        task_service = get_task_service()
        task = await task_service.get_task(task_id)

        if not task:
            return APIResponse.error("Task not found", 404)

        # Update task
        await task_service.update_task_status(
            task_id=task_id,
            status=new_status,
            message=data.get("message") or f"Task manually updated to {new_status}",
            progress=data.get("progress", 0 if new_status == "failed" else 100 if new_status == "completed" else task.progress),
            error=data.get("error"),
        )

        # Get updated task
        updated_task = await task_service.get_task(task_id)

        return APIResponse.success({
            "message": f"Task {task_id} updated to {new_status}",
            "task": updated_task.to_api_response() if updated_task else None
        })

    except TokenExpiredError:
        return APIResponse.error("Token expired", 401)
    except TokenValidationError:
        return APIResponse.error("Invalid token", 401)
    except Exception as e:
        logger.exception(f"Error updating task: {e}")
        return APIResponse.error(str(e), 500)


@tasks_bp.route("/<task_id>/stream", methods=["GET"])
@rate_limit(100, timedelta(minutes=1), key_function=default_rate_limit_key)
async def stream_task_progress(task_id: str) -> Response:
    """
    Stream background task progress updates in real-time using SSE.

    Polls the BackgroundTask entity and streams progress events including:
    - Progress percentage (0-100)
    - Status changes (pending -> running -> completed/failed)
    - Progress messages
    - Statistics
    - Final result or error

    Query params:
        - poll_interval: int (optional) - Seconds between polls (default: 3)

    Returns:
        SSE stream with events: start, progress, done, error
    """
    try:
        user_id, is_superuser = await get_authenticated_user()

        # Get task to validate ownership
        task_service = get_task_service()
        task = await task_service.get_task(task_id)

        if not task:
            async def error_stream():
                yield f"event: error\ndata: {json.dumps({'error': 'Task not found'})}\n\n"

            return Response(error_stream(), mimetype="text/event-stream")

        # Validate ownership (unless superuser)
        if not is_superuser and task.user_id != user_id:
            async def error_stream():
                yield f"event: error\ndata: {json.dumps({'error': 'Access denied'})}\n\n"

            return Response(error_stream(), mimetype="text/event-stream")

        # Get poll interval from query params
        poll_interval = int(request.args.get("poll_interval", "3"))

        # Stream progress updates
        return Response(
            StreamingService.stream_progress_updates(
                task_id=task_id,
                task_service=task_service,
                poll_interval=poll_interval,
            ),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except TokenExpiredError:
        async def error_stream():
            yield f"event: error\ndata: {json.dumps({'error': 'Token expired'})}\n\n"

        return Response(error_stream(), mimetype="text/event-stream")
    except TokenValidationError:
        async def error_stream():
            yield f"event: error\ndata: {json.dumps({'error': 'Invalid token'})}\n\n"

        return Response(error_stream(), mimetype="text/event-stream")
    except Exception as e:
        logger.exception(f"Error setting up task stream: {e}")

        async def error_stream():
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return Response(error_stream(), mimetype="text/event-stream")

