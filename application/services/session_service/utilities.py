"""Serialization, deserialization, and conversion utilities for CyodaSessionService."""

import copy
import logging
from typing import Any

from google.adk.events.event import Event
from google.adk.sessions.session import Session

from application.entity.adk_session import AdkSession
from .message_sanitizer import sanitize_adk_session_events

logger = logging.getLogger(__name__)


def to_adk_session(adk_session: AdkSession, deserialize_event_fn) -> Session:
    """Convert AdkSession entity to ADK Session object.

    Args:
        adk_session: AdkSession entity
        deserialize_event_fn: Function to deserialize event data

    Returns:
        ADK Session object
    """
    events = [deserialize_event_fn(event_data) for event_data in adk_session.events]

    # Sanitize events to remove incomplete tool call sequences
    events = sanitize_adk_session_events(events)

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


def serialize_event(event: Event) -> dict[str, Any]:
    """Serialize an Event object to dictionary.

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


def filter_none_values(data: Any) -> Any:
    """Recursively filter out None values from dictionaries.

    Args:
        data: Data to filter (dict, list, or other)

    Returns:
        Filtered data with None values removed
    """
    if isinstance(data, dict):
        return {
            k: filter_none_values(v)
            for k, v in data.items()
            if v is not None
        }
    elif isinstance(data, list):
        return [filter_none_values(item) for item in data]
    else:
        return data


def deserialize_event(event_data: dict[str, Any]) -> Event:
    """Deserialize an event dictionary to Event object.

    Args:
        event_data: Serialized event dictionary

    Returns:
        Event object
    """
    # Filter out None values recursively to avoid Pydantic validation errors
    filtered_data = filter_none_values(event_data)

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
