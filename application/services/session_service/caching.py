"""Write-behind caching and event persistence for CyodaSessionService.

Implements batched event persistence to reduce HTTP calls from ~100 per message to ~2.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from google.adk.events.event import Event

from application.entity.adk_session import AdkSession
from common.service.entity_service import EntityService
from common.service.service import EntityServiceError

logger = logging.getLogger(__name__)


@dataclass
class CachedSession:
    """Cached session with metadata for write-behind caching."""

    session: AdkSession
    cached_at: float
    pending_events: list[dict[str, Any]] = field(default_factory=list)
    pending_state_delta: dict[str, Any] = field(default_factory=dict)
    is_dirty: bool = False


async def queue_event(
    technical_id: str,
    event_data: dict[str, Any],
    event: Event,
    session_cache: dict[str, CachedSession],
    entity_service: EntityService,
    entity_name: str = "AdkSession",
    entity_version: str = "1",
) -> None:
    """Queue an event for batch persistence.

    Args:
        technical_id: Session technical ID
        event_data: Serialized event data
        event: Original event object
        session_cache: Session cache dictionary
        entity_service: Cyoda entity service
        entity_name: Cyoda entity class name
        entity_version: Cyoda entity version
    """
    # Get or create cached session
    if technical_id not in session_cache:
        from .retrieval import fetch_session_from_cyoda

        adk_session = await fetch_session_from_cyoda(
            entity_service, technical_id, entity_name, entity_version
        )
        if not adk_session:
            logger.warning(f"Session {technical_id} not found, cannot queue event")
            return
        session_cache[technical_id] = CachedSession(
            session=adk_session,
            cached_at=time.time(),
        )

    cached = session_cache[technical_id]
    cached.pending_events.append(event_data)
    cached.is_dirty = True

    # Merge state delta if present
    if event.actions and event.actions.state_delta:
        cached.pending_state_delta.update(event.actions.state_delta)

    logger.debug(
        f"📝 Queued event for session {technical_id}. "
        f"Pending: {len(cached.pending_events)} events"
    )


async def persist_session_with_retry(
    adk_session: AdkSession,
    entity_service: EntityService,
    entity_name: str = "AdkSession",
    entity_version: str = "1",
    max_retries: int = 5,
) -> None:
    """Persist session with retry logic for version conflicts.

    Args:
        adk_session: Session to persist
        entity_service: Cyoda entity service
        entity_name: Cyoda entity class name
        entity_version: Cyoda entity version
        max_retries: Maximum number of retry attempts
    """
    if not adk_session.technical_id:
        raise ValueError("Cannot persist session without technical_id")

    retry_delay = 0.1
    entity_id = adk_session.technical_id

    for attempt in range(max_retries):
        try:
            await entity_service.update(
                entity_id=entity_id,
                entity=adk_session.model_dump(),
                entity_class=entity_name,
                entity_version=entity_version,
            )
            if attempt > 0:
                logger.info(
                    f"Successfully persisted session after {attempt + 1} attempts"
                )
            return
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
                logger.warning(
                    f"Version conflict (attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise


async def flush_session(
    technical_id: str,
    session_cache: dict[str, CachedSession],
    entity_service: EntityService,
    flush_lock: asyncio.Lock,
    entity_name: str = "AdkSession",
    entity_version: str = "1",
) -> bool:
    """Persist all pending events for a session in a single batch update.

    This is the key optimization - instead of N HTTP calls (one per event),
    we do a single fetch + single update.

    Args:
        technical_id: Session technical ID to flush
        session_cache: Session cache dictionary
        entity_service: Cyoda entity service
        flush_lock: Asyncio lock for thread-safe flushing
        entity_name: Cyoda entity class name
        entity_version: Cyoda entity version

    Returns:
        True if flush was successful, False otherwise
    """
    async with flush_lock:
        if technical_id not in session_cache:
            logger.debug(f"No cached session for {technical_id}, nothing to flush")
            return True

        cached = session_cache[technical_id]
        if not cached.is_dirty:
            logger.debug(f"Session {technical_id} is clean, nothing to flush")
            return True

        pending_count = len(cached.pending_events)
        logger.info(
            f"🔄 Flushing session {technical_id}: "
            f"{pending_count} pending events, "
            f"{len(cached.pending_state_delta)} state changes"
        )

        try:
            # Fetch fresh session to avoid version conflicts
            from .retrieval import fetch_session_from_cyoda

            adk_session = await fetch_session_from_cyoda(
                entity_service, technical_id, entity_name, entity_version
            )
            if not adk_session:
                logger.error(f"Session {technical_id} not found during flush")
                return False

            # Apply all pending events
            for event_data in cached.pending_events:
                adk_session.add_event(event_data)

            # Apply merged state delta
            if cached.pending_state_delta:
                adk_session.update_state(cached.pending_state_delta)

            # Single persist with retry logic
            await persist_session_with_retry(
                adk_session, entity_service, entity_name, entity_version
            )

            # Clear pending data
            cached.pending_events.clear()
            cached.pending_state_delta.clear()
            cached.is_dirty = False
            cached.session = adk_session
            cached.cached_at = time.time()

            logger.info(
                f"✅ Flushed session {technical_id}: {pending_count} events persisted"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to flush session {technical_id}: {e}")
            return False
