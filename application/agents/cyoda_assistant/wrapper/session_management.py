"""Session management operations for CyodaAssistantWrapper.

Handles session loading, saving, creation, retrieval, and verification.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from application.entity.conversation import Conversation
from common.service.service import EntityServiceError

logger = logging.getLogger(__name__)

# Constants for session management
_APP_NAME = "cyoda-assistant"
_SESSION_TECHNICAL_ID_KEY = "__cyoda_technical_id__"
_ADK_SESSION_STATE_KEY = "adk_session_state"
_MAX_SESSION_SAVE_RETRIES = 5
_BASE_RETRY_DELAY_SECONDS = 0.1


async def _get_session_by_technical_id(runner, technical_id: str) -> Any:
    """Retrieve session by technical ID using CyodaSessionService.

    Args:
        runner: ADK Runner instance
        technical_id: ADK session technical ID

    Returns:
        ADK session or None if not found
    """
    from application.services.cyoda_session_service import CyodaSessionService

    if not isinstance(runner.session_service, CyodaSessionService):
        return None

    try:
        adk_session_entity = (
            await runner.session_service.get_session_by_technical_id(
                technical_id
            )
        )
        if adk_session_entity:
            return runner.session_service._to_adk_session(
                adk_session_entity
            )
    except Exception as e:
        logger.debug(f"Failed to get session by technical_id: {e}")

    return None


async def _get_or_create_session(
    runner,
    session_id: str,
    user_id: str,
    session_state: dict[str, Any],
) -> tuple[Any, str | None]:
    """Get existing session or create new one.

    Returns:
        Tuple of (session, session_technical_id)
    """
    # Try to get existing session
    session = await runner.session_service.get_session(
        app_name=_APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    if session:
        logger.info(f"Session {session_id} exists, updating state")
        # Update existing session state
        for key, value in session_state.items():
            session.state[key] = value
        # Get technical ID from session state if available
        session_technical_id = session.state.get(_SESSION_TECHNICAL_ID_KEY)
        if session_technical_id:
            logger.info(
                f"Retrieved technical_id from session state: {session_technical_id}"
            )
        return session, session_technical_id

    # Create new session
    logger.info(f"Session {session_id} does not exist, creating new session")
    try:
        created_session = await runner.session_service.create_session(
            app_name=_APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state=session_state,
        )
        logger.info(f"Session created: {created_session.id}")

        # Get technical ID from created session
        session_technical_id = created_session.state.get(
            _SESSION_TECHNICAL_ID_KEY
        )
        if session_technical_id:
            logger.info(f"AdkSession technical_id: {session_technical_id}")
        else:
            logger.warning(
                "Created session does not have technical_id in state!"
            )

        return created_session, session_technical_id

    except Exception as create_error:
        logger.error(
            f"Failed to create session {session_id}: {create_error}",
            exc_info=True,
        )
        raise ValueError(
            f"Failed to create session: {create_error}"
        ) from create_error


async def _load_session_state(entity_service, conversation_id: str) -> dict[str, Any]:
    """Load ADK session state from Cyoda Conversation.workflow_cache.

    Args:
      conversation_id: Cyoda Conversation technical ID

    Returns:
      Session state dictionary (empty if not found)
    """
    try:
        response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not response:
            return {}

        conversation_data = response.data if hasattr(response, "data") else response
        conversation = Conversation(**conversation_data)

        return conversation.workflow_cache.get("adk_session_state", {})

    except Exception as e:
        logger.warning(f"Failed to load session state: {e}")
        return {}


async def _save_session_state(
    entity_service, conversation_id: str, session_state: dict[str, Any]
) -> None:
    """Save ADK session state to Cyoda Conversation.workflow_cache.
    Includes retry logic for version conflict errors.

    Args:
      conversation_id: Cyoda Conversation technical ID
      session_state: Session state dictionary to save
    """
    max_retries = _MAX_SESSION_SAVE_RETRIES
    base_delay = _BASE_RETRY_DELAY_SECONDS

    for attempt in range(max_retries):
        try:
            response = await entity_service.get_by_id(
                entity_id=conversation_id,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            if not response:
                logger.warning(
                    f"Conversation {conversation_id} not found for state save"
                )
                return

            conversation_data = (
                response.data if hasattr(response, "data") else response
            )
            conversation = Conversation(**conversation_data)

            # Update workflow_cache with session state
            conversation.workflow_cache[_ADK_SESSION_STATE_KEY] = session_state

            # Save back to Cyoda
            entity_data = conversation.model_dump(by_alias=False)
            await entity_service.update(
                entity_id=conversation_id,
                entity=entity_data,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            logger.debug(
                f"✓ Saved session state for conversation {conversation_id}"
            )
            if attempt > 0:
                logger.info(
                    f"Successfully saved session state after {attempt + 1} attempts"
                )
            return  # Success

        except EntityServiceError as e:
            error_str = str(e).lower()
            is_version_conflict = (
                "422" in error_str
                or "500" in error_str
                or "version mismatch" in error_str
                or "earliestupdateaccept" in error_str
                or "was changed by another transaction" in error_str
                or "update operation returned no entity id" in error_str
            )

            if is_version_conflict and attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Version conflict saving session state for {conversation_id} "
                    f"(attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {delay:.3f}s... Error: {str(e)[:100]}"
                )
                await asyncio.sleep(delay)
                continue  # Retry
            else:
                # Non-retryable error or max retries reached
                logger.error(
                    f"Failed to save session state after {attempt + 1} attempts: {e}"
                )
                return  # Don't crash, just log the error

        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
            return  # Don't crash on unexpected errors


async def _verify_session_retrievable(
    runner, session_id: str, session_technical_id: str
) -> None:
    """Verify session is retrievable by technical ID.

    Args:
        runner: ADK Runner instance
        session_id: Session ID for logging
        session_technical_id: Technical ID to verify
    """
    from application.services.cyoda_session_service import CyodaSessionService

    if not isinstance(runner.session_service, CyodaSessionService):
        return

    logger.debug(f"Verifying session by technical_id: {session_technical_id}")
    adk_session_entity = (
        await runner.session_service.get_session_by_technical_id(
            session_technical_id
        )
    )
    if adk_session_entity:
        logger.info(f"Session {session_id} verified as retrievable by technical_id")
    else:
        logger.error(
            f"Session {session_id} was created but is not retrievable by technical_id!"
        )


async def _build_initial_session_state(
    entity_service,
    conversation_history: list[dict[str, str]],
    user_id: str,
    conversation_id: str | None,
) -> dict[str, Any]:
    """Build initial session state with conversation context.

    Args:
        entity_service: Entity service for persistence
        conversation_history: Previous messages in the conversation
        user_id: User ID from authentication
        conversation_id: Cyoda Conversation technical ID

    Returns:
        Session state dictionary
    """
    session_state = {}

    # Load persistent session state from Cyoda if conversation exists
    if conversation_id:
        session_state = await _load_session_state(entity_service, conversation_id)

    # Add current context
    session_state["conversation_history"] = conversation_history
    session_state["user_id"] = user_id
    session_state["conversation_id"] = conversation_id

    return session_state
