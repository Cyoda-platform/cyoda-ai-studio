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

Key components:
- _pending_events: Queued events waiting to be persisted
- _pending_state_deltas: Merged state changes waiting to be persisted
- _session_cache: In-memory cache of session entities
- flush_session(): Persists all pending data in a single update
"""

from __future__ import annotations

import asyncio
import copy
import logging
import time
import uuid
from dataclasses import dataclass, field
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
    SearchOperator,
)
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
        """
        Create a new session in Cyoda.

        Args:
            app_name: Application name
            user_id: User ID
            state: Initial session state
            session_id: Optional session ID (generated if not provided)

        Returns:
            Created Session object
        """
        session_id = (
            session_id.strip()
            if session_id and session_id.strip()
            else str(uuid.uuid4())
        )

        logger.info(
            f"Creating session: app_name={app_name}, user_id={user_id}, session_id={session_id}"
        )

        # Skip the "already exists" check for now - it's causing issues with search
        # The Cyoda save operation will fail if the entity truly already exists
        # existing = await self._find_session_entity(app_name, user_id, session_id)
        # if existing:
        #     logger.warning(f"Session {session_id} already exists, raising error")
        #     raise ValueError(f"Session {session_id} already exists")

        adk_session = AdkSession.from_adk_session(
            session_id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state or {},
            events=[],
        )

        logger.debug(f"Saving AdkSession entity: {adk_session.model_dump()}")
        response = await self.entity_service.save(
            entity=adk_session.model_dump(),
            entity_class=self.ENTITY_NAME,
            entity_version=self.ENTITY_VERSION,
        )

        adk_session.technical_id = response.metadata.id
        logger.info(
            f"Session saved with technical_id={response.metadata.id}, state={response.metadata.state}"
        )

        # Activate the session (transition from initial_state to active)
        try:
            logger.debug(f"Activating session {session_id} via 'activate' transition")
            await self.entity_service.execute_transition(
                entity_id=response.metadata.id,
                transition="activate",
                entity_class=self.ENTITY_NAME,
                entity_version=self.ENTITY_VERSION,
            )
            logger.info(f"Session {session_id} activated successfully")
        except Exception as e:
            logger.error(f"Failed to activate session {session_id}: {e}", exc_info=True)

        session = self._to_adk_session(adk_session)
        # Store technical_id in session state for fast retrieval
        session.state["__cyoda_technical_id__"] = response.metadata.id
        logger.info(
            f"Session created successfully: {session.id}, technical_id={response.metadata.id}"
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
        """
        Get a session from Cyoda.

        OPTIMIZATION: If session_id looks like a UUID AND is an AdkSession technical_id,
        tries fast lookup first. Otherwise falls back to search by session_id field.

        Args:
            app_name: Application name
            user_id: User ID
            session_id: Session ID (can be conversation_id OR technical_id)
            config: Optional configuration for filtering events

        Returns:
            Session object or None if not found
        """
        logger.debug(
            f"Getting session: app_name={app_name}, user_id={user_id}, session_id={session_id}"
        )

        # OPTIMIZATION: If session_id looks like a UUID, try fast lookup by technical_id first
        # This handles the case where session_id IS the technical_id (common in our flow)
        # We check if it's actually an AdkSession by verifying required fields exist
        if len(session_id) == 36 and session_id.count("-") == 4:
            logger.debug(
                f"Session ID looks like UUID, trying fast lookup by technical_id: {session_id}"
            )
            try:
                adk_session = await self.get_session_by_technical_id(session_id)
                if adk_session:
                    logger.info(
                        f"✅ FAST LOOKUP: Session found by technical_id: {session_id}, "
                        f"events_count={len(adk_session.events)}"
                    )
                    session = self._to_adk_session(adk_session)
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
            except Exception as e:
                # Fast lookup failed (entity is not an AdkSession), fall back to search
                logger.debug(
                    f"Fast lookup by technical_id failed (not an AdkSession): {e}, "
                    f"falling back to search by session_id field"
                )

        # Fallback: Search by session_id field (slower ~1 second)
        logger.debug(f"🔍 SEARCH: Looking up session by session_id field: {session_id}")
        adk_session = await self._find_session_entity(app_name, user_id, session_id)
        if not adk_session:
            logger.warning(
                f"Session not found: app_name={app_name}, user_id={user_id}, session_id={session_id}"
            )
            return None

        logger.info(
            f"Session found via search: {session_id}, technical_id={adk_session.technical_id}, "
            f"events_count={len(adk_session.events)}"
        )
        session = self._to_adk_session(adk_session)

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

    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        """
        List sessions from Cyoda.

        Args:
            app_name: Application name
            user_id: Optional user ID filter

        Returns:
            ListSessionsResponse with sessions (without events)
        """
        builder = SearchConditionRequest.builder()
        builder.add_condition("app_name", SearchOperator.EQUALS, app_name)
        if user_id:
            builder.add_condition("user_id", SearchOperator.EQUALS, user_id)

        responses = await self.entity_service.search(
            entity_class=self.ENTITY_NAME,
            condition=builder.build(),
            entity_version=self.ENTITY_VERSION,
        )

        sessions = []
        for response in responses:
            adk_session = AdkSession(**response.data.model_dump())
            session = self._to_adk_session(adk_session)
            session.events = []
            sessions.append(session)

        return ListSessionsResponse(sessions=sessions)

    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        """
        Delete a session from Cyoda.

        Args:
            app_name: Application name
            user_id: User ID
            session_id: Session ID
        """
        adk_session = await self._find_session_entity(app_name, user_id, session_id)
        if not adk_session or not adk_session.technical_id:
            return

        await self.entity_service.delete_by_id(
            entity_id=adk_session.technical_id,
            entity_class=self.ENTITY_NAME,
            entity_version=self.ENTITY_VERSION,
        )

    async def append_event(self, session: Session, event: Event) -> Event:
        """
        Append an event to a session using write-behind caching.

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
        event_data = self._serialize_event(event)
        await self._queue_event(technical_id, event_data, event)

        return event

    async def _queue_event(
        self, technical_id: str, event_data: dict[str, Any], event: Event
    ) -> None:
        """
        Queue an event for batch persistence.

        Args:
            technical_id: Session technical ID
            event_data: Serialized event data
            event: Original event object
        """
        # Get or create cached session
        if technical_id not in self._session_cache:
            adk_session = await self._fetch_session_from_cyoda(technical_id)
            if not adk_session:
                logger.warning(f"Session {technical_id} not found, cannot queue event")
                return
            self._session_cache[technical_id] = CachedSession(
                session=adk_session,
                cached_at=time.time(),
            )

        cached = self._session_cache[technical_id]
        cached.pending_events.append(event_data)
        cached.is_dirty = True

        # Merge state delta if present
        if event.actions and event.actions.state_delta:
            cached.pending_state_delta.update(event.actions.state_delta)

        logger.debug(
            f"📝 Queued event for session {technical_id}. "
            f"Pending: {len(cached.pending_events)} events"
        )

    async def flush_session(self, technical_id: str) -> bool:
        """
        Persist all pending events for a session in a single batch update.

        This is the key optimization - instead of N HTTP calls (one per event),
        we do a single fetch + single update.

        Args:
            technical_id: Session technical ID to flush

        Returns:
            True if flush was successful, False otherwise
        """
        async with self._flush_lock:
            if technical_id not in self._session_cache:
                logger.debug(f"No cached session for {technical_id}, nothing to flush")
                return True

            cached = self._session_cache[technical_id]
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
                adk_session = await self._fetch_session_from_cyoda(technical_id)
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
                await self._persist_session_with_retry(adk_session)

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

    async def _persist_session_with_retry(self, adk_session: AdkSession) -> None:
        """
        Persist session with retry logic for version conflicts.

        Args:
            adk_session: Session to persist
        """
        if not adk_session.technical_id:
            raise ValueError("Cannot persist session without technical_id")

        max_retries = 5
        retry_delay = 0.1
        entity_id = adk_session.technical_id

        for attempt in range(max_retries):
            try:
                await self.entity_service.update(
                    entity_id=entity_id,
                    entity=adk_session.model_dump(),
                    entity_class=self.ENTITY_NAME,
                    entity_version=self.ENTITY_VERSION,
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

    async def _fetch_session_from_cyoda(
        self, technical_id: str
    ) -> Optional[AdkSession]:
        """
        Fetch session directly from Cyoda (bypasses cache).

        Args:
            technical_id: Session technical ID

        Returns:
            AdkSession or None
        """
        try:
            response = await self.entity_service.get_by_id(
                entity_id=technical_id,
                entity_class=self.ENTITY_NAME,
                entity_version=self.ENTITY_VERSION,
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

    def get_pending_event_count(self, technical_id: str) -> int:
        """
        Get the number of pending events for a session.

        Args:
            technical_id: Session technical ID

        Returns:
            Number of pending events
        """
        if technical_id not in self._session_cache:
            return 0
        return len(self._session_cache[technical_id].pending_events)

    def get_pending_state_delta(self, technical_id: str) -> dict[str, Any]:
        """
        Get the pending state delta for a session.

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
        """
        Clear session cache.

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
        """
        Get a session entity by its Cyoda technical ID.

        Uses in-memory cache when available to avoid HTTP calls.

        Args:
            technical_id: Cyoda technical UUID of the AdkSession entity
            use_cache: Whether to use cached session (default True)

        Returns:
            AdkSession entity or None
        """
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
        adk_session = await self._fetch_session_from_cyoda(technical_id)
        if adk_session and use_cache:
            self._session_cache[technical_id] = CachedSession(
                session=adk_session,
                cached_at=time.time(),
            )

        return adk_session

    async def _find_session_entity(
        self, app_name: str, user_id: str, session_id: str
    ) -> Optional[AdkSession]:
        """
        Find a session entity in Cyoda using search.

        NOTE: This is slower than get_session_by_technical_id().
        Prefer storing and using the technical_id when possible.

        Args:
            app_name: Application name
            user_id: User ID
            session_id: Session ID

        Returns:
            AdkSession entity or None
        """
        logger.debug(
            f"Finding session by search: app_name={app_name}, user_id={user_id}, session_id={session_id}"
        )

        try:
            # Use search with session_id filter
            builder = SearchConditionRequest.builder()
            builder.add_condition("session_id", SearchOperator.EQUALS, session_id)

            responses = await self.entity_service.search(
                entity_class=self.ENTITY_NAME,
                condition=builder.build(),
                entity_version=self.ENTITY_VERSION,
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

    def _to_adk_session(self, adk_session: AdkSession) -> Session:
        """
        Convert AdkSession entity to ADK Session object.

        Args:
            adk_session: AdkSession entity

        Returns:
            ADK Session object
        """
        events = [
            self._deserialize_event(event_data) for event_data in adk_session.events
        ]

        state = copy.deepcopy(adk_session.session_state)
        # Store technical_id in state for fast retrieval
        if adk_session.technical_id:
            state["__cyoda_technical_id__"] = adk_session.technical_id

        return Session(
            id=adk_session.session_id,
            app_name=adk_session.app_name,
            user_id=adk_session.user_id,
            state=state,
            events=events,
            last_update_time=adk_session.last_update_time,
        )

    def _serialize_event(self, event: Event) -> dict[str, Any]:
        """
        Serialize an Event object to dictionary.

        Args:
            event: Event object

        Returns:
            Serialized event dictionary
        """
        # Exclude None values to avoid Pydantic validation errors on deserialization
        # Use by_alias=True to serialize with camelCase field names (Event uses alias_generator=to_camel)
        # The Event model has extra='forbid' and doesn't accept None for optional fields
        # Use mode='json' to properly serialize bytes to base64 strings (Event has ser_json_bytes='base64')
        return event.model_dump(exclude_none=True, by_alias=True, mode='json')

    def _filter_none_values(self, data: Any) -> Any:
        """
        Recursively filter out None values from dictionaries.

        Args:
            data: Data to filter (dict, list, or other)

        Returns:
            Filtered data with None values removed
        """
        if isinstance(data, dict):
            return {
                k: self._filter_none_values(v)
                for k, v in data.items()
                if v is not None
            }
        elif isinstance(data, list):
            return [self._filter_none_values(item) for item in data]
        else:
            return data

    def _deserialize_event(self, event_data: dict[str, Any]) -> Event:
        """
        Deserialize an event dictionary to Event object.

        Args:
            event_data: Serialized event dictionary

        Returns:
            Event object
        """
        # Filter out None values recursively to avoid Pydantic validation errors
        filtered_data = self._filter_none_values(event_data)

        # Filter to only include fields that are actually in the Event model
        # This handles backward compatibility with old serialized events that may have extra fields
        valid_fields = set(Event.model_fields.keys())

        # Also include camelCase aliases for fields (Event uses alias_generator=to_camel)
        # Convert field names to camelCase
        def to_camel_case(snake_str: str) -> str:
            components = snake_str.split('_')
            return components[0] + ''.join(x.title() for x in components[1:])

        camel_aliases = {to_camel_case(f) for f in valid_fields if '_' in f}
        all_valid_fields = valid_fields | camel_aliases

        # Filter the data to only include valid fields
        clean_data = {k: v for k, v in filtered_data.items() if k in all_valid_fields}

        try:
            return Event(**clean_data)
        except Exception as e:
            logger.error(f"Failed to deserialize event: {e}")
            logger.error(f"Event data keys: {list(clean_data.keys())}")
            logger.error(f"Valid Event fields: {valid_fields}")
            raise
