"""Session management for streaming."""

import logging
from typing import Any, Dict, Optional

from application.services.session_service.utilities import (
    deserialize_event,
    to_adk_session,
)
from application.services.streaming.constants import (
    APP_NAME,
    CYODA_TECHNICAL_ID_KEY,
)

logger = logging.getLogger(__name__)


async def load_or_create_session(
    agent_wrapper: Any,
    conversation_id: str,
    adk_session_id: Optional[str],
    user_id: str,
    session_state: Dict[str, Any],
) -> tuple[Any, Optional[str]]:
    """Load existing session or create new one.

    Args:
        agent_wrapper: CyodaAssistantWrapper instance
        conversation_id: Conversation ID
        adk_session_id: ADK session ID (if exists)
        user_id: User ID
        session_state: Initial session state

    Returns:
        Tuple of (session, session_technical_id)
    """
    session = None
    session_technical_id = None

    # Try to load by technical ID first
    if adk_session_id and hasattr(
        agent_wrapper.runner.session_service, "get_session_by_technical_id"
    ):
        adk_session_entity = (
            await agent_wrapper.runner.session_service.get_session_by_technical_id(
                adk_session_id
            )
        )
        if adk_session_entity:
            session = to_adk_session(adk_session_entity, deserialize_event)
            session_technical_id = adk_session_id
            logger.info(
                f"✅ Loaded existing session via technical_id: {adk_session_id}"
            )

    # Try to load by conversation ID
    if not session:
        session = await agent_wrapper.runner.session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=conversation_id,
        )
        if session:
            session_technical_id = session.state.get(CYODA_TECHNICAL_ID_KEY)
            logger.info(
                f"✅ Loaded existing session via search: {conversation_id}, "
                f"technical_id={session_technical_id}"
            )

    # Create new session if not found
    if not session:
        created_session = await agent_wrapper.runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=conversation_id,
            state=session_state,
        )
        session_technical_id = created_session.state.get(CYODA_TECHNICAL_ID_KEY)
        session = created_session
        logger.info(
            f"✅ Created new session: {conversation_id}, "
            f"technical_id={session_technical_id}"
        )

    # Update session state
    if session:
        for key, value in session_state.items():
            session.state[key] = value

    return session, session_technical_id


async def save_session_state(
    agent_wrapper: Any,
    conversation_id: str,
    session_state: Dict[str, Any],
) -> None:
    """Save session state to persistence layer.

    Args:
        agent_wrapper: CyodaAssistantWrapper instance
        conversation_id: Conversation ID
        session_state: Session state to save
    """
    if conversation_id and session_state:
        await agent_wrapper._save_session_state(conversation_id, session_state)
