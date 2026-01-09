"""Session retrieval and lookup for CyodaSessionService.

Handles session fetching, searching, and optimized lookup by technical ID.
"""

import asyncio
import logging
from typing import Optional

from google.adk.sessions.base_session_service import GetSessionConfig
from google.adk.sessions.session import Session

from application.entity.adk_session import AdkSession
from common.search import CyodaOperator
from common.service.entity_service import EntityService, SearchConditionRequest

logger = logging.getLogger(__name__)


def is_uuid_format(session_id: str) -> bool:
    """Check if session ID looks like a UUID.

    Args:
        session_id: Session ID to check.

    Returns:
        True if ID matches UUID format.
    """
    return len(session_id) == 36 and session_id.count("-") == 4


async def fetch_session_from_cyoda(
    entity_service: EntityService,
    technical_id: str,
    entity_name: str = "AdkSession",
    entity_version: str = "1",
) -> Optional[AdkSession]:
    """Fetch session directly from Cyoda (bypasses cache).

    Args:
        entity_service: Cyoda entity service
        technical_id: Session technical ID
        entity_name: Cyoda entity class name
        entity_version: Cyoda entity version

    Returns:
        AdkSession or None
    """
    try:
        response = await entity_service.get_by_id(
            entity_id=technical_id,
            entity_class=entity_name,
            entity_version=entity_version,
        )

        if not response:
            return None

        if hasattr(response.data, "model_dump"):
            session_data = response.data.model_dump()
        elif isinstance(response.data, dict):
            session_data = response.data
        else:
            logger.error(f"Unexpected data type: {type(response.data)}")
            return None

        adk_session = AdkSession(**session_data)
        adk_session.technical_id = response.metadata.id
        return adk_session

    except Exception as e:
        logger.debug(f"Could not fetch session {technical_id}: {e}")
        return None


async def find_session_entity(
    entity_service: EntityService,
    app_name: str,
    user_id: str,
    session_id: str,
    entity_name: str = "AdkSession",
    entity_version: str = "1",
) -> Optional[AdkSession]:
    """Find a session entity in Cyoda using search.

    NOTE: This is slower than fetch_session_from_cyoda().
    Prefer storing and using the technical_id when possible.

    Args:
        entity_service: Cyoda entity service
        app_name: Application name
        user_id: User ID
        session_id: Session ID
        entity_name: Cyoda entity class name
        entity_version: Cyoda entity version

    Returns:
        AdkSession entity or None
    """
    logger.debug(
        f"Finding session by search: app_name={app_name}, user_id={user_id}, session_id={session_id}"
    )

    try:
        # Use search with session_id filter
        builder = SearchConditionRequest.builder()
        builder.add_condition("session_id", CyodaOperator.EQUALS, session_id)

        responses = await entity_service.search(
            entity_class=entity_name,
            condition=builder.build(),
            entity_version=entity_version,
        )

        if not responses:
            logger.debug(f"No session found for session_id={session_id}")
            return None

        # Get the first matching session
        response = responses[0]

        # Extract session data - handle both Pydantic models and dicts
        if hasattr(response.data, "model_dump"):
            session_data = response.data.model_dump()
        elif isinstance(response.data, dict):
            # Check if this is a nested Cyoda response structure
            if "type" in response.data and response.data.get("type") == "ENTITY":
                # Extract the actual entity data from nested structure
                session_data = response.data.get("data", {})
            else:
                session_data = response.data
        else:
            logger.error(f"Unexpected data type: {type(response.data)}")
            return None

        logger.debug(
            f"Found session: technical_id={response.metadata.id}, data={session_data}"
        )

        adk_session = AdkSession(**session_data)
        adk_session.technical_id = response.metadata.id
        return adk_session

    except Exception as e:
        logger.error(f"Error finding session {session_id}: {e}", exc_info=True)
        return None


def filter_session_events(
    session: Session, config: Optional[GetSessionConfig]
) -> Session:
    """Filter session events based on config.

    Args:
        session: Session object.
        config: Optional configuration for filtering.

    Returns:
        Session with filtered events.
    """
    if config:
        if config.num_recent_events:
            session.events = session.events[-config.num_recent_events :]
        if config.after_timestamp:
            session.events = [
                event
                for event in session.events
                if event.timestamp > config.after_timestamp
            ]
    return session


async def try_fast_lookup(
    entity_service: EntityService,
    session_id: str,
    to_adk_session_fn,
    entity_name: str = "AdkSession",
    entity_version: str = "1",
) -> Optional[Session]:
    """Try fast lookup by technical_id.

    Args:
        entity_service: Cyoda entity service
        session_id: Session ID (assumed to be technical_id).
        to_adk_session_fn: Function to convert AdkSession to Session
        entity_name: Cyoda entity class name
        entity_version: Cyoda entity version

    Returns:
        Session object or None if not found.
    """
    logger.debug(
        f"Session ID looks like UUID, trying fast lookup by technical_id: {session_id}"
    )
    try:
        adk_session = await fetch_session_from_cyoda(
            entity_service, session_id, entity_name, entity_version
        )
        if adk_session:
            logger.info(
                f"✅ FAST LOOKUP: Session found by technical_id: {session_id}, "
                f"events_count={len(adk_session.events)}"
            )
            return to_adk_session_fn(adk_session)
    except Exception as e:
        logger.debug(
            f"Fast lookup by technical_id failed (not an AdkSession): {e}, "
            f"falling back to search by session_id field"
        )
    return None


async def fallback_search(
    entity_service: EntityService,
    app_name: str,
    user_id: str,
    session_id: str,
    to_adk_session_fn,
    entity_name: str = "AdkSession",
    entity_version: str = "1",
) -> Optional[Session]:
    """Search session by session_id field.

    Args:
        entity_service: Cyoda entity service
        app_name: Application name.
        user_id: User ID.
        session_id: Session ID to search for.
        to_adk_session_fn: Function to convert AdkSession to Session
        entity_name: Cyoda entity class name
        entity_version: Cyoda entity version

    Returns:
        Session object or None if not found.
    """
    logger.debug(f"🔍 SEARCH: Looking up session by session_id field: {session_id}")
    adk_session = await find_session_entity(
        entity_service, app_name, user_id, session_id, entity_name, entity_version
    )
    if not adk_session:
        logger.warning(
            f"Session not found: app_name={app_name}, user_id={user_id}, session_id={session_id}"
        )
        return None

    logger.info(
        f"Session found via search: {session_id}, technical_id={adk_session.technical_id}, "
        f"events_count={len(adk_session.events)}"
    )
    return to_adk_session_fn(adk_session)


async def fallback_search_with_retry(
    entity_service: EntityService,
    app_name: str,
    user_id: str,
    session_id: str,
    to_adk_session_fn,
    entity_name: str = "AdkSession",
    entity_version: str = "1",
    max_retries: int = 3,
    retry_delay: float = 0.5,
) -> Optional[Session]:
    """Search session by session_id field with retry logic for eventual consistency.

    This function retries the search operation to handle cases where a session
    was just created but isn't immediately searchable due to eventual consistency
    in the Cyoda database or search indexes.

    Args:
        entity_service: Cyoda entity service
        app_name: Application name.
        user_id: User ID.
        session_id: Session ID to search for.
        to_adk_session_fn: Function to convert AdkSession to Session
        entity_name: Cyoda entity class name
        entity_version: Cyoda entity version
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Delay in seconds between retries (default: 0.5)

    Returns:
        Session object or None if not found after all retries.
    """
    for attempt in range(max_retries):
        session = await fallback_search(
            entity_service,
            app_name,
            user_id,
            session_id,
            to_adk_session_fn,
            entity_name,
            entity_version,
        )

        if session:
            if attempt > 0:
                logger.info(
                    f"✅ Session found after {attempt + 1} attempts "
                    f"(eventual consistency delay)"
                )
            return session

        if attempt < max_retries - 1:
            logger.debug(
                f"Session not found on attempt {attempt + 1}/{max_retries}, "
                f"retrying in {retry_delay}s (eventual consistency)"
            )
            await asyncio.sleep(retry_delay)

    logger.warning(
        f"❌ Session not found after {max_retries} attempts: "
        f"app_name={app_name}, user_id={user_id}, session_id={session_id}"
    )
    return None
