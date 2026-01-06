"""Tests for get_session method in CyodaSessionService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from google.adk.sessions.session import Session

from application.services.cyoda_session_service import CyodaSessionService
from application.entity.adk_session import AdkSession


class TestGetSession:
    """Tests for get_session method."""

    @pytest.mark.asyncio
    async def test_get_session_fast_lookup_by_technical_id(self):
        """Test fast lookup when session_id is a UUID."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        # Mock AdkSession
        mock_adk_session = MagicMock(spec=AdkSession)
        mock_adk_session.technical_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_adk_session.events = []

        with patch('application.services.cyoda_session_service.try_fast_lookup') as mock_fast:
            mock_fast.return_value = MagicMock(spec=Session)

            result = await session_service.get_session(
                app_name="test-app",
                user_id="user-123",
                session_id="550e8400-e29b-41d4-a716-446655440000"
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_session_fallback_to_search(self):
        """Test fallback to search when fast lookup fails."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        # Mock AdkSession from search
        mock_adk_session = MagicMock(spec=AdkSession)
        mock_adk_session.technical_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_adk_session.events = []

        with patch('application.services.cyoda_session_service.fallback_search_with_retry') as mock_search:
            mock_search.return_value = MagicMock(spec=Session)

            result = await session_service.get_session(
                app_name="test-app",
                user_id="user-123",
                session_id="550e8400-e29b-41d4-a716-446655440000"
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_session_non_uuid_session_id(self):
        """Test get_session with non-UUID session_id."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        # Mock AdkSession from search
        mock_adk_session = MagicMock(spec=AdkSession)
        mock_adk_session.technical_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_adk_session.events = []

        with patch('application.services.cyoda_session_service.fallback_search_with_retry') as mock_search:
            mock_search.return_value = MagicMock(spec=Session)

            result = await session_service.get_session(
                app_name="test-app",
                user_id="user-123",
                session_id="conv-123"
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """Test get_session when session not found."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        with patch('application.services.cyoda_session_service.fallback_search') as mock_search:
            mock_search.return_value = None

            result = await session_service.get_session(
                app_name="test-app",
                user_id="user-123",
                session_id="conv-123"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_get_session_with_config_num_recent_events(self):
        """Test get_session with config filtering recent events."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        # Mock Session with events
        mock_session = MagicMock(spec=Session)
        mock_session.events = [MagicMock() for _ in range(10)]

        with patch('application.services.cyoda_session_service.try_fast_lookup') as mock_fast:
            mock_fast.return_value = mock_session

            from google.adk.sessions.base_session_service import GetSessionConfig
            config = GetSessionConfig(num_recent_events=5)

            result = await session_service.get_session(
                app_name="test-app",
                user_id="user-123",
                session_id="550e8400-e29b-41d4-a716-446655440000",
                config=config
            )

            assert result is not None
            # Verify events were filtered
            assert len(result.events) == 5

    @pytest.mark.asyncio
    async def test_get_session_with_config_after_timestamp(self):
        """Test get_session with config filtering by timestamp."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        # Mock Session with events
        mock_event1 = MagicMock()
        mock_event1.timestamp = 1000
        mock_event2 = MagicMock()
        mock_event2.timestamp = 2000

        mock_session = MagicMock(spec=Session)
        mock_session.events = [mock_event1, mock_event2]

        with patch('application.services.cyoda_session_service.try_fast_lookup') as mock_fast:
            mock_fast.return_value = mock_session

            from google.adk.sessions.base_session_service import GetSessionConfig
            config = GetSessionConfig(after_timestamp=1500)

            result = await session_service.get_session(
                app_name="test-app",
                user_id="user-123",
                session_id="550e8400-e29b-41d4-a716-446655440000",
                config=config
            )

            assert result is not None
            # Verify only events after timestamp are included
            assert len(result.events) == 1
            assert result.events[0].timestamp == 2000

    @pytest.mark.asyncio
    async def test_get_session_search_fallback_with_config(self):
        """Test get_session search fallback applies config filtering."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        # Mock Session
        mock_session = MagicMock(spec=Session)
        mock_session.events = [MagicMock() for _ in range(10)]

        with patch('application.services.cyoda_session_service.fallback_search_with_retry') as mock_search:
            mock_search.return_value = mock_session

            from google.adk.sessions.base_session_service import GetSessionConfig
            config = GetSessionConfig(num_recent_events=3)

            result = await session_service.get_session(
                app_name="test-app",
                user_id="user-123",
                session_id="conv-123",
                config=config
            )

            assert result is not None
            assert len(result.events) == 3

