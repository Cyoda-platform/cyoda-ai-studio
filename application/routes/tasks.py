"""
Task Routes for AI Assistant Application

Manages background task tracking API endpoints.
Includes SSE streaming for real-time task progress updates.
"""

import json
import logging
from datetime import timedelta
from typing import Any, Dict

from quart import Blueprint, Response, jsonify, request
from quart_rate_limiter import rate_limit

from application.services.streaming_service import StreamingService
from common.utils.jwt_utils import (
    TokenExpiredError,
    TokenValidationError,
    get_user_info_from_header,
)
from services.services import get_entity_service, get_task_service

logger = logging.getLogger(__name__)

tasks_bp = Blueprint("tasks", __name__)


# Service proxy to avoid repeated lookups
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


async def _rate_limit_key() -> str:
    """Generate rate limit key (IP-based)."""
    return request.remote_addr or "unknown"


async def _get_user_info() -> tuple[str, bool]:
    """
    Extract user ID and superuser status from JWT token in Authorization header.

    Returns:
        Tuple of (user_id, is_superuser)

    Raises:
        TokenExpiredError: If token has expired
        TokenValidationError: If token is invalid
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header:
        # No auth header - return default guest session
        return "guest.anonymous", False

    try:
        user_id, is_superuser = get_user_info_from_header(auth_header)
        return user_id, is_superuser

    except TokenExpiredError:
        logger.warning("Token has expired")
        raise

    except TokenValidationError as e:
        logger.warning(f"Invalid token: {e}")
        raise


@tasks_bp.route("/<task_id>", methods=["GET"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def get_task(task_id: str) -> tuple[Response, int]:
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
        user_id, is_superuser = await _get_user_info()

        # Get task from service
        task_service = get_task_service()
        task = await task_service.get_task(task_id)

        if not task:
            return jsonify({"error": "Task not found"}), 404

        # Validate ownership (unless superuser)
        if not is_superuser and task.user_id != user_id:
            return jsonify({"error": "Access denied"}), 403

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

        return jsonify(response_body), 200

    except TokenExpiredError:
        return jsonify({"error": "Token expired"}), 401
    except TokenValidationError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        logger.exception(f"Error getting task: {e}")
        return jsonify({"error": str(e)}), 500


@tasks_bp.route("", methods=["GET"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def list_tasks() -> tuple[Response, int]:
    """
    List all background tasks for a conversation.

    Query params:
        - conversation_id: str (required) - Conversation ID to get tasks for
    """
    try:
        user_id, is_superuser = await _get_user_info()

        # Get conversation_id from query params
        conversation_id = request.args.get("conversation_id")

        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400

        # Get conversation to access task IDs
        from application.entity.conversation import Conversation

        response = await service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not response:
            return jsonify({"error": "Conversation not found"}), 404

        conversation_data = response.data if hasattr(response, "data") else response
        conversation = Conversation(**conversation_data)

        # Validate ownership (unless superuser)
        if not is_superuser and conversation.user_id != user_id:
            return jsonify({"error": "Access denied"}), 403

        # Get all tasks by their IDs from background_task_ids field
        task_ids = conversation.background_task_ids or []
        logger.info(f"Found {len(task_ids)} task IDs for conversation {conversation_id}: {task_ids}")

        tasks_data = []
        task_service = get_task_service()

        for task_id in task_ids:
            try:
                task = await task_service.get_task(task_id)
                if task:
                    tasks_data.append(task.to_api_response())
                else:
                    logger.warning(f"Task {task_id} not found")
            except Exception as e:
                logger.warning(f"Failed to get task {task_id}: {e}")
                # Continue with other tasks

        return jsonify({"tasks": tasks_data, "count": len(tasks_data)}), 200

    except TokenExpiredError:
        return jsonify({"error": "Token expired"}), 401
    except TokenValidationError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        logger.exception(f"Error listing tasks: {e}")
        return jsonify({"error": str(e)}), 500


@tasks_bp.route("/<task_id>/stream", methods=["GET"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
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
        user_id, is_superuser = await _get_user_info()

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

