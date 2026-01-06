"""Advanced tests for Cyoda Session Service.

This module tests advanced features like event handling, session persistence,
and configuration options.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.events.event import Event
from google.adk.sessions.base_session_service import GetSessionConfig
from google.adk.sessions.session import Session

from application.entity.adk_session import AdkSession
from application.services.cyoda_session_service import CyodaSessionService
from common.entity.cyoda_entity import CyodaEntity
from common.service.entity_service import EntityMetadata, EntityResponse


@pytest.fixture
def mock_entity_service():
    """Create mock entity service."""
    service = MagicMock()
    service.save = AsyncMock()
    service.search = AsyncMock()
    service.update = AsyncMock()
    service.delete_by_id = AsyncMock()
    return service


@pytest.fixture
def session_service(mock_entity_service):
    """Create Cyoda session service with mocked entity service."""
    return CyodaSessionService(mock_entity_service)


@pytest.mark.asyncio
async def test_get_session_with_config(session_service, mock_entity_service):
    """Test retrieving session with event filtering."""
    from datetime import datetime

    events = [
        {"invocation_id": f"inv-{i}", "timestamp": 1704067200.0 + i, "author": "user"}
        for i in range(10)
    ]

    adk_session = AdkSession(
        session_id="session-abc",
        app_name="test_app",
        user_id="user123",
        session_state={},
        events=events,
        last_update_time=1704067200.0,
        technical_id="tech-123",
    )

    mock_entity_service.search.return_value = [
        EntityResponse(
            data=adk_session,
            metadata=EntityMetadata(
                id="tech-123",
                state="active",
                created_at=datetime.now(),
                entity_type="AdkSession",
            ),
        )
    ]

    config = GetSessionConfig(num_recent_events=3)
    session = await session_service.get_session(
        app_name="test_app",
        user_id="user123",
        session_id="session-abc",
        config=config,
    )

    assert len(session.events) == 3


@pytest.mark.asyncio
async def test_append_event(session_service, mock_entity_service):
    """Test appending an event to a session."""
    from datetime import datetime

    adk_session = AdkSession(
        session_id="session-abc",
        app_name="test_app",
        user_id="user123",
        session_state={},
        events=[],
        last_update_time=1704067200.0,
        technical_id="tech-123",
    )

    mock_entity_service.search.return_value = [
        EntityResponse(
            data=adk_session,
            metadata=EntityMetadata(
                id="tech-123",
                state="active",
                created_at=datetime.now(),
                entity_type="AdkSession",
            ),
        )
    ]

    def update_side_effect(entity_id, entity, entity_class, transition, entity_version):
        return EntityResponse(
            data=AdkSession(**entity),
            metadata=EntityMetadata(
                id=entity_id,
                state="active",
                created_at=datetime.now(),
                entity_type="AdkSession",
            ),
        )

    mock_entity_service.update.side_effect = update_side_effect

    session = Session(
        id="session-abc",
        app_name="test_app",
        user_id="user123",
        state={},
        events=[],
    )

    event = Event(
        invocation_id="inv-001",
        author="user",
        timestamp=1704067200.0,
    )

    await session_service.append_event(session, event)

    mock_entity_service.update.assert_called_once()
    assert len(session.events) == 1


@pytest.mark.asyncio
async def test_session_persistence_simulation(session_service, mock_entity_service):
    """Test that sessions can be retrieved after 'restart'."""
    from datetime import datetime

    adk_session = AdkSession(
        session_id="persistent-session",
        app_name="test_app",
        user_id="user123",
        session_state={"context": "important"},
        events=[
            {"invocation_id": "inv-001", "timestamp": 1704067200.0, "author": "user"}
        ],
        last_update_time=1704067200.0,
        technical_id="tech-123",
    )

    def save_side_effect(entity, entity_class, entity_version):
        return EntityResponse(
            data=AdkSession(**entity),
            metadata=EntityMetadata(
                id="tech-123",
                state="active",
                created_at=datetime.now(),
                entity_type="AdkSession",
            ),
        )

    # First search returns empty (session doesn't exist yet), second returns the session
    search_call_count = [0]

    def search_side_effect(entity_class, condition, entity_version):
        search_call_count[0] += 1
        if search_call_count[0] == 1:
            return []  # First call: session doesn't exist
        else:
            return [  # Subsequent calls: session exists
                EntityResponse(
                    data=adk_session,
                    metadata=EntityMetadata(
                        id="tech-123",
                        state="active",
                        created_at=datetime.now(),
                        entity_type="AdkSession",
                    ),
                )
            ]

    mock_entity_service.save.side_effect = save_side_effect
    mock_entity_service.search.side_effect = search_side_effect

    session1 = await session_service.create_session(
        app_name="test_app",
        user_id="user123",
        session_id="persistent-session",
        state={"context": "important"},
    )

    session2 = await session_service.get_session(
        app_name="test_app",
        user_id="user123",
        session_id="persistent-session",
    )

    assert session2 is not None
    assert session2.id == session1.id
    assert session2.state == {"context": "important"}
