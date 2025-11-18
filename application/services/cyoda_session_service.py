"""
Cyoda-based Session Service for Google ADK.

Implements BaseSessionService using Cyoda entities for persistent storage.
Sessions survive application restarts and can be shared across instances.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import time
import uuid
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
    LogicalOperator,
    SearchConditionRequest,
    SearchOperator,
)
from common.service.service import EntityServiceError

logger = logging.getLogger(__name__)


class CyodaSessionService(BaseSessionService):
    """
    Cyoda-based implementation of ADK SessionService.

    Stores sessions as Cyoda entities, providing:
    - Persistent storage across application restarts
    - Scalable multi-instance support
    - Full ADK session compatibility
    """

    ENTITY_NAME = "AdkSession"
    ENTITY_VERSION = "1"

    def __init__(self, entity_service: EntityService):
        """
        Initialize Cyoda session service.

        Args:
            entity_service: Cyoda entity service for persistence
        """
        self.entity_service = entity_service
        logger.info("CyodaSessionService initialized")

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
        Append an event to a session in Cyoda.

        Args:
            session: Session object
            event: Event to append

        Returns:
            The appended event
        """
        if event.partial:
            return event

        await super().append_event(session=session, event=event)
        session.last_update_time = event.timestamp

        # Get technical_id from session state (FAST - no search needed!)
        technical_id = session.state.get("__cyoda_technical_id__")
        if not technical_id:
            logger.warning(
                f"Session {session.id} has no technical_id in state, cannot append event. "
                f"This should not happen - session was not properly initialized."
            )
            return event

        # Get session entity by technical_id (FAST - direct lookup, no search)
        adk_session = await self.get_session_by_technical_id(technical_id)
        if not adk_session or not adk_session.technical_id:
            logger.warning(
                f"Session {session.id} with technical_id={technical_id} not found in Cyoda, cannot append event"
            )
            return event

        event_data = self._serialize_event(event)
        adk_session.add_event(event_data)

        if event.actions and event.actions.state_delta:
            adk_session.update_state(event.actions.state_delta)

        # Retry logic for version conflicts
        max_retries = 5
        retry_delay = 0.1  # Start with 100ms

        for attempt in range(max_retries):
            try:
                await self.entity_service.update(
                    entity_id=adk_session.technical_id,
                    entity=adk_session.model_dump(),
                    entity_class=self.ENTITY_NAME,
                    entity_version=self.ENTITY_VERSION,
                )
                # Success - break out of retry loop
                if attempt > 0:
                    logger.info(
                        f"Successfully updated session {session.id} after {attempt + 1} attempts"
                    )
                break
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
                        f"Version conflict updating session {session.id} "
                        f"(attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {retry_delay}s... Error: {e}"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

                    # Re-fetch the session to get the latest version (using technical_id - FAST!)
                    adk_session = await self.get_session_by_technical_id(technical_id)
                    if not adk_session or not adk_session.technical_id:
                        logger.error(
                            f"Session {session.id} with technical_id={technical_id} disappeared during retry"
                        )
                        raise

                    # Re-apply the event and state delta to the fresh session
                    adk_session.add_event(event_data)
                    if event.actions and event.actions.state_delta:
                        adk_session.update_state(event.actions.state_delta)
                else:
                    # Not a version conflict or max retries reached
                    logger.error(
                        f"Failed to update session {session.id} after {attempt + 1} attempts: {e}"
                    )
                    raise

        return event

    async def get_session_by_technical_id(
        self, technical_id: str
    ) -> Optional[AdkSession]:
        """
        Get a session entity by its Cyoda technical ID (fastest method).

        Args:
            technical_id: Cyoda technical UUID of the AdkSession entity

        Returns:
            AdkSession entity or None
        """
        logger.debug(f"Getting session by technical_id: {technical_id}")

        try:
            response = await self.entity_service.get_by_id(
                entity_id=technical_id,
                entity_class=self.ENTITY_NAME,
                entity_version=self.ENTITY_VERSION,
            )

            if not response:
                logger.debug(f"No session found for technical_id={technical_id}")
                return None

            if hasattr(response.data, "model_dump"):
                session_data = response.data.model_dump()
            elif isinstance(response.data, dict):
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
            logger.debug(
                f"Could not load entity {technical_id} as AdkSession: {e}"
            )
            return None

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
        return event.model_dump(exclude_none=True, by_alias=True)

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
