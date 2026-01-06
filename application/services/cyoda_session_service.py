"""
Cyoda-based Session Service for Google ADK.

Implements BaseSessionService using Cyoda entities for persistent storage.
Sessions survive application restarts and can be shared across instances.

PERFORMANCE OPTIMIZATION: Write-Behind Caching
----------------------------------------------
This service implements write-behind caching to reduce HTTP calls during
agent execution. Instead of persisting every event immediately (which caused
~100 HTTP calls per user message), events are accumulated in memory and
persisted in a single batch at the end of the stream.

Internal organization:
- session_service/initialization.py: Session creation and activation
- session_service/retrieval.py: Session lookup and fetching
- session_service/caching.py: Write-behind caching and batch persistence
- session_service/utilities.py: Serialization and conversion utilities
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from google.adk.events.event import Event
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session

from application.entity.adk_session import AdkSession
from common.service.entity_service import (
    EntityService,
    SearchConditionRequest,
)
from common.search import CyodaOperator

# Re-export from session_service modules for backward compatibility
from .session_service import (
    save_session_entity,
    activate_session,
    normalize_session_id,
    is_uuid_format,
    fetch_session_from_cyoda,
    find_session_entity,
    filter_session_events,
    try_fast_lookup,
    fallback_search,
    fallback_search_with_retry,
    CachedSession,
    queue_event,
    persist_session_with_retry,
    flush_session,
    to_adk_session,
    serialize_event,
    filter_none_values,
    deserialize_event,
)

logger = logging.getLogger(__name__)


class CyodaSessionService(BaseSessionService):
    """
    Cyoda-based implementation of ADK SessionService with write-behind caching.

    Stores sessions as Cyoda entities, providing:
    - Persistent storage across application restarts
    - Scalable multi-instance support
    - Full ADK session compatibility
    - Write-behind caching for reduced latency (events batched, single persist)
    """

    ENTITY_NAME = "AdkSession"
    ENTITY_VERSION = "1"
    CACHE_TTL_SECONDS = 300  # 5 minutes cache TTL

    def __init__(self, entity_service: EntityService):
        """
        Initialize Cyoda session service with write-behind caching.

        Args:
            entity_service: Cyoda entity service for persistence
        """
        self.entity_service = entity_service
        self._session_cache: dict[str, CachedSession] = {}
        self._flush_lock = asyncio.Lock()
        logger.info("CyodaSessionService initialized with write-behind caching")

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Create a new session in Cyoda.

        Args:
            app_name: Application name
            user_id: User ID
            state: Initial session state
            session_id: Optional session ID (generated if not provided)

        Returns:
            Created Session object
        """
        session_id = normalize_session_id(session_id)

        logger.info(
            f"Creating session: app_name={app_name}, user_id={user_id}, session_id={session_id}"
        )

        adk_session, technical_id = await save_session_entity(
            self.entity_service, session_id, app_name, user_id, state or {}, self.ENTITY_NAME, self.ENTITY_VERSION
        )

        await activate_session(self.entity_service, session_id, technical_id, self.ENTITY_NAME, self.ENTITY_VERSION)

        session = to_adk_session(adk_session, deserialize_event)
        session.state["__cyoda_technical_id__"] = technical_id
        logger.info(
            f"Session created successfully: {session.id}, technical_id={technical_id}"
        )

        return session

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        """Get a session from Cyoda with optimized lookup.

        Tries fast lookup by technical_id if session_id looks like UUID,
        otherwise falls back to search by session_id field.

        Args:
            app_name: Application name.
            user_id: User ID.
            session_id: Session ID (can be conversation_id OR technical_id).
            config: Optional configuration for filtering events.

        Returns:
            Session object or None if not found.
        """
        logger.debug(
            f"Getting session: app_name={app_name}, user_id={user_id}, session_id={session_id}"
        )

        # Try fast lookup if UUID format
        if is_uuid_format(session_id):
            session = await try_fast_lookup(
                self.entity_service, session_id,
                lambda adk: to_adk_session(adk, deserialize_event),
                self.ENTITY_NAME, self.ENTITY_VERSION
            )
            if session:
                return filter_session_events(session, config)

        # Fallback to search with retry logic for eventual consistency
        session = await fallback_search_with_retry(
            self.entity_service, app_name, user_id, session_id,
            lambda adk: to_adk_session(adk, deserialize_event),
            self.ENTITY_NAME, self.ENTITY_VERSION
        )
        if not session:
            return None

        return filter_session_events(session, config)

    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        """List sessions from Cyoda.

        Args:
            app_name: Application name
            user_id: Optional user ID filter

        Returns:
            ListSessionsResponse with sessions (without events)
        """
        builder = SearchConditionRequest.builder()
        builder.add_condition("app_name", CyodaOperator.EQUALS, app_name)
        if user_id:
            builder.add_condition("user_id", CyodaOperator.EQUALS, user_id)

        responses = await self.entity_service.search(
            entity_class=self.ENTITY_NAME,
            condition=builder.build(),
            entity_version=self.ENTITY_VERSION,
        )

        sessions = []
        for response in responses:
            adk_session = AdkSession(**response.data.model_dump())
            session = to_adk_session(adk_session, deserialize_event)
            session.events = []
            sessions.append(session)

        return ListSessionsResponse(sessions=sessions)

    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        """Delete a session from Cyoda.

        Args:
            app_name: Application name
            user_id: User ID
            session_id: Session ID
        """
        adk_session = await find_session_entity(
            self.entity_service, app_name, user_id, session_id, self.ENTITY_NAME, self.ENTITY_VERSION
        )
        if not adk_session or not adk_session.technical_id:
            return

        await self.entity_service.delete_by_id(
            entity_id=adk_session.technical_id,
            entity_class=self.ENTITY_NAME,
            entity_version=self.ENTITY_VERSION,
        )

    async def append_event(self, session: Session, event: Event) -> Event:
        """Append an event to a session using write-behind caching.

        Events are accumulated in memory and persisted in batch via flush_session().
        This reduces HTTP calls from ~100 per message to ~2 (one fetch, one update).

        Args:
            session: Session object
            event: Event to append

        Returns:
            The appended event
        """
        if event.partial:
            return event

        # Update in-memory ADK session (required by base class)
        await super().append_event(session=session, event=event)
        session.last_update_time = event.timestamp

        # Get technical_id for cache lookup
        technical_id = session.state.get("__cyoda_technical_id__")
        if not technical_id:
            logger.warning(
                f"Session {session.id} has no technical_id in state, cannot queue event."
            )
            return event

        # Queue event for batch persistence (write-behind)
        event_data = serialize_event(event)
        await queue_event(
            technical_id, event_data, event, self._session_cache,
            self.entity_service, self.ENTITY_NAME, self.ENTITY_VERSION
        )

        return event

    async def flush_session(self, technical_id: str) -> bool:
        """Persist all pending events for a session in a single batch update.

        This is the key optimization - instead of N HTTP calls (one per event),
        we do a single fetch + single update.

        Args:
            technical_id: Session technical ID to flush

        Returns:
            True if flush was successful, False otherwise
        """
        return await flush_session(
            technical_id, self._session_cache, self.entity_service,
            self._flush_lock, self.ENTITY_NAME, self.ENTITY_VERSION
        )

    def get_pending_event_count(self, technical_id: str) -> int:
        """Get the number of pending events for a session.

        Args:
            technical_id: Session technical ID

        Returns:
            Number of pending events
        """
        if technical_id not in self._session_cache:
            return 0
        return len(self._session_cache[technical_id].pending_events)

    def get_pending_state_delta(self, technical_id: str) -> dict[str, Any]:
        """Get the pending state delta for a session.

        This returns state changes that have been queued but not yet persisted.
        Useful for getting hooks and other state that was set during the stream.

        Args:
            technical_id: Session technical ID

        Returns:
            Dictionary of pending state changes
        """
        if technical_id not in self._session_cache:
            return {}
        return dict(self._session_cache[technical_id].pending_state_delta)

    def clear_cache(self, technical_id: Optional[str] = None) -> None:
        """Clear session cache.

        Args:
            technical_id: Specific session to clear, or None to clear all
        """
        if technical_id:
            self._session_cache.pop(technical_id, None)
        else:
            self._session_cache.clear()
        logger.debug(f"Cleared session cache: {technical_id or 'all'}")

    async def get_session_by_technical_id(
        self, technical_id: str, use_cache: bool = True
    ) -> Optional[AdkSession]:
        """Get a session entity by its Cyoda technical ID.

        Uses in-memory cache when available to avoid HTTP calls.

        Args:
            technical_id: Cyoda technical UUID of the AdkSession entity
            use_cache: Whether to use cached session (default True)

        Returns:
            AdkSession entity or None
        """
        import time

        # Check cache first
        if use_cache and technical_id in self._session_cache:
            cached = self._session_cache[technical_id]
            cache_age = time.time() - cached.cached_at
            if cache_age < self.CACHE_TTL_SECONDS:
                logger.debug(
                    f"Cache hit for session {technical_id} (age: {cache_age:.1f}s)"
                )
                return cached.session

        # Fetch from Cyoda
        adk_session = await fetch_session_from_cyoda(
            self.entity_service, technical_id, self.ENTITY_NAME, self.ENTITY_VERSION
        )
        if adk_session and use_cache:
            self._session_cache[technical_id] = CachedSession(
                session=adk_session,
                cached_at=time.time(),
            )

        return adk_session


__all__ = [
    # Main class
    "CyodaSessionService",
    # Data class
    "CachedSession",
    # Re-exported for backward compatibility
    "save_session_entity",
    "activate_session",
    "normalize_session_id",
    "is_uuid_format",
    "fetch_session_from_cyoda",
    "find_session_entity",
    "filter_session_events",
    "try_fast_lookup",
    "fallback_search",
    "fallback_search_with_retry",
    "queue_event",
    "persist_session_with_retry",
    "flush_session",
    "to_adk_session",
    "serialize_event",
    "filter_none_values",
    "deserialize_event",
]
