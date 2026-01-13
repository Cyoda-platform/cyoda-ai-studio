"""
ADK Session Entity for persistent storage of Google ADK sessions in Cyoda.

This entity stores complete ADK session data including events, state, and metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class AdkSession(CyodaEntity):
    """
    ADK Session entity for persistent storage of Google ADK sessions.

    Stores complete session data including:
    - Session metadata (app_name, user_id, session_id)
    - Session state (key-value pairs)
    - Events (conversation history, tool calls, responses)
    - Timestamps for tracking
    """

    ENTITY_NAME: ClassVar[str] = "AdkSession"
    ENTITY_VERSION: ClassVar[int] = 1

    session_id: str = Field(..., description="Unique ADK session identifier")

    app_name: str = Field(..., description="Name of the ADK application")

    user_id: str = Field(..., description="User ID who owns this session")

    session_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Session state key-value pairs",
    )

    events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of serialized Event objects (messages, tool calls, etc.)",
    )

    last_update_time: float = Field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp(),
        description="Last update timestamp (Unix timestamp)",
    )

    create_time: float = Field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp(),
        description="Session creation timestamp (Unix timestamp)",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

    def add_event(self, event_data: dict[str, Any]) -> None:
        """
        Add an event to the session.

        Args:
            event_data: Serialized event dictionary
        """
        self.events.append(event_data)
        self.last_update_time = datetime.now(timezone.utc).timestamp()
        self.update_timestamp()

    def update_state(self, state_updates: dict[str, Any]) -> None:
        """
        Update session state.

        Args:
            state_updates: Dictionary of state updates to merge
        """
        self.session_state.update(state_updates)
        self.last_update_time = datetime.now(timezone.utc).timestamp()
        self.update_timestamp()

    def get_recent_events(self, num_events: int) -> list[dict[str, Any]]:
        """
        Get the most recent N events.

        Args:
            num_events: Number of recent events to return

        Returns:
            List of recent event dictionaries
        """
        return self.events[-num_events:] if num_events > 0 else self.events

    def get_events_after_timestamp(self, timestamp: float) -> list[dict[str, Any]]:
        """
        Get events after a specific timestamp.

        Args:
            timestamp: Unix timestamp to filter events

        Returns:
            List of events after the timestamp
        """
        return [event for event in self.events if event.get("timestamp", 0) > timestamp]

    def to_adk_session_dict(self) -> dict[str, Any]:
        """
        Convert to ADK Session dictionary format.

        Returns:
            Dictionary compatible with google.adk.sessions.Session
        """
        return {
            "id": self.session_id,
            "app_name": self.app_name,
            "user_id": self.user_id,
            "state": self.session_state,
            "events": self.events,
            "last_update_time": self.last_update_time,
        }

    @classmethod
    def from_adk_session(
        cls,
        session_id: str,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        events: list[dict[str, Any]] | None = None,
        last_update_time: float | None = None,
    ) -> AdkSession:
        """
        Create AdkSession from ADK Session data.

        Args:
            session_id: ADK session ID
            app_name: Application name
            user_id: User ID
            state: Session state dictionary
            events: List of serialized events
            last_update_time: Last update timestamp

        Returns:
            AdkSession instance
        """
        now = datetime.now(timezone.utc).timestamp()
        return cls(
            session_id=session_id,
            app_name=app_name,
            user_id=user_id,
            session_state=state or {},
            events=events or [],
            last_update_time=last_update_time or now,
            create_time=now,
        )
