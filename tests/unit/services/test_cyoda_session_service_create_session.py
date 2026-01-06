"""Tests for create_session method in CyodaSessionService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from application.services.cyoda_session_service import CyodaSessionService


class TestCreateSession:
    """Tests for create_session method."""

    def _create_mock_session(self, session_id="test-session"):
        """Helper to create a properly configured mock session."""
        mock_session = MagicMock()
        mock_session.model_dump = MagicMock(return_value={"session_id": session_id})
        mock_session.events = []
        mock_session.session_state = {}
        mock_session.technical_id = None
        mock_session.session_id = session_id
        mock_session.app_name = "test-app"
        mock_session.user_id = "user-1"
        mock_session.last_update_time = 1234567890.0
        return mock_session

    @pytest.mark.asyncio
    async def test_create_session_basic(self):
        """Test basic session creation."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        response = MagicMock()
        response.metadata.id = "session-123"
        response.metadata.state = "active"
        entity_service.save = AsyncMock(return_value=response)
        entity_service.execute_transition = AsyncMock()

        with patch("application.services.session_service.initialization.AdkSession") as mock_adk:
            mock_session = self._create_mock_session()
            mock_adk.from_adk_session = MagicMock(return_value=mock_session)

            result = await session_service.create_session(
                app_name="test-app",
                user_id="user-1"
            )

            assert result is not None
            entity_service.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_with_session_id(self):
        """Test session creation with provided session ID."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        response = MagicMock()
        response.metadata.id = "session-123"
        response.metadata.state = "active"
        entity_service.save = AsyncMock(return_value=response)
        entity_service.execute_transition = AsyncMock()

        with patch("application.services.session_service.initialization.AdkSession") as mock_adk:
            mock_session = self._create_mock_session("custom-id")
            mock_adk.from_adk_session = MagicMock(return_value=mock_session)

            result = await session_service.create_session(
                app_name="test-app",
                user_id="user-1",
                session_id="custom-id"
            )

            assert result is not None
            call_args = mock_adk.from_adk_session.call_args
            assert call_args[1]["session_id"] == "custom-id"

    @pytest.mark.asyncio
    async def test_create_session_with_state(self):
        """Test session creation with initial state."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        response = MagicMock()
        response.metadata.id = "session-123"
        response.metadata.state = "active"
        entity_service.save = AsyncMock(return_value=response)
        entity_service.execute_transition = AsyncMock()

        initial_state = {"key": "value"}

        with patch("application.services.session_service.initialization.AdkSession") as mock_adk:
            mock_session = self._create_mock_session()
            mock_adk.from_adk_session = MagicMock(return_value=mock_session)

            result = await session_service.create_session(
                app_name="test-app",
                user_id="user-1",
                state=initial_state
            )

            assert result is not None
            call_args = mock_adk.from_adk_session.call_args
            assert call_args[1]["state"] == initial_state

    @pytest.mark.asyncio
    async def test_create_session_generates_uuid_when_not_provided(self):
        """Test that UUID is generated when session_id not provided."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        response = MagicMock()
        response.metadata.id = "session-123"
        response.metadata.state = "active"
        entity_service.save = AsyncMock(return_value=response)
        entity_service.execute_transition = AsyncMock()

        with patch("application.services.session_service.initialization.AdkSession") as mock_adk:
            mock_session = self._create_mock_session()
            mock_adk.from_adk_session = MagicMock(return_value=mock_session)

            result = await session_service.create_session(
                app_name="test-app",
                user_id="user-1"
            )

            assert result is not None
            call_args = mock_adk.from_adk_session.call_args
            session_id = call_args[1]["session_id"]
            assert session_id is not None
            assert len(session_id) > 0

    @pytest.mark.asyncio
    async def test_create_session_strips_whitespace_from_session_id(self):
        """Test that whitespace is stripped from provided session ID."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        response = MagicMock()
        response.metadata.id = "session-123"
        response.metadata.state = "active"
        entity_service.save = AsyncMock(return_value=response)
        entity_service.execute_transition = AsyncMock()

        with patch("application.services.session_service.initialization.AdkSession") as mock_adk:
            mock_session = self._create_mock_session("custom-id")
            mock_adk.from_adk_session = MagicMock(return_value=mock_session)

            result = await session_service.create_session(
                app_name="test-app",
                user_id="user-1",
                session_id="  custom-id  "
            )

            assert result is not None
            call_args = mock_adk.from_adk_session.call_args
            assert call_args[1]["session_id"] == "custom-id"

    @pytest.mark.asyncio
    async def test_create_session_activates_session(self):
        """Test that session is activated after creation."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        response = MagicMock()
        response.metadata.id = "session-123"
        response.metadata.state = "active"
        entity_service.save = AsyncMock(return_value=response)
        entity_service.execute_transition = AsyncMock()

        with patch("application.services.session_service.initialization.AdkSession") as mock_adk:
            mock_session = self._create_mock_session()
            mock_adk.from_adk_session = MagicMock(return_value=mock_session)

            result = await session_service.create_session(
                app_name="test-app",
                user_id="user-1"
            )

            assert result is not None
            entity_service.execute_transition.assert_called_once()
            call_args = entity_service.execute_transition.call_args
            assert call_args[1]["transition"] == "activate"

    @pytest.mark.asyncio
    async def test_create_session_handles_activation_failure(self):
        """Test that activation failure doesn't prevent session creation."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        response = MagicMock()
        response.metadata.id = "session-123"
        response.metadata.state = "active"
        entity_service.save = AsyncMock(return_value=response)
        entity_service.execute_transition = AsyncMock(side_effect=Exception("Activation failed"))

        with patch("application.services.session_service.initialization.AdkSession") as mock_adk:
            mock_session = self._create_mock_session()
            mock_adk.from_adk_session = MagicMock(return_value=mock_session)

            result = await session_service.create_session(
                app_name="test-app",
                user_id="user-1"
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_create_session_stores_technical_id_in_state(self):
        """Test that technical_id is stored in session state."""
        entity_service = AsyncMock()
        session_service = CyodaSessionService(entity_service)

        response = MagicMock()
        response.metadata.id = "tech-id-123"
        response.metadata.state = "active"
        entity_service.save = AsyncMock(return_value=response)
        entity_service.execute_transition = AsyncMock()

        with patch("application.services.session_service.initialization.AdkSession") as mock_adk:
            mock_session = self._create_mock_session()
            mock_adk.from_adk_session = MagicMock(return_value=mock_session)

            result = await session_service.create_session(
                app_name="test-app",
                user_id="user-1"
            )

            assert result is not None
            assert "__cyoda_technical_id__" in result.state

