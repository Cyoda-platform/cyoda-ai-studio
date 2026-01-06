"""Session initialization and activation for CyodaSessionService.

Handles session creation, entity persistence, and activation via Cyoda transitions.
"""

import logging
import uuid
from typing import Optional

from application.entity.adk_session import AdkSession
from common.service.entity_service import EntityService

logger = logging.getLogger(__name__)


async def save_session_entity(
    entity_service: EntityService,
    session_id: str,
    app_name: str,
    user_id: str,
    state: dict,
    entity_name: str = "AdkSession",
    entity_version: str = "1",
) -> tuple[AdkSession, str]:
    """Save session entity to Cyoda.

    Args:
        entity_service: Cyoda entity service for persistence
        session_id: Session ID
        app_name: Application name
        user_id: User ID
        state: Session state
        entity_name: Cyoda entity class name
        entity_version: Cyoda entity version

    Returns:
        Tuple of (adk_session, technical_id)
    """
    adk_session = AdkSession.from_adk_session(
        session_id=session_id,
        app_name=app_name,
        user_id=user_id,
        state=state or {},
        events=[],
    )

    logger.debug(f"Saving AdkSession entity: {adk_session.model_dump()}")
    response = await entity_service.save(
        entity=adk_session.model_dump(),
        entity_class=entity_name,
        entity_version=entity_version,
    )

    adk_session.technical_id = response.metadata.id
    logger.info(
        f"Session saved with technical_id={response.metadata.id}, state={response.metadata.state}"
    )

    return adk_session, response.metadata.id


async def activate_session(
    entity_service: EntityService,
    session_id: str,
    technical_id: str,
    entity_name: str = "AdkSession",
    entity_version: str = "1",
) -> None:
    """Activate session via transition.

    Args:
        entity_service: Cyoda entity service
        session_id: Session ID
        technical_id: Technical ID
        entity_name: Cyoda entity class name
        entity_version: Cyoda entity version
    """
    try:
        logger.debug(f"Activating session {session_id} via 'activate' transition")
        await entity_service.execute_transition(
            entity_id=technical_id,
            transition="activate",
            entity_class=entity_name,
            entity_version=entity_version,
        )
        logger.info(f"Session {session_id} activated successfully")
    except Exception as e:
        logger.error(f"Failed to activate session {session_id}: {e}", exc_info=True)


def normalize_session_id(session_id: Optional[str]) -> str:
    """Normalize session ID, generating if not provided.

    Args:
        session_id: Optional session ID

    Returns:
        Normalized session ID
    """
    if session_id and session_id.strip():
        return session_id.strip()

    return str(uuid.uuid4())
