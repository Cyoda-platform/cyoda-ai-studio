"""
Chat Routes for AI Assistant Application

Manages all chat-related API endpoints including CRUD operations,
question/answer flow, and canvas questions.

PHASE 3: Integrated with Google ADK for real AI responses.
PHASE 4: Added SSE streaming for real-time agent updates.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from quart import Blueprint, Response, jsonify, request
from quart_rate_limiter import rate_limit

from application.entity.conversation import Conversation
from application.services import GoogleADKService
from application.services.streaming_service import StreamingService
from application.services.edge_message_persistence_service import (
    EdgeMessagePersistenceService,
)
from application.services.sdk_factory import is_using_openai_sdk
from common.exception import is_not_found
from common.service.entity_service import SearchConditionRequest
from common.utils.jwt_utils import (
    TokenExpiredError,
    TokenValidationError,
    get_user_info_from_header,
    get_user_info_from_token,
)
from services.services import (
    get_cyoda_assistant,
    get_entity_service,
    get_task_service,
    get_repository,
)

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)


# Service proxy to avoid repeated lookups
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()

# Initialize Google ADK service for AI responses (for canvas questions)
google_adk_service = GoogleADKService()

# Simple in-memory cache for chat lists (30 second TTL)
_chat_list_cache: Dict[str, tuple[List[Dict[str, Any]], float]] = {}
_CACHE_TTL_SECONDS = 30


def _get_cyoda_assistant() -> Any:
    """Get the Cyoda Assistant instance."""
    return get_cyoda_assistant()


def _get_edge_message_persistence_service() -> EdgeMessagePersistenceService:
    """Get the edge message persistence service."""
    repository = get_repository()
    return EdgeMessagePersistenceService(repository)


async def _get_user_info() -> tuple[str, bool]:
    """
    Extract user ID and superuser status from JWT token in Authorization header.

    Validates JWT tokens and extracts:
    - user_id from 'caas_org_id' claim
    - is_superuser from 'caas_cyoda_employee' claim

    Guest tokens (user_id starts with 'guest.') are signature-verified.
    Other tokens are decoded without verification (assumes external auth).

    Returns:
        tuple: (user_id, is_superuser)

    Raises:
        401 error if token is missing, invalid, or expired
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
        raise Exception("Token has expired") from None

    except TokenValidationError as e:
        logger.warning(f"Invalid token: {e}")
        raise Exception(f"Invalid token: {e}") from None


async def _create_conversation(
    user_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    file_blob_ids: Optional[List[str]] = None,
) -> Conversation:
    """Create a new conversation entity in Cyoda."""
    conversation = Conversation(
        user_id=user_id,
        name=name or "New Chat",
        description=description or "",
        file_blob_ids=file_blob_ids or [],  # type: ignore[call-arg]
    )

    # Save to Cyoda
    # Use by_alias=False to ensure snake_case field names (user_id, not userId)
    entity_data = conversation.model_dump(by_alias=False)
    response = await service.save(
        entity=entity_data,
        entity_class=Conversation.ENTITY_NAME,
        entity_version=str(Conversation.ENTITY_VERSION),
    )

    # Return the created conversation
    saved_data = response.data if hasattr(response, "data") else response
    return Conversation(**saved_data)


async def _get_conversation(technical_id: str) -> Optional[Conversation]:
    """Get a conversation by technical ID."""
    try:
        response = await service.get_by_id(
            entity_id=technical_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if response and hasattr(response, "data"):
            return Conversation(**response.data)
        elif response:
            return Conversation(**response)
        return None
    except Exception as e:
        if is_not_found(e):
            return None
        raise


async def _update_conversation(conversation: Conversation) -> Conversation:
    """
    Update a conversation entity in Cyoda.
    Includes retry logic for version conflict errors (422 and 500).

    Note: The conversation object should have all desired changes already applied.
    On retry, we fetch the fresh version and re-apply the changes from the input conversation.
    """
    import copy

    max_retries = 5
    base_delay = 0.1  # 100ms base delay

    # Store the data we want to save (from the input conversation)
    # We'll use the chat_flow which contains all messages
    # IMPORTANT: Use deepcopy to copy nested lists (current_flow, finished_flow)
    target_chat_flow = (
        copy.deepcopy(conversation.chat_flow) if conversation.chat_flow else {}
    )
    target_adk_session_id = conversation.adk_session_id
    target_name = conversation.name
    target_description = conversation.description
    target_background_task_ids = conversation.background_task_ids or []

    for attempt in range(max_retries):
        try:
            # On retry, fetch fresh version to get latest version number
            if attempt > 0 and conversation.technical_id:
                fresh_conversation = await _get_conversation(conversation.technical_id)
                if fresh_conversation:
                    # MERGE messages instead of replacing entire chat_flow
                    # This prevents message loss when multiple processes update concurrently
                    fresh_messages = fresh_conversation.chat_flow.get(
                        "finished_flow", []
                    )
                    target_messages = target_chat_flow.get("finished_flow", [])

                    # Build set of existing message IDs to avoid duplicates
                    existing_ids = {
                        msg.get("technical_id")
                        for msg in fresh_messages
                        if msg.get("technical_id")
                    }

                    # Add only new messages that don't already exist
                    for msg in target_messages:
                        msg_id = msg.get("technical_id")
                        if msg_id and msg_id not in existing_ids:
                            fresh_messages.append(msg)
                            existing_ids.add(msg_id)  # Track added messages

                    # Update chat_flow with merged messages
                    fresh_conversation.chat_flow["finished_flow"] = fresh_messages
                    fresh_conversation.chat_flow["current_flow"] = target_chat_flow.get(
                        "current_flow", []
                    )

                    # Apply other target data
                    fresh_conversation.adk_session_id = target_adk_session_id
                    fresh_conversation.name = target_name
                    fresh_conversation.description = target_description

                    # IMPORTANT: Merge background_task_ids instead of overwriting
                    # This preserves task IDs added by tools during agent execution
                    fresh_task_ids = set(fresh_conversation.background_task_ids or [])
                    target_task_ids = set(target_background_task_ids)
                    fresh_conversation.background_task_ids = list(
                        fresh_task_ids | target_task_ids
                    )

                    conversation = fresh_conversation

            # Use by_alias=False to ensure snake_case field names (user_id, not userId)
            entity_data = conversation.model_dump(by_alias=False)

            response = await service.update(
                entity_id=conversation.technical_id,
                entity=entity_data,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            saved_data = response.data if hasattr(response, "data") else response
            return Conversation(**saved_data)

        except Exception as e:
            error_str = str(e).lower()
            # Check for version conflict errors (can be 422 or 500)
            is_version_conflict = (
                "422" in error_str
                or "500" in error_str
                or "version mismatch" in error_str
                or "earliestupdateaccept" in error_str
                or "was changed by another transaction" in error_str
            )

            if is_version_conflict and attempt < max_retries - 1:
                # Exponential backoff: 100ms, 200ms, 400ms, 800ms, 1600ms
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Version conflict updating conversation {conversation.technical_id} "
                    f"(attempt {attempt + 1}/{max_retries}). Retrying in {delay:.3f}s... "
                    f"Error: {str(e)[:100]}"
                )
                await asyncio.sleep(delay)
                continue  # Retry
            else:
                # Non-retryable error or max retries reached
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to update conversation after {max_retries} attempts: {e}"
                    )
                raise  # Re-raise the exception

    # This should never be reached due to the raise in the except block
    # but mypy needs a return statement
    raise RuntimeError("Update conversation failed after all retries")


async def _validate_chat_ownership(
    conversation: Conversation, user_id: str, is_superuser: bool = False
) -> None:
    """
    Validate that the user owns the chat or is a superuser.

    Args:
        conversation: The conversation to validate
        user_id: The requesting user's ID
        is_superuser: Whether the user has superuser privileges

    Raises:
        403 error if user doesn't own the chat and isn't a superuser
    """
    if is_superuser:
        # Superusers can access any chat
        return

    if conversation.user_id != user_id:
        raise PermissionError(
            f"User {user_id} does not have access to chat {conversation.technical_id}"
        )


# Rate limit key function (simple IP-based for now)
async def _rate_limit_key() -> str:
    return request.remote_addr or "unknown"


@chat_bp.route("", methods=["GET"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def list_chats() -> tuple[Response, int]:
    """
    List all chats for the current user.

    Query params:
        - super: bool (optional) - Request super user access
        - target_user_id: str (optional) - Target user ID for super users
        - limit: int (optional) - Maximum number of chats to return (default: 100, max: 1000)
        - before: str (optional) - ISO 8601 timestamp for cursor-based pagination (get chats before this time)
    """
    import time
    request_start = time.time()

    try:
        user_id, is_superuser = await _get_user_info()

        logger.info(f"📋 Chat list request from user: {user_id}")

        # Check if superuser access is requested
        is_super_request = request.args.get("super", "false").lower() == "true"
        target_user_id = request.args.get("target_user_id")

        # Parse pagination parameters
        try:
            limit = min(int(request.args.get("limit", "100")), 1000)  # Max 1000
        except (ValueError, TypeError):
            limit = 100

        # Parse cursor (clientPointTime) for pagination
        before_time = request.args.get("before")  # ISO 8601 timestamp
        point_in_time = None
        if before_time:
            try:
                from dateutil import parser as date_parser
                point_in_time = date_parser.isoparse(before_time)
                logger.info(f"📅 Using cursor-based pagination: before={before_time}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid 'before' timestamp: {before_time}, error: {e}")
                before_time = None

        # Determine effective superuser status
        effective_super = is_super_request and is_superuser

        # Determine which user's chats to retrieve
        if effective_super and target_user_id:
            # Superuser requesting specific user's chats
            query_user_id = target_user_id
        elif effective_super and not target_user_id:
            # Superuser requesting all chats - don't filter by user_id
            query_user_id = None
        else:
            # Regular user requesting their own chats
            query_user_id = user_id

        # Check cache first (only for first page requests with default limit)
        cache_key = f"chats:{query_user_id or 'all'}"
        current_time = datetime.now(timezone.utc).timestamp()

        if not before_time and limit == 100:  # Only cache first page with default limit
            if cache_key in _chat_list_cache:
                cached_chats, cache_time = _chat_list_cache[cache_key]
                if current_time - cache_time < _CACHE_TTL_SECONDS:
                    cache_age = current_time - cache_time
                    logger.info(f"💾 CACHE HIT for {cache_key} (age: {cache_age:.1f}s, {len(cached_chats)} chats)")

                    # Calculate next cursor (oldest chat's date in this page)
                    next_cursor = cached_chats[-1]["date"] if len(cached_chats) == limit else None

                    return jsonify({
                        "chats": cached_chats[:limit],
                        "limit": limit,
                        "next_cursor": next_cursor,
                        "has_more": len(cached_chats) == limit,
                        "cached": True
                    }), 200
                else:
                    logger.info(f"🗑️ Cache expired for {cache_key} (age: {current_time - cache_time:.1f}s > {_CACHE_TTL_SECONDS}s)")

        # Build search condition and execute search
        search_start = time.time()

        if query_user_id:
            # Search for specific user's chats using snake_case field name
            # Use cursor-based pagination with clientPointTime
            logger.info(f"🔎 Searching chats for user_id={query_user_id}, limit={limit}, before={before_time or 'none'}")
            search_condition = (
                SearchConditionRequest.builder()
                .equals("user_id", query_user_id)
                .limit(limit + 1)  # Fetch one extra to determine if there are more results
                .build()
            )

            # Only pass point_in_time if we have a cursor (for pagination)
            # Don't pass it on first request to get latest chats
            if point_in_time:
                response_list = await service.search_at_time(
                    entity_class=Conversation.ENTITY_NAME,
                    condition=search_condition,
                    point_in_time=point_in_time,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )
            else:
                response_list = await service.search(
                    entity_class=Conversation.ENTITY_NAME,
                    condition=search_condition,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )
        else:
            # Superuser viewing all chats - use find_all instead of search
            logger.info(f"🔎 Fetching ALL chats (superuser mode), limit={limit}")
            response_list = await service.find_all(
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

        search_elapsed = time.time() - search_start
        logger.info(f"⏱️ Search completed in {search_elapsed:.3f}s, returned {len(response_list) if isinstance(response_list, list) else 0} results")

        # Extract conversations from response
        # EntityService returns list of EntityResponse objects
        # Each EntityResponse has: .data (Cyoda repository response) and .metadata (with .id as technical_id)
        # The Cyoda repository response has structure: {'type': ..., 'data': {...entity fields...}, 'meta': ..., 'technical_id': ...}
        user_chats = []
        if isinstance(response_list, list):
            for resp in response_list:
                # EntityResponse object - proper structure
                if hasattr(resp, "data") and hasattr(resp, "metadata"):
                    cyoda_response = resp.data
                    tech_id = resp.metadata.id

                    # Extract entity data from Cyoda repository response
                    # The actual entity fields are nested inside the 'data' key
                    if isinstance(cyoda_response, dict) and 'data' in cyoda_response:
                        entity_data = cyoda_response['data']
                        name = entity_data.get("name", "")
                        description = entity_data.get("description", "")
                        date = entity_data.get("date", "") or entity_data.get("created_at", "")
                    else:
                        # Fallback: try to extract directly (shouldn't happen with Cyoda repository)
                        name = ""
                        description = ""
                        date = ""

                    user_chats.append(
                        {
                            "technical_id": tech_id,
                            "name": name,
                            "description": description,
                            "date": date,
                        }
                    )
                # Legacy dict format (for backward compatibility)
                elif isinstance(resp, dict):
                    conv_data = resp.get("data", resp)
                    tech_id = resp.get("technical_id", "") or conv_data.get("technical_id", "")

                    name = conv_data.get("name", "")
                    description = conv_data.get("description", "")
                    date = conv_data.get("date", "") or conv_data.get("created_at", "")

                    user_chats.append(
                        {
                            "technical_id": tech_id,
                            "name": name,
                            "description": description,
                            "date": date,
                        }
                    )

        # Sort by date descending (most recent first)
        # Note: Cyoda doesn't support ORDER BY, so we sort client-side
        sort_start = time.time()
        user_chats.sort(key=lambda x: x.get("date", ""), reverse=True)
        sort_elapsed = time.time() - sort_start
        logger.debug(f"⏱️ Sorted {len(user_chats)} chats in {sort_elapsed:.3f}s")

        # Determine if there are more results (we fetched limit+1)
        has_more = len(user_chats) > limit
        if has_more:
            user_chats = user_chats[:limit]  # Remove the extra item

        # Calculate next cursor (oldest chat's date in this page)
        next_cursor = user_chats[-1]["date"] if has_more and len(user_chats) > 0 else None

        # For superuser mode (all chats), apply limit client-side
        if query_user_id is None:
            # Superuser mode - simple limit without cursor pagination
            user_chats = user_chats[:limit]
            next_cursor = None
            has_more = False

        # Update cache for first page requests (no cursor, default limit)
        # Only cache for regular users (not superuser mode)
        if not before_time and limit == 100 and query_user_id is not None:
            _chat_list_cache[cache_key] = (user_chats, current_time)
            logger.info(f"💾 Cache updated for {cache_key} with {len(user_chats)} chats")

        total_elapsed = time.time() - request_start
        logger.info(f"✅ Chat list request completed in {total_elapsed:.3f}s (returned {len(user_chats)} chats, has_more={has_more})")

        return jsonify({
            "chats": user_chats,
            "limit": limit,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "cached": False
        }), 200
    except Exception as e:
        logger.exception(f"Error listing chats: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def create_chat() -> tuple[Response, int]:
    """
    Create a new chat conversation.

    Single Responsibility: Only creates the chat entity.
    To send messages, use POST /chats/<id>/stream after creation.

    Accepts:
    - name: Chat name (required)
    - description: Chat description (optional)
    """
    try:
        user_id, _ = await _get_user_info()

        # Get chat metadata from request
        if request.is_json:
            data = await request.get_json()
            name = data.get("name")
            description = data.get("description")
        else:
            form = await request.form
            name = form.get("name")
            description = form.get("description")

        # Validate required fields
        if not name:
            return jsonify({"error": "Chat name is required"}), 400

        # Create conversation in Cyoda (no message processing)
        conversation = await _create_conversation(
            user_id, name, description, file_blob_ids=None
        )

        # Invalidate cache for this user
        cache_key = f"chats:{user_id}"
        if cache_key in _chat_list_cache:
            del _chat_list_cache[cache_key]
            logger.debug(f"Cache invalidated for {cache_key}")

        logger.info(f"Created chat {conversation.technical_id} for user {user_id}")

        return jsonify(conversation.to_api_response()), 201
    except Exception as e:
        logger.exception(f"Error creating chat: {e}")
        return jsonify({"error": str(e)}), 400


@chat_bp.route("/<technical_id>", methods=["GET"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def get_chat(technical_id: str) -> tuple[Response, int]:
    """
    Get specific chat by ID.

    Query params:
        - super: bool (optional) - Request super user access
    """
    try:
        user_id, is_superuser = await _get_user_info()

        # Check if superuser access is requested
        is_super_request = request.args.get("super", "false").lower() == "true"
        effective_super = is_super_request and is_superuser

        conversation = await _get_conversation(technical_id)
        if not conversation:
            return jsonify({"error": "Chat not found"}), 404

        # Validate ownership unless superuser
        try:
            await _validate_chat_ownership(conversation, user_id, effective_super)
        except PermissionError as e:
            return jsonify({"error": "Access denied"}), 403

        # Populate messages from edge messages
        edge_message_repository = get_repository()
        await conversation.populate_messages_from_edge_messages(edge_message_repository)

        # Format dialogue for UI
        dialogue = conversation.get_dialogue()

        # Build entities_data with workflow information
        entities_data = {}
        if conversation.technical_id and conversation.workflow_name:
            entities_data[conversation.technical_id] = {
                "workflow_name": conversation.workflow_name,
                "entity_versions": [
                    {
                        "date": conversation.date,
                        "state": conversation.state or conversation.current_state,
                    }
                ],
                "next_transitions": [],  # TODO: Get from workflow if needed
            }

        chat_body = {
            "technical_id": conversation.technical_id,
            "name": conversation.name,
            "description": conversation.description,
            "date": conversation.date,
            "dialogue": dialogue,
            "entities_data": entities_data,
            "repository_name": conversation.repository_name,
            "repository_owner": conversation.repository_owner,
            "repository_branch": conversation.repository_branch,
            "repository_url": conversation.repository_url,
            "installation_id": conversation.installation_id,
        }

        return jsonify({"chat_body": chat_body}), 200
    except Exception as e:
        logger.exception(f"Error getting chat: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/<technical_id>", methods=["PUT"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def update_chat(technical_id: str) -> tuple[Response, int]:
    """Update chat name/description."""
    try:
        user_id, is_superuser = await _get_user_info()

        conversation = await _get_conversation(technical_id)
        if not conversation:
            return jsonify({"error": "Chat not found"}), 404

        # Validate ownership
        try:
            await _validate_chat_ownership(conversation, user_id, is_superuser)
        except PermissionError:
            return jsonify({"error": "Access denied"}), 403

        data = await request.get_json()

        if "chat_name" in data:
            conversation.name = data["chat_name"]
        if "chat_description" in data:
            conversation.description = data["chat_description"]

        # Save updated conversation
        await _update_conversation(conversation)

        # Invalidate cache for this user
        cache_key = f"chats:{user_id}"
        if cache_key in _chat_list_cache:
            del _chat_list_cache[cache_key]
            logger.debug(f"Cache invalidated for {cache_key}")

        return jsonify({"message": "Chat updated successfully"}), 200
    except Exception as e:
        logger.exception(f"Error updating chat: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/<technical_id>", methods=["DELETE"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def delete_chat(technical_id: str) -> tuple[Response, int]:
    """Delete a chat."""
    try:
        user_id, is_superuser = await _get_user_info()

        conversation = await _get_conversation(technical_id)
        if not conversation:
            return jsonify({"error": "Chat not found"}), 404

        # Validate ownership
        try:
            await _validate_chat_ownership(conversation, user_id, is_superuser)
        except PermissionError:
            return jsonify({"error": "Access denied"}), 403

        # Delete from Cyoda
        await service.delete_by_id(
            entity_id=technical_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        # Invalidate cache for this user
        cache_key = f"chats:{user_id}"
        if cache_key in _chat_list_cache:
            del _chat_list_cache[cache_key]
            logger.debug(f"Cache invalidated for {cache_key}")

        return jsonify({"message": "Chat deleted successfully"}), 200
    except Exception as e:
        logger.exception(f"Error deleting chat: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/test-sse", methods=["GET"])
async def test_sse() -> Response:
    """
    Test SSE endpoint - sends events every 30 seconds for 3 minutes with heartbeats.
    No auth required. Use this to test if SSE works without backend logic.

    Test with: curl http://localhost:8000/api/v1/chats/test-sse
    """
    import asyncio
    import time

    async def event_generator():
        start_time = time.time()
        counter = 0
        last_event_time = start_time
        heartbeat_interval = 15  # Send heartbeat every 15 seconds
        event_interval = 30  # Send actual event every 30 seconds

        logger.info(f"🚀 Starting test SSE stream")

        try:
            # Send events for 3 minutes (180 seconds)
            iteration = 0
            while time.time() - start_time < 180:
                iteration += 1
                current_time = time.time()
                elapsed = int(current_time - start_time)

                if iteration % 10 == 0:  # Log every 10 iterations (10 seconds)
                    logger.info(f"🔄 Loop iteration {iteration}, elapsed={elapsed}s, remaining={180 - elapsed}s")

                # Send heartbeat if no event sent in last 15 seconds
                if current_time - last_event_time >= heartbeat_interval:
                    yield f": heartbeat {int(current_time)}\n\n"
                    logger.info(f"💓 Sent heartbeat at {elapsed}s")
                    last_event_time = current_time

                # Send actual event every 30 seconds
                if elapsed > 0 and elapsed % event_interval == 0 and current_time - last_event_time >= event_interval - 1:
                    counter += 1
                    yield f"id: {counter}\n"
                    yield f"event: test\n"
                    yield f"data: {json.dumps({'counter': counter, 'elapsed': elapsed, 'message': f'Event {counter} at {elapsed}s'})}\n\n"
                    logger.info(f"📡 Sent test event {counter} at {elapsed}s")
                    last_event_time = current_time

                try:
                    await asyncio.sleep(1)  # Check every second
                except asyncio.CancelledError:
                    logger.warning(f"⚠️ asyncio.sleep cancelled at {elapsed}s")
                    raise

            # Send final done event
            yield f"id: {counter + 1}\n"
            yield f"event: done\n"
            yield f"data: {json.dumps({'message': 'Test completed', 'total_events': counter, 'duration': int(time.time() - start_time)})}\n\n"
            logger.info(f"✅ Test SSE completed - sent {counter} events over {int(time.time() - start_time)}s")

        except GeneratorExit:
            logger.warning(f"⚠️ Test SSE generator closed by client/server at {int(time.time() - start_time)}s")
            raise
        except Exception as e:
            logger.error(f"❌ Test SSE error at {int(time.time() - start_time)}s: {e}", exc_info=True)
            raise
        finally:
            logger.info(f"🏁 Test SSE generator finished at {int(time.time() - start_time)}s")

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Content-Encoding": "none",
        },
    )


async def _stream_openai_response(
    assistant: Any,
    user_message: str,
    conversation_history: List[Dict[str, str]],
    conversation_id: str,
    user_id: str,
) -> AsyncGenerator[str, None]:
    """
    Stream OpenAI agent response with SSE events.

    Args:
        assistant: OpenAIAssistantWrapper instance
        user_message: User's message
        conversation_history: Previous messages
        conversation_id: Conversation ID
        user_id: User ID

    Yields:
        SSE-formatted events
    """
    try:
        logger.info(f"Starting OpenAI streaming for conversation {conversation_id}")

        # Emit start event
        yield f"event: start\ndata: {json.dumps({'agent': 'OpenAI'})}\n\n"

        # Stream the response
        accumulated_content = ""
        hooks = []
        async for chunk in assistant.stream_message(
            user_message=user_message,
            conversation_history=conversation_history,
            conversation_id=conversation_id,
            user_id=user_id,
        ):
            # Check if chunk is a hook (JSON with __hook__ key)
            if chunk.startswith('{"__hook__":'):
                try:
                    hook_data = json.loads(chunk)
                    if "__hook__" in hook_data:
                        hook = hook_data["__hook__"]
                        hooks.append(hook)
                        logger.info(f"Received hook: {hook.get('type', 'unknown')}")
                        # Emit hook as a separate event
                        yield f"event: hook\ndata: {json.dumps(hook)}\n\n"
                except json.JSONDecodeError:
                    # Not a hook, treat as regular content
                    accumulated_content += chunk
                    yield f"event: content\ndata: {json.dumps({'chunk': chunk})}\n\n"
            # Check if chunk is SSE-formatted or raw content
            elif chunk.startswith("event:"):
                # Already formatted, yield as-is
                yield chunk
            else:
                # Raw content, format as SSE
                accumulated_content += chunk
                yield f"event: content\ndata: {json.dumps({'chunk': chunk})}\n\n"

        # Emit done event with hooks if any
        done_data = {
            'response': accumulated_content,
            'message_count': len(conversation_history) + 2
        }
        if hooks:
            done_data['hooks'] = hooks
            logger.info(f"Emitting done event with {len(hooks)} hook(s)")

        yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
        logger.info(f"OpenAI streaming completed for conversation {conversation_id}")

    except Exception as e:
        logger.exception(f"Error streaming OpenAI response: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@chat_bp.route("/<technical_id>/stream", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def stream_chat_message(technical_id: str) -> Response:
    """
    Stream AI response in real-time using Server-Sent Events (SSE).

    Supports both JSON (text-only) and multipart/form-data (with file attachments).

    Provides real-time updates including:
    - Agent transitions (which agent is active)
    - Tool executions (which tools are being called)
    - Content chunks (streaming LLM responses)
    - Progress updates
    - Error states

    Returns:
        SSE stream with events: start, agent, tool, content, progress, error, done
    """
    try:
        user_id, is_superuser = await _get_user_info()
        logger.info(
            f"Stream chat message - user_id: {user_id}, conversation_id: {technical_id}"
        )

        # Get conversation
        conversation = await _get_conversation(technical_id)
        if not conversation:
            # Return error as SSE event
            async def error_stream():
                yield f"event: error\ndata: {json.dumps({'error': 'Chat not found'})}\n\n"

            return Response(error_stream(), mimetype="text/event-stream")

        # Validate ownership
        try:
            await _validate_chat_ownership(conversation, user_id, is_superuser)
        except PermissionError:

            async def error_stream():
                yield f"event: error\ndata: {json.dumps({'error': 'Access denied'})}\n\n"

            return Response(error_stream(), mimetype="text/event-stream")

        # Get message and files from request (support both JSON and form-data)
        file_blob_ids = []
        if request.is_json:
            # JSON request (text-only)
            data = await request.get_json()
            user_message = data.get("message", "")
        else:
            # Form data (potentially with files)
            form = await request.form
            user_message = form.get("message", "")

            # Handle file uploads - save to edge messages
            files = await request.files
            if files:
                import base64

                for file_key in files:
                    file = files[file_key]

                    # Read file content
                    file_content = file.read()

                    # Encode as base64
                    base64_content = base64.b64encode(file_content).decode("utf-8")

                    # Create edge message content
                    edge_message_content = {
                        "message": base64_content,
                        "metadata": {
                            "filename": file.filename,
                            "encoding": "base64",
                            "content_type": file.content_type
                            or "application/octet-stream",
                            "size": len(file_content),
                        },
                    }

                    # Send edge message
                    from common.config.config import (
                        CYODA_ENTITY_TYPE_EDGE_MESSAGE,
                        ENTITY_VERSION,
                    )
                    from services.services import get_repository

                    repository = get_repository()
                    meta = {
                        "type": CYODA_ENTITY_TYPE_EDGE_MESSAGE,
                        "entity_model": "flow_edge_message",
                        "entity_version": ENTITY_VERSION,
                    }

                    edge_message_id = await repository.save(
                        meta=meta, entity=edge_message_content
                    )

                    if edge_message_id:
                        file_blob_ids.append(edge_message_id)
                        logger.info(
                            f"✅ Uploaded file {file.filename} -> edge message {edge_message_id}"
                        )
                    else:
                        logger.error(f"❌ Failed to upload file {file.filename}")

                        async def error_stream():
                            yield f"event: error\ndata: {json.dumps({'error': f'Failed to upload file {file.filename}'})}\n\n"

                        return Response(error_stream(), mimetype="text/event-stream")

        if not user_message:

            async def error_stream():
                yield f"event: error\ndata: {json.dumps({'error': 'Message is required'})}\n\n"

            return Response(error_stream(), mimetype="text/event-stream")

        # Save user message as edge message
        persistence_service = _get_edge_message_persistence_service()
        user_message_edge_id = await persistence_service.save_message_as_edge_message(
            message_type="user",
            message_content=user_message,
            conversation_id=technical_id,
            user_id=user_id,
            file_blob_ids=file_blob_ids if file_blob_ids else None,
        )
        logger.info(f"✅ User message saved as edge message: {user_message_edge_id}")

        # Add user message to conversation immediately (with edge message ID)
        conversation.add_message(
            "user", user_message_edge_id, file_blob_ids if file_blob_ids else None
        )

        # Also accumulate files at conversation level for easy retrieval
        if file_blob_ids:
            if conversation.file_blob_ids is None:
                conversation.file_blob_ids = []
            # Add new files to conversation-level list (avoid duplicates)
            for file_id in file_blob_ids:
                if file_id not in conversation.file_blob_ids:
                    conversation.file_blob_ids.append(file_id)
            logger.info(
                f"📎 Conversation now has {len(conversation.file_blob_ids)} total files"
            )

        conversation = await _update_conversation(conversation)

        # Get assistant
        assistant = _get_cyoda_assistant()

        # Build message with file information if files were attached
        message_to_process = user_message
        if file_blob_ids:
            message_to_process = (
                f"{user_message} (with {len(file_blob_ids)} attached file(s))"
            )

        # Stream the response
        async def event_generator():
            accumulated_response = ""
            adk_session_id_result = None
            ui_functions_result = []
            repository_info_result = None
            build_task_id_result = None
            hook_result = None  # Initialize hook variable
            done_event_sent = False
            done_event_to_send = None
            stream_error = None
            streaming_events = []  # Track all streaming events for debug history

            try:
                # Route to appropriate streaming handler based on SDK
                if is_using_openai_sdk():
                    streaming_generator = _stream_openai_response(
                        assistant=assistant,
                        user_message=message_to_process,
                        conversation_history=conversation.messages,
                        conversation_id=technical_id,
                        user_id=user_id,
                    )
                else:
                    streaming_generator = StreamingService.stream_agent_response(
                        agent_wrapper=assistant,
                        user_message=message_to_process,
                        conversation_history=conversation.messages,
                        conversation_id=technical_id,
                        adk_session_id=conversation.adk_session_id,
                        user_id=user_id,
                    )

                async for sse_event in streaming_generator:
                    # Parse event to accumulate response
                    if "event: content" in sse_event:
                        try:
                            data_line = [
                                line
                                for line in sse_event.split("\n")
                                if line.startswith("data: ")
                            ][0]
                            event_data = json.loads(
                                data_line[6:]
                            )  # Remove "data: " prefix
                            accumulated_response += event_data.get("chunk", "")
                            # Track streaming event
                            streaming_events.append({
                                "type": "content",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "chunk_length": len(event_data.get("chunk", "")),
                            })
                        except Exception:
                            pass
                        # Forward content events immediately
                        yield sse_event

                    # Capture final data from done event but DON'T send it yet
                    elif "event: done" in sse_event:
                        done_event_sent = True
                        done_event_to_send = sse_event  # Store it for later
                        try:
                            data_line = [
                                line
                                for line in sse_event.split("\n")
                                if line.startswith("data: ")
                            ][0]
                            event_data = json.loads(data_line[6:])
                            logger.info(f"📤 Done event received - response length: {len(event_data.get('response', ''))}")
                            logger.info(f"📤 Done event data keys: {list(event_data.keys())}")
                            accumulated_response = event_data.get(
                                "response", accumulated_response
                            )
                            logger.info(f"📤 Final accumulated_response length: {len(accumulated_response)}")
                            adk_session_id_result = event_data.get("adk_session_id")
                            ui_functions_result = event_data.get("ui_functions", [])
                            repository_info_result = event_data.get(
                                "repository_info"
                            )  # Extract repository info
                            build_task_id_result = event_data.get(
                                "build_task_id"
                            )  # Extract build task ID
                            hook_result = event_data.get("hook")  # Extract hook for persistence
                            # Track done event
                            streaming_events.append({
                                "type": "done",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                        except Exception as done_parse_error:
                            logger.error(f"❌ Error parsing done event: {done_parse_error}")
                            pass
                        # DON'T yield the done event yet - we need to save conversation first

                    else:
                        # Forward all other events (start, agent, tool, etc.)
                        # Track other events
                        event_type = "unknown"
                        if "event: start" in sse_event:
                            event_type = "start"
                        elif "event: agent" in sse_event:
                            event_type = "agent"
                        elif "event: tool" in sse_event:
                            event_type = "tool"
                        elif "event: error" in sse_event:
                            event_type = "error"

                        streaming_events.append({
                            "type": event_type,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                        yield sse_event

            except Exception as e:
                stream_error = str(e)
                logger.error(f"Error in stream generator: {e}", exc_info=True)

                # Check if this is an OpenAI tool-related error
                is_tool_error = (
                    ("tool_call_id" in stream_error and "must be followed by tool messages" in stream_error) or
                    ("No tool output found for function call" in stream_error) or
                    ("invalid_request_error" in stream_error and "tool" in stream_error.lower())
                )

                if is_tool_error:
                    logger.warning(f"⚠️ Detected OpenAI tool synchronization error - clearing ADK session to recover")
                    # Clear the ADK session to start fresh
                    try:
                        from services.services import get_session_service
                        session_service = get_session_service()
                        if conversation.adk_session_id:
                            await session_service.delete_session(conversation.adk_session_id)
                            conversation.adk_session_id = None
                            await _update_conversation(conversation)
                            logger.info(f"✅ Cleared corrupted ADK session")

                            # Send helpful error message to user
                            error_data = {
                                'error': 'Tool synchronization error detected. The conversation state has been reset. Please send your message again.',
                                'recoverable': True,
                                'error_type': 'tool_sync_error'
                            }
                            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                        else:
                            yield f"event: error\ndata: {json.dumps({'error': stream_error})}\n\n"
                    except Exception as clear_error:
                        logger.error(f"Failed to clear ADK session: {clear_error}")
                        yield f"event: error\ndata: {json.dumps({'error': stream_error})}\n\n"
                else:
                    yield f"event: error\ndata: {json.dumps({'error': stream_error})}\n\n"

            finally:
                # Post-processing: Save AI response to conversation and edge messages
                # This happens BEFORE sending the done event
                logger.info(f"🔄 FINALLY BLOCK STARTED - accumulated_response length: {len(accumulated_response)}")
                logger.info(f"🔄 done_event_sent: {done_event_sent}, done_event_to_send: {done_event_to_send is not None}")
                logger.info(f"🔄 Streaming events tracked: {len(streaming_events)}")
                post_processing_error = None
                edge_message_ids = {}  # Track edge message IDs
                try:
                    # Check if we need to update the conversation
                    # Update if: we have a response, OR we have metadata to save
                    has_response = accumulated_response and accumulated_response.strip()
                    has_metadata = (
                        adk_session_id_result
                        or ui_functions_result
                        or repository_info_result
                        or build_task_id_result
                        or hook_result  # Include hook in metadata check
                    )

                    if has_response or has_metadata:
                        # Save response and debug history as edge messages
                        persistence_service = _get_edge_message_persistence_service()

                        if has_response:
                            # Save response with streaming debug history
                            logger.info(f"💾 Saving response and debug history as edge message...")
                            response_edge_message_id = await persistence_service.save_response_with_history(
                                conversation_id=technical_id,
                                user_id=user_id,
                                response_content=accumulated_response,
                                streaming_events=streaming_events,
                                metadata={"hook": hook_result} if hook_result else None,
                            )
                            logger.info(f"✅ Response saved as edge message: {response_edge_message_id}")

                        # Reload conversation to get latest version
                        fresh_conversation = await _get_conversation(technical_id)
                        if fresh_conversation:
                            logger.info(f"📥 Loaded fresh conversation with {len(fresh_conversation.messages)} existing messages")

                            # Add message only if we have actual content
                            if has_response and response_edge_message_id:
                                # Prepare metadata with hook
                                message_metadata = {
                                    "hook": hook_result,
                                } if hook_result else None

                                fresh_conversation.add_message(
                                    "ai",
                                    response_edge_message_id,
                                    metadata=message_metadata
                                )
                                logger.info(f"💬 Added AI response to conversation")
                                logger.info(f"📊 Conversation now has {len(fresh_conversation.messages)} messages")
                                if hook_result:
                                    logger.info(f"🎣 Saved hook in message metadata: {hook_result.get('type')}")
                                logger.info(f"📨 Linked edge message: {response_edge_message_id}")

                            # Update adk_session_id if this is the first message
                            if (
                                not fresh_conversation.adk_session_id
                                and adk_session_id_result
                            ):
                                fresh_conversation.adk_session_id = adk_session_id_result
                                logger.info(f"🔑 Updated ADK session ID: {adk_session_id_result}")

                            # Add UI functions if any
                            if ui_functions_result:
                                for ui_func in ui_functions_result:
                                    # Ensure ui_func is a dict, not a string
                                    if isinstance(ui_func, str):
                                        try:
                                            ui_func = json.loads(ui_func)
                                        except json.JSONDecodeError:
                                            logger.error(f"Failed to parse ui_func string: {ui_func}")
                                            continue

                                    # Create properly formatted message entry
                                    message_entry = {
                                        "type": "ui_function",
                                        "message": ui_func,  # Store as dict, not JSON string
                                        "ui_function": ui_func,  # Store as dict, not JSON string
                                        "timestamp": datetime.now(timezone.utc).isoformat(),
                                        "approve": False,
                                        "consumed": True,
                                        "technical_id": str(uuid.uuid4()),
                                        "user_id": fresh_conversation.user_id or "default",
                                        "file_blob_ids": None,
                                        "publish": True,
                                        "failed": False,
                                        "error": None,
                                        "error_code": "None",
                                        "current_state": None,
                                        "current_transition": None,
                                        "workflow_name": None,
                                        "metadata": None,
                                        "last_modified": int(
                                            datetime.now(timezone.utc).timestamp() * 1000
                                        ),
                                        "last_modified_at": datetime.now(timezone.utc).strftime(
                                            "%Y-%m-%d %H:%M:%S"
                                        ),
                                    }
                                    fresh_conversation.messages.append(message_entry)
                                logger.info(f"🎨 Added {len(ui_functions_result)} UI functions")

                            # Update repository info from tool_context.state (set by build agent)
                            # This is the ONLY place where conversation entity is updated with repository info
                            if repository_info_result:
                                logger.info(
                                    f"📦 Updating conversation with repository info: {repository_info_result}"
                                )
                                fresh_conversation.workflow_cache["repository_name"] = (
                                    repository_info_result.get("repository_name")
                                )
                                fresh_conversation.workflow_cache["repository_owner"] = (
                                    repository_info_result.get("repository_owner")
                                )
                                fresh_conversation.workflow_cache["repository_branch"] = (
                                    repository_info_result.get("repository_branch")
                                )

                                # Also set root-level fields (for Pydantic model compatibility)
                                fresh_conversation.repository_name = (
                                    repository_info_result.get("repository_name")
                                )
                                fresh_conversation.repository_owner = (
                                    repository_info_result.get("repository_owner")
                                )
                                fresh_conversation.repository_branch = (
                                    repository_info_result.get("repository_branch")
                                )
                                fresh_conversation.repository_url = (
                                    repository_info_result.get("repository_url")
                                )
                                fresh_conversation.installation_id = (
                                    repository_info_result.get("installation_id")
                                )

                            # Add build task ID to conversation from tool_context.state (set by build agent)
                            if build_task_id_result:
                                if (
                                    build_task_id_result
                                    not in fresh_conversation.background_task_ids
                                ):
                                    fresh_conversation.background_task_ids.append(
                                        build_task_id_result
                                    )
                                    logger.info(
                                        f"📋 Added build task {build_task_id_result} to conversation background_task_ids"
                                    )

                            # Save conversation - this is the SINGLE place where conversation is updated
                            logger.info(f"💾 About to save conversation with {len(fresh_conversation.messages)} messages")
                            logger.info(f"💾 Last message: {fresh_conversation.messages[-1] if fresh_conversation.messages else 'NONE'}")
                            saved_conversation = await _update_conversation(fresh_conversation)
                            logger.info(f"✅ Conversation saved successfully with {len(saved_conversation.messages)} messages")
                            logger.info(f"✅ Saved conversation last message: {saved_conversation.messages[-1] if saved_conversation.messages else 'NONE'}")
                    else:
                        logger.info(f"ℹ️ No response or metadata to save, skipping conversation update")
                except Exception as post_error:
                    post_processing_error = str(post_error)
                    logger.error(f"Error in post-processing: {post_error}", exc_info=True)
                    # Don't re-raise - we still want to send the done event

                # NOW send the done event (after conversation is saved)
                if done_event_to_send:
                    # If there was a post-processing error, modify the done event to include it
                    if post_processing_error:
                        try:
                            # Parse the original done event and add error info
                            data_line = [
                                line
                                for line in done_event_to_send.split("\n")
                                if line.startswith("data: ")
                            ][0]
                            event_data = json.loads(data_line[6:])
                            event_data["post_processing_error"] = post_processing_error
                            event_data["message"] = f"Stream completed with post-processing error: {post_processing_error}"
                            yield f"event: done\ndata: {json.dumps(event_data)}\n\n"
                        except Exception:
                            # Fallback: just send the original done event
                            yield done_event_to_send
                    else:
                        yield done_event_to_send
                elif not done_event_sent:
                    # Fallback: create a done event if one wasn't received
                    logger.warning("Done event was not sent by streaming service, sending it now")
                    done_data = {
                        'message': 'Stream completed',
                        'response': accumulated_response
                    }
                    if stream_error:
                        done_data['error'] = stream_error
                        done_data['message'] = f'Stream ended with error: {stream_error}'
                    if post_processing_error:
                        done_data['post_processing_error'] = post_processing_error
                        done_data['message'] = f'Stream completed with post-processing error: {post_processing_error}'
                    yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

        return Response(
            event_generator(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Connection": "keep-alive",
                "Content-Encoding": "none",  # Prevent compression which can buffer
            },
        )

    except Exception as stream_error:
        logger.exception(f"Error setting up stream: {stream_error}")
        error_message = str(stream_error)

        async def error_stream():
            yield f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"

        return Response(error_stream(), mimetype="text/event-stream")


@chat_bp.route("/canvas-questions", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def submit_canvas_question() -> tuple[Response, int]:
    """
    Submit a canvas question for stateless AI generation.

    MOCK: Returns hardcoded structured responses for testing.
    """
    try:
        data = await request.get_json()

        question = data.get("question")
        response_type = data.get("response_type")
        context = data.get("context", {})

        if not question:
            return jsonify({"error": "Missing required field: question"}), 400

        if not response_type:
            return jsonify({"error": "Missing required field: response_type"}), 400

        # Validate response_type
        valid_types = [
            "entity_json",
            "workflow_json",
            "app_config_json",
            "environment_json",
            "requirement_json",
            "text",
        ]
        if response_type not in valid_types:
            return (
                jsonify(
                    {
                        "error": "Invalid request",
                        "details": {
                            "field": "response_type",
                            "message": f"Must be one of: {', '.join(valid_types)}",
                        },
                    }
                ),
                400,
            )

        # Generate structured response using Google ADK
        try:
            if google_adk_service.is_configured() and response_type != "text":
                # Get schema for structured output
                schema = _get_canvas_schema(response_type)

                # Build detailed prompt
                prompt = _build_canvas_prompt(response_type, question, context)

                # Generate structured output
                generated_data = await google_adk_service.generate_structured_output(
                    prompt=prompt,
                    schema=schema,
                    system_instruction="You are an expert in Cyoda platform configuration. Generate valid, production-ready configurations.",
                )

                message = f"I've created a {response_type.replace('_', ' ')} based on your requirements."

            elif response_type == "text":
                # For text responses, use regular generation
                if google_adk_service.is_configured():
                    text_response = await google_adk_service.generate_response(
                        prompt=question,
                        system_instruction="You are a helpful AI assistant for the Cyoda platform.",
                    )
                    generated_data = {"text": text_response}
                    message = text_response
                else:
                    generated_data = {"text": f"[MOCK] Response to: {question}"}
                    message = generated_data["text"]
            else:
                # Fallback to mock if Google ADK is not configured
                logger.warning("Google ADK not configured - using mock response")
                generated_data = _generate_mock_canvas_response(
                    response_type, question, context
                )
                message = f"[MOCK] I've created a {response_type.replace('_', ' ')} based on your requirements. Please configure GOOGLE_API_KEY for real AI generation."

            result = {
                "message": message,
                "hook": {
                    "type": response_type.replace("_json", "_config"),
                    "action": "preview",
                    "data": generated_data,
                },
            }

            return jsonify(result), 200

        except Exception as ai_error:
            logger.exception(f"Error generating canvas response: {ai_error}")
            # Fallback to mock on error
            mock_data = _generate_mock_canvas_response(response_type, question, context)
            result = {
                "message": f"Error generating response: {str(ai_error)}. Using fallback data.",
                "hook": {
                    "type": response_type.replace("_json", "_config"),
                    "action": "preview",
                    "data": mock_data,
                },
            }
            return jsonify(result), 200
    except Exception as e:
        logger.exception(f"Error in canvas question: {e}")
        return jsonify({"error": str(e)}), 400


def _get_canvas_schema(response_type: str) -> Dict[str, Any]:
    """Get JSON schema for structured output based on response type."""
    if response_type == "entity_json":
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "required": {"type": "boolean"},
                        },
                    },
                },
                "description": {"type": "string"},
            },
            "required": ["name", "fields"],
        }
    elif response_type == "workflow_json":
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "states": {"type": "array", "items": {"type": "string"}},
                "transitions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "name": {"type": "string"},
                        },
                    },
                },
                "initial_state": {"type": "string"},
            },
            "required": ["name", "states", "transitions", "initial_state"],
        }
    elif response_type == "app_config_json":
        return {
            "type": "object",
            "properties": {
                "app_name": {"type": "string"},
                "entities": {"type": "array", "items": {"type": "string"}},
                "workflows": {"type": "array", "items": {"type": "string"}},
                "language": {"type": "string"},
            },
            "required": ["app_name"],
        }
    else:
        # Generic schema for other types
        return {
            "type": "object",
            "properties": {"data": {"type": "object"}, "message": {"type": "string"}},
        }


def _build_canvas_prompt(
    response_type: str, question: str, context: Dict[str, Any]
) -> str:
    """Build detailed prompt for canvas question generation."""
    base_prompt = f"User request: {question}\n\n"

    if response_type == "entity_json":
        base_prompt += (
            "Generate a Cyoda entity configuration with:\n"
            "- A descriptive name (PascalCase)\n"
            "- Fields with name, type (string/number/boolean/date), and required flag\n"
            "- A clear description of the entity's purpose\n"
        )
    elif response_type == "workflow_json":
        base_prompt += (
            "Generate a workflow configuration with:\n"
            "- A descriptive name\n"
            "- States (array of state names)\n"
            "- Transitions (from state, to state, transition name)\n"
            "- Initial state\n"
        )
    elif response_type == "app_config_json":
        app_name = context.get("app_name", "MyApp")
        base_prompt += (
            f"Generate an application configuration for '{app_name}' with:\n"
            "- Application name\n"
            "- List of entities\n"
            "- List of workflows\n"
            "- Programming language (python/java/javascript)\n"
        )

    if context:
        base_prompt += f"\n\nAdditional context: {context}"

    return base_prompt


def _generate_mock_canvas_response(
    response_type: str, question: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate mock structured response for canvas questions (fallback)."""
    if response_type == "entity_json":
        return {
            "name": "MockEntity",
            "fields": [
                {"name": "id", "type": "string", "required": True},
                {"name": "name", "type": "string", "required": True},
                {"name": "description", "type": "string", "required": False},
            ],
            "description": f"Mock entity generated from: {question[:50]}",
        }
    elif response_type == "workflow_json":
        return {
            "name": "MockWorkflow",
            "states": ["draft", "active", "completed"],
            "transitions": [
                {"from": "draft", "to": "active", "name": "activate"},
                {"from": "active", "to": "completed", "name": "complete"},
            ],
            "initial_state": "draft",
        }
    elif response_type == "app_config_json":
        return {
            "app_name": context.get("app_name", "MockApp"),
            "entities": ["MockEntity"],
            "workflows": ["MockWorkflow"],
            "language": context.get("language", "python"),
        }
    else:
        return {"mock": True, "type": response_type, "question": question}


@chat_bp.route("/<technical_id>/approve", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def approve(technical_id: str) -> tuple[Response, int]:
    """Approve current state and proceed (workflow control)."""
    try:
        conversation = await _get_conversation(technical_id)
        if not conversation:
            return jsonify({"error": "Chat not found"}), 404

        # TODO: Phase 4 - implement workflow transitions
        return jsonify({"message": "Approved successfully"}), 200
    except Exception as e:
        logger.exception(f"Error approving: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/<technical_id>/rollback", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def rollback(technical_id: str) -> tuple[Response, int]:
    """Rollback to previous state (workflow control)."""
    try:
        conversation = await _get_conversation(technical_id)
        if not conversation:
            return jsonify({"error": "Chat not found"}), 404

        # TODO: Phase 4 - implement workflow transitions
        return jsonify({"message": "Rolled back successfully"}), 200
    except Exception as e:
        logger.exception(f"Error rolling back: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/<technical_id>/files/<blob_id>", methods=["GET"])
async def download_file(
    technical_id: str, blob_id: str
) -> tuple[Response | Dict[str, Any], int]:
    """Download a file by blob ID from a chat."""
    try:
        conversation = await _get_conversation(technical_id)
        if not conversation:
            return jsonify({"error": "Chat not found"}), 404

        # TODO: Phase 2 - implement real file download from Cyoda blobs
        # Mock file download for now
        mock_content = f"Mock file content for blob {blob_id}".encode()

        response = Response(
            mock_content,
            mimetype="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="mock_file_{blob_id}.txt"',
                "Content-Length": str(len(mock_content)),
                "Cache-Control": "no-cache",
            },
        )
        return response, 200
    except Exception as e:
        logger.exception(f"Error downloading file: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/transfer", methods=["POST"])
@rate_limit(100, timedelta(minutes=1), key_function=_rate_limit_key)
async def transfer_chats() -> tuple[Response, int]:
    """
    Transfer guest chats to authenticated user.

    This endpoint allows authenticated users to transfer chats that were created
    while they were using the application as a guest user. The transfer process:

    1. Validates the current user is authenticated (not a guest)
    2. Extracts and validates the guest token from the request
    3. Finds all chats belonging to the guest user
    4. Updates the user_id of each chat to the authenticated user
    5. Invalidates chat cache for both users
    6. Returns the count of successfully transferred chats

    Request body:
        {
            "guest_token": "JWT token of the guest user"
        }

    Returns:
        200: Success with transfer count
        400: Invalid request (missing token, invalid token, or guest-to-guest transfer)
        500: Server error
    """
    try:
        # Get current authenticated user
        current_user_id, _ = await _get_user_info()

        # Ensure we have an authenticated user (not a guest)
        if current_user_id.startswith("guest."):
            return jsonify({"error": "Cannot transfer chats to guest user"}), 400

        data = await request.get_json()
        guest_token = data.get("guest_token")

        if not guest_token:
            return jsonify({"error": "guest_token is required"}), 400

        # Extract guest user ID from the guest token
        try:
            guest_user_id, _ = get_user_info_from_token(guest_token)
        except (TokenValidationError, TokenExpiredError) as e:
            logger.warning(f"Invalid guest token: {e}")
            return jsonify({"error": "Invalid guest token"}), 400

        # Ensure the token is actually a guest token
        if not guest_user_id.startswith("guest."):
            return jsonify({"error": "Token is not a guest token"}), 400

        logger.info(f"🔄 Starting chat transfer from {guest_user_id} to {current_user_id}")

        # Find all chats belonging to the guest user
        search_condition = (
            SearchConditionRequest.builder()
            .equals("user_id", guest_user_id)
            .build()
        )

        guest_chats = await service.search(
            entity_class=Conversation.ENTITY_NAME,
            condition=search_condition,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        transferred_count = 0

        if isinstance(guest_chats, list):
            for chat_response in guest_chats:
                if hasattr(chat_response, "data") and hasattr(chat_response, "metadata"):
                    # Get the conversation entity
                    conversation = await _get_conversation(chat_response.metadata.id)
                    if conversation:
                        # Update the user_id to the authenticated user
                        conversation.user_id = current_user_id

                        # Update the conversation in storage
                        entity_data = conversation.model_dump(by_alias=False)
                        await service.update(
                            entity_id=chat_response.metadata.id,
                            entity=entity_data,
                            entity_class=Conversation.ENTITY_NAME,
                            entity_version=str(Conversation.ENTITY_VERSION),
                        )
                        transferred_count += 1

                        logger.debug(f"✅ Transferred chat {conversation.technical_id}")

        # Invalidate cache for both users
        guest_cache_key = f"chats:{guest_user_id}"
        current_cache_key = f"chats:{current_user_id}"

        if guest_cache_key in _chat_list_cache:
            del _chat_list_cache[guest_cache_key]
            logger.debug(f"Cache invalidated for guest user: {guest_cache_key}")

        if current_cache_key in _chat_list_cache:
            del _chat_list_cache[current_cache_key]
            logger.debug(f"Cache invalidated for current user: {current_cache_key}")

        logger.info(f"✅ Chat transfer completed: {transferred_count} chats transferred from {guest_user_id} to {current_user_id}")

        return jsonify({
            "message": "Chats transferred successfully",
            "transferred_count": transferred_count
        }), 200

    except Exception as e:
        logger.exception(f"Error transferring chats: {e}")
        return jsonify({"error": str(e)}), 500
