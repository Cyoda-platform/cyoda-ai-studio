"""Unit tests for cyoda_session_service module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.sessions.session import Session

from application.entity.adk_session import AdkSession
from application.services.cyoda_session_service import (
    CachedSession,
    CyodaSessionService,
)


class TestCachedSession:
    """Test CachedSession dataclass."""

    def test_cached_session_initialization(self):
        """Test CachedSession initialization."""
        adk_session = MagicMock(spec=AdkSession)
        cached = CachedSession(session=adk_session, cached_at=123.45)
        assert cached.session == adk_session
        assert cached.cached_at == 123.45
        assert cached.pending_events == []
        assert cached.pending_state_delta == {}
        assert cached.is_dirty is False


class TestCyodaSessionService:
    """Test CyodaSessionService class."""

    @pytest.fixture
    def mock_entity_service(self):
        """Create mock entity service."""
        return AsyncMock()

    @pytest.fixture
    def session_service(self, mock_entity_service):
        """Create CyodaSessionService instance."""
        return CyodaSessionService(mock_entity_service)

    @pytest.mark.asyncio
    async def test_create_session(self, session_service, mock_entity_service):
        """Test creating a new session."""
        mock_response = MagicMock()
        mock_response.metadata.id = "tech-id-123"
        mock_response.metadata.state = "active"
        mock_entity_service.save.return_value = mock_response
        mock_entity_service.execute_transition.return_value = None

        session = await session_service.create_session(
            app_name="test-app",
            user_id="user1",
            session_id="session1",
            state={"key": "value"},
        )

        assert session is not None
        assert session.id == "session1"
        assert session.app_name == "test-app"
        assert session.user_id == "user1"
        mock_entity_service.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_by_technical_id(
        self, session_service, mock_entity_service
    ):
        """Test getting session by technical ID."""
        # Create a proper AdkSession instance
        adk_session = AdkSession(
            session_id="session1",
            app_name="test-app",
            user_id="user1",
            session_state={},
            events=[],
        )
        adk_session.technical_id = "tech-id-123"

        mock_response = MagicMock()
        mock_response.data = adk_session
        mock_response.metadata.id = "tech-id-123"
        mock_entity_service.get_by_id.return_value = mock_response

        result = await session_service.get_session_by_technical_id("tech-id-123")

        assert result is not None
        assert result.session_id == "session1"

    @pytest.mark.asyncio
    async def test_get_pending_event_count(self, session_service):
        """Test getting pending event count."""
        adk_session = MagicMock(spec=AdkSession)
        cached = CachedSession(session=adk_session, cached_at=123.45)
        cached.pending_events = [{"event": 1}, {"event": 2}]
        session_service._session_cache["tech-id"] = cached

        count = session_service.get_pending_event_count("tech-id")
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_pending_state_delta(self, session_service):
        """Test getting pending state delta."""
        adk_session = MagicMock(spec=AdkSession)
        cached = CachedSession(session=adk_session, cached_at=123.45)
        cached.pending_state_delta = {"key": "value"}
        session_service._session_cache["tech-id"] = cached

        delta = session_service.get_pending_state_delta("tech-id")
        assert delta == {"key": "value"}

    def test_clear_cache_specific(self, session_service):
        """Test clearing specific cache entry."""
        adk_session = MagicMock(spec=AdkSession)
        cached = CachedSession(session=adk_session, cached_at=123.45)
        session_service._session_cache["tech-id"] = cached

        session_service.clear_cache("tech-id")
        assert "tech-id" not in session_service._session_cache

    def test_clear_cache_all(self, session_service):
        """Test clearing all cache entries."""
        adk_session = MagicMock(spec=AdkSession)
        cached = CachedSession(session=adk_session, cached_at=123.45)
        session_service._session_cache["tech-id-1"] = cached
        session_service._session_cache["tech-id-2"] = cached

        session_service.clear_cache()
        assert len(session_service._session_cache) == 0

    @pytest.mark.asyncio
    async def test_list_sessions(self, session_service, mock_entity_service):
        """Test listing sessions."""
        adk_session = AdkSession(
            session_id="session1",
            app_name="test-app",
            user_id="user1",
            session_state={},
            events=[],
        )

        mock_response = MagicMock()
        mock_response.data = MagicMock()
        mock_response.data.model_dump = MagicMock(
            return_value={
                "session_id": "session1",
                "app_name": "test-app",
                "user_id": "user1",
                "session_state": {},
                "events": [],
            }
        )
        mock_entity_service.search.return_value = [mock_response]

        result = await session_service.list_sessions(
            app_name="test-app", user_id="user1"
        )

        assert result is not None
        assert len(result.sessions) == 1
