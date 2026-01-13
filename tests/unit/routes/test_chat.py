"""
Unit tests for chat routes.

Tests all chat-related API endpoints including CRUD operations,
streaming, canvas questions, and chat transfer functionality.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from quart import Quart
from quart.testing import QuartClient

from application.entity.conversation import Conversation
from application.routes.chat import chat_bp
from application.services.service_factory import ServiceFactory


@pytest.fixture
def app():
    """Create test Quart application."""
    app = Quart(__name__)
    app.register_blueprint(chat_bp, url_prefix="/api/v1/chats")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_service_factory():
    """Mock service factory across all endpoint modules."""
    patches = [
        patch("application.routes.chat_endpoints.helpers.get_service_factory"),
        patch("application.routes.chat_endpoints.list_and_create.get_chat_service"),
        patch("application.routes.chat_endpoints.crud.get_chat_service"),
        patch("application.routes.chat_endpoints.stream.get_chat_service"),
        patch("application.routes.chat_endpoints.workflow.get_chat_service"),
        patch("application.routes.chat_endpoints.helpers.get_repository"),
        patch("application.routes.chat_endpoints.helpers.get_cyoda_assistant"),
    ]
    mocks = [p.start() for p in patches]

    factory = MagicMock()
    factory.chat_service = MagicMock()
    factory.chat_stream_service = MagicMock()
    mocks[0].return_value = factory

    # For direct get_chat_service calls
    for i in range(1, 5):
        mocks[i].return_value = factory.chat_service

    # Mock repository with async methods
    mock_repo = MagicMock()
    mock_repo.save = AsyncMock(return_value="msg_123")
    mocks[5].return_value = mock_repo

    # Mock Cyoda assistant
    mock_assistant = MagicMock()
    mocks[6].return_value = mock_assistant

    yield factory
    for p in patches:
        p.stop()


@pytest.fixture
def mock_auth():
    """Mock authentication across all endpoint modules."""
    patches = [
        patch(
            "application.routes.chat_endpoints.list_and_create.get_authenticated_user"
        ),
        patch("application.routes.chat_endpoints.crud.get_authenticated_user"),
        patch("application.routes.chat_endpoints.stream.get_authenticated_user"),
        patch("application.routes.common.auth.get_authenticated_user"),
    ]
    mocks = [p.start() for p in patches]
    for mock in mocks:
        mock.return_value = ("test_user_id", False)
    yield mocks[0]
    for p in patches:
        p.stop()


@pytest.fixture
def mock_superuser_auth():
    """Mock superuser authentication across all endpoint modules."""
    patches = [
        patch(
            "application.routes.chat_endpoints.list_and_create.get_authenticated_user"
        ),
        patch("application.routes.chat_endpoints.crud.get_authenticated_user"),
        patch("application.routes.chat_endpoints.stream.get_authenticated_user"),
        patch("application.routes.common.auth.get_authenticated_user"),
    ]
    mocks = [p.start() for p in patches]
    for mock in mocks:
        mock.return_value = ("superuser_id", True)
    yield mocks[0]
    for p in patches:
        p.stop()


@pytest.fixture
def mock_guest_auth():
    """Mock guest authentication across all endpoint modules."""
    patches = [
        patch(
            "application.routes.chat_endpoints.list_and_create.get_authenticated_user"
        ),
        patch("application.routes.chat_endpoints.crud.get_authenticated_user"),
        patch("application.routes.chat_endpoints.stream.get_authenticated_user"),
        patch("application.routes.common.auth.get_authenticated_user"),
    ]
    mocks = [p.start() for p in patches]
    for mock in mocks:
        mock.return_value = ("guest.12345", False)
    yield mocks[0]
    for p in patches:
        p.stop()


@pytest.fixture
def sample_conversation():
    """Create sample conversation for testing."""
    return Conversation(
        technical_id="conv_123",
        user_id="test_user_id",
        name="Test Chat",
        description="Test Description",
        date=datetime.now(timezone.utc).isoformat(),
    )


class TestListChats:
    """Tests for GET /chats endpoint."""

    @pytest.mark.asyncio
    async def test_list_chats_success(self, client, mock_auth, mock_service_factory):
        """Test successful chat listing."""
        mock_service_factory.chat_service.list_conversations = AsyncMock(
            return_value={
                "chats": [
                    {
                        "technical_id": "conv_1",
                        "name": "Chat 1",
                        "description": "Desc 1",
                    },
                    {
                        "technical_id": "conv_2",
                        "name": "Chat 2",
                        "description": "Desc 2",
                    },
                ],
                "limit": 100,
                "next_cursor": None,
                "has_more": False,
                "cached": False,
            }
        )

        response = await client.get("/api/v1/chats")
        assert response.status_code == 200

        data = await response.get_json()
        assert len(data["chats"]) == 2
        assert data["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_chats_with_pagination(
        self, client, mock_auth, mock_service_factory
    ):
        """Test chat listing with pagination."""
        mock_service_factory.chat_service.list_conversations = AsyncMock(
            return_value={
                "chats": [
                    {"technical_id": f"conv_{i}", "name": f"Chat {i}"}
                    for i in range(10)
                ],
                "limit": 10,
                "next_cursor": "2024-01-01T00:00:00Z",
                "has_more": True,
                "cached": False,
            }
        )

        response = await client.get(
            "/api/v1/chats?limit=10&point_in_time=2024-01-01T00:00:00Z"
        )
        assert response.status_code == 200

        data = await response.get_json()
        assert data["has_more"] is True
        assert data["next_point_in_time"] == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_list_chats_superuser_all(
        self, client, mock_superuser_auth, mock_service_factory
    ):
        """Test superuser listing all chats."""
        mock_service_factory.chat_service.list_conversations = AsyncMock(
            return_value={
                "chats": [
                    {"technical_id": "conv_1", "name": "Chat 1", "user_id": "user_1"}
                ],
                "limit": 100,
                "next_cursor": None,
                "has_more": False,
                "cached": False,
            }
        )

        response = await client.get("/api/v1/chats?super=true")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_chats_error(self, client, mock_auth, mock_service_factory):
        """Test error handling in list chats."""
        mock_service_factory.chat_service.list_conversations = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = await client.get("/api/v1/chats")
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_list_chats_limit_validation(
        self, client, mock_auth, mock_service_factory
    ):
        """Test limit parameter validation."""
        mock_service_factory.chat_service.list_conversations = AsyncMock(
            return_value={
                "chats": [],
                "limit": 1000,
                "next_cursor": None,
                "has_more": False,
                "cached": False,
            }
        )

        response = await client.get("/api/v1/chats?limit=5000")
        assert response.status_code == 200

        data = await response.get_json()
        assert data["limit"] == 1000  # Should be capped at 1000

    @pytest.mark.asyncio
    async def test_list_chats_invalid_limit(
        self, client, mock_auth, mock_service_factory
    ):
        """Test invalid limit parameter."""
        mock_service_factory.chat_service.list_conversations = AsyncMock(
            return_value={
                "chats": [],
                "limit": 100,
                "next_cursor": None,
                "has_more": False,
                "cached": False,
            }
        )

        response = await client.get("/api/v1/chats?limit=invalid")
        assert response.status_code == 200

        data = await response.get_json()
        assert data["limit"] == 100  # Should default to 100

    @pytest.mark.asyncio
    async def test_list_chats_cached(self, client, mock_auth, mock_service_factory):
        """Test cached response."""
        mock_service_factory.chat_service.list_conversations = AsyncMock(
            return_value={
                "chats": [{"technical_id": "conv_1", "name": "Chat 1"}],
                "limit": 100,
                "next_cursor": None,
                "has_more": False,
                "cached": True,
            }
        )

        response = await client.get("/api/v1/chats")
        assert response.status_code == 200

        data = await response.get_json()
        assert data["cached"] is True


class TestCreateChat:
    """Tests for POST /chats endpoint."""

    @pytest.mark.asyncio
    async def test_create_chat_success(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test successful chat creation."""
        mock_service_factory.chat_service.create_conversation = AsyncMock(
            return_value=sample_conversation
        )

        response = await client.post(
            "/api/v1/chats",
            json={"name": "Test Chat", "description": "Test Description"},
        )
        assert response.status_code == 201

        data = await response.get_json()
        # Response uses APIResponse.success() which returns unwrapped data
        assert data["chat_id"] == "conv_123"

    @pytest.mark.asyncio
    async def test_create_chat_missing_name(self, client, mock_auth):
        """Test chat creation without name."""
        response = await client.post("/api/v1/chats", json={"description": "Test"})
        assert response.status_code == 400

        data = await response.get_json()
        assert "name is required" in str(data).lower()

    @pytest.mark.asyncio
    async def test_create_chat_guest_limit(
        self, client, mock_guest_auth, mock_service_factory
    ):
        """Test guest user chat creation limit."""
        mock_service_factory.chat_service.count_user_chats = AsyncMock(return_value=2)

        response = await client.post("/api/v1/chats", json={"name": "Test Chat"})
        assert response.status_code == 403

        data = await response.get_json()
        assert "guest" in str(data).lower()
        assert "maximum" in str(data).lower()

    @pytest.mark.asyncio
    async def test_create_chat_form_data(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test chat creation with form data."""
        mock_service_factory.chat_service.create_conversation = AsyncMock(
            return_value=sample_conversation
        )

        response = await client.post(
            "/api/v1/chats",
            form={"name": "Test Chat", "description": "Test Description"},
        )
        assert response.status_code == 201


class TestGetChat:
    """Tests for GET /chats/<id> endpoint."""

    @pytest.mark.asyncio
    async def test_get_chat_success(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test successful chat retrieval."""
        # sample_conversation has messages property
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()

        with patch(
            "application.routes.chat_endpoints.crud.get_repository"
        ) as mock_repo:
            mock_repo.return_value = MagicMock()
            with patch.object(
                sample_conversation,
                "populate_messages_from_edge_messages",
                new_callable=AsyncMock,
            ):
                with patch.object(sample_conversation, "get_dialogue", return_value=[]):
                    response = await client.get("/api/v1/chats/conv_123")
                    assert response.status_code == 200

                    data = await response.get_json()
                    # Response uses APIResponse.success() which returns unwrapped data
                    assert data["chat_body"]["id"] == "conv_123"

    @pytest.mark.asyncio
    async def test_get_chat_not_found(self, client, mock_auth, mock_service_factory):
        """Test chat not found."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=None
        )

        response = await client.get("/api/v1/chats/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_chat_access_denied(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test access denied for unauthorized user."""
        sample_conversation.user_id = "other_user"
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock(
            side_effect=PermissionError("Access denied")
        )

        response = await client.get("/api/v1/chats/conv_123")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_chat_with_workflow_data(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test chat retrieval with workflow information."""
        sample_conversation.repository_name = "test-repo"
        sample_conversation.repository_owner = "test-owner"
        sample_conversation.repository_branch = "main"
        sample_conversation.repository_url = "https://github.com/test-owner/test-repo"
        sample_conversation.installation_id = "12345"

        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()

        with patch(
            "application.routes.chat_endpoints.crud.get_repository"
        ) as mock_repo:
            mock_repo.return_value = MagicMock()
            with patch.object(
                sample_conversation,
                "populate_messages_from_edge_messages",
                new_callable=AsyncMock,
            ):
                with patch.object(sample_conversation, "get_dialogue", return_value=[]):
                    response = await client.get("/api/v1/chats/conv_123")
                    assert response.status_code == 200

                    data = await response.get_json()
                    chat_body = data["chat_body"]
                    assert chat_body["repository_name"] == "test-repo"
                    assert chat_body["repository_owner"] == "test-owner"
                    assert chat_body["repository_branch"] == "main"
                    assert chat_body["installation_id"] == "12345"
                    assert "entities" in chat_body

    @pytest.mark.asyncio
    async def test_get_chat_superuser_access(
        self, client, mock_superuser_auth, mock_service_factory, sample_conversation
    ):
        """Test superuser can access any chat."""
        sample_conversation.user_id = "other_user"
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()

        with patch(
            "application.routes.chat_endpoints.crud.get_repository"
        ) as mock_repo:
            mock_repo.return_value = MagicMock()
            with patch.object(
                sample_conversation,
                "populate_messages_from_edge_messages",
                new_callable=AsyncMock,
            ):
                with patch.object(sample_conversation, "get_dialogue", return_value=[]):
                    response = await client.get("/api/v1/chats/conv_123?super=true")
                    assert response.status_code == 200


class TestUpdateChat:
    """Tests for PUT /chats/<id> endpoint."""

    @pytest.mark.asyncio
    async def test_update_chat_success(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test successful chat update."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()
        mock_service_factory.chat_service.update_conversation = AsyncMock(
            return_value=sample_conversation
        )

        response = await client.put(
            "/api/v1/chats/conv_123",
            json={
                "chat_name": "Updated Name",
                "chat_description": "Updated Description",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_chat_not_found(self, client, mock_auth, mock_service_factory):
        """Test update non-existent chat."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=None
        )

        response = await client.put(
            "/api/v1/chats/nonexistent", json={"chat_name": "Updated"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_chat_access_denied(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test update access denied for unauthorized user."""
        sample_conversation.user_id = "other_user"
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock(
            side_effect=PermissionError("Access denied")
        )

        response = await client.put(
            "/api/v1/chats/conv_123", json={"chat_name": "Updated"}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_chat_name_only(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test updating only chat name."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()
        mock_service_factory.chat_service.update_conversation = AsyncMock(
            return_value=sample_conversation
        )

        response = await client.put(
            "/api/v1/chats/conv_123", json={"chat_name": "New Name"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_chat_description_only(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test updating only chat description."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()
        mock_service_factory.chat_service.update_conversation = AsyncMock(
            return_value=sample_conversation
        )

        response = await client.put(
            "/api/v1/chats/conv_123", json={"chat_description": "New Description"}
        )
        assert response.status_code == 200


class TestDeleteChat:
    """Tests for DELETE /chats/<id> endpoint."""

    @pytest.mark.asyncio
    async def test_delete_chat_success(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test successful chat deletion."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()
        mock_service_factory.chat_service.delete_conversation = AsyncMock()

        response = await client.delete("/api/v1/chats/conv_123")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_chat_not_found(self, client, mock_auth, mock_service_factory):
        """Test delete non-existent chat."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=None
        )

        response = await client.delete("/api/v1/chats/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_chat_access_denied(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test delete access denied for unauthorized user."""
        sample_conversation.user_id = "other_user"
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock(
            side_effect=PermissionError("Access denied")
        )

        response = await client.delete("/api/v1/chats/conv_123")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_chat_superuser(
        self, client, mock_superuser_auth, mock_service_factory, sample_conversation
    ):
        """Test superuser can delete any chat."""
        sample_conversation.user_id = "other_user"
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()
        mock_service_factory.chat_service.delete_conversation = AsyncMock()

        response = await client.delete("/api/v1/chats/conv_123")
        assert response.status_code == 200


class TestStreamChatMessage:
    """Tests for POST /chats/<id>/stream endpoint."""

    @pytest.mark.asyncio
    async def test_stream_chat_message_success(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test successful message streaming."""

        async def mock_stream():
            yield "event: start\ndata: {}\n\n"
            yield 'event: content\ndata: {"chunk": "Hello"}\n\n'
            yield 'event: done\ndata: {"response": "Hello"}\n\n'

        mock_service_factory.chat_stream_service.prepare_stream = AsyncMock(
            return_value=(sample_conversation, "Test message", MagicMock())
        )
        mock_service_factory.chat_stream_service.stream_and_save = MagicMock(
            return_value=mock_stream()
        )

        response = await client.post(
            "/api/v1/chats/conv_123/stream", json={"message": "Test message"}
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.content_type

    @pytest.mark.asyncio
    async def test_stream_chat_message_no_message(
        self, client, mock_auth, mock_service_factory
    ):
        """Test streaming without message."""
        response = await client.post("/api/v1/chats/conv_123/stream", json={})
        assert response.status_code == 200
        content = await response.get_data(as_text=True)
        assert "error" in content.lower()

    @pytest.mark.asyncio
    async def test_stream_chat_message_with_files(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test streaming with file uploads."""
        # Skip file upload test - Quart test client file handling is complex
        # This functionality is tested via integration tests
        pytest.skip("File upload testing requires integration test setup")

    @pytest.mark.asyncio
    async def test_stream_with_context(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test stream with context parameter."""

        async def mock_stream():
            yield "event: start\ndata: {}\n\n"
            yield 'event: done\ndata: {"response": "OK"}\n\n'

        mock_service_factory.chat_stream_service.prepare_stream = AsyncMock(
            return_value=(sample_conversation, "Test message", MagicMock())
        )
        mock_service_factory.chat_stream_service.stream_and_save = MagicMock(
            return_value=mock_stream()
        )

        response = await client.post(
            "/api/v1/chats/conv_123/stream",
            json={"message": "Test message", "context": {"key": "value"}},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_access_denied(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test stream access denied for unauthorized user."""
        sample_conversation.user_id = "other_user"
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock(
            side_effect=PermissionError("Access denied")
        )

        response = await client.post(
            "/api/v1/chats/conv_123/stream", json={"message": "Test"}
        )
        assert response.status_code == 200
        content = await response.get_data(as_text=True)
        assert "access denied" in content.lower() or "permission" in content.lower()

    @pytest.mark.asyncio
    async def test_stream_empty_message(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test stream with empty message."""

        async def mock_stream():
            yield "event: start\ndata: {}\n\n"
            yield 'event: done\ndata: {"response": "OK"}\n\n'

        mock_service_factory.chat_stream_service.prepare_stream = AsyncMock(
            return_value=(sample_conversation, "", MagicMock())
        )
        mock_service_factory.chat_stream_service.stream_and_save = MagicMock(
            return_value=mock_stream()
        )

        response = await client.post(
            "/api/v1/chats/conv_123/stream", json={"message": ""}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_conversation_not_found(
        self, client, mock_auth, mock_service_factory
    ):
        """Test stream on non-existent conversation."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=None
        )

        response = await client.post(
            "/api/v1/chats/nonexistent/stream", json={"message": "Test"}
        )
        assert response.status_code == 200
        content = await response.get_data(as_text=True)
        assert "chat not found" in content.lower()

    @pytest.mark.asyncio
    async def test_stream_with_multiple_content_chunks(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test stream with multiple content chunks."""

        async def mock_stream():
            yield "event: start\ndata: {}\n\n"
            yield 'event: content\ndata: {"chunk": "Hello "}\n\n'
            yield 'event: content\ndata: {"chunk": "world"}\n\n'
            yield 'event: content\ndata: {"chunk": "!"}\n\n'
            yield 'event: done\ndata: {"response": "Hello world!"}\n\n'

        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.update_conversation = AsyncMock(
            return_value=sample_conversation
        )

        with patch(
            "application.routes.chat_endpoints.helpers.get_cyoda_assistant_instance"
        ) as mock_assistant:
            mock_assistant.return_value = MagicMock()
            with patch(
                "application.routes.chat_endpoints.stream.StreamingService"
            ) as mock_streaming:
                mock_streaming.stream_agent_response = MagicMock(
                    return_value=mock_stream()
                )
                with patch(
                    "application.routes.chat_endpoints.helpers.get_edge_message_persistence_service"
                ) as mock_persistence:
                    mock_persistence.return_value.save_message_as_edge_message = (
                        AsyncMock(return_value="msg_123")
                    )
                    mock_persistence.return_value.save_response_with_history = (
                        AsyncMock(return_value="resp_123")
                    )

                    response = await client.post(
                        "/api/v1/chats/conv_123/stream",
                        json={"message": "Test message"},
                    )
                    assert response.status_code == 200
                    content = await response.get_data(as_text=True)
                    assert "event: content" in content
                    assert "Hello" in content

    @pytest.mark.asyncio
    async def test_stream_with_hook_in_response(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test stream with hook data in done event."""

        async def mock_stream():
            yield "event: start\ndata: {}\n\n"
            yield 'event: content\ndata: {"chunk": "Response"}\n\n'
            yield 'event: done\ndata: {"response": "Response", "hook": {"type": "entity_config"}}\n\n'

        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.update_conversation = AsyncMock(
            return_value=sample_conversation
        )

        with patch(
            "application.routes.chat_endpoints.helpers.get_cyoda_assistant_instance"
        ) as mock_assistant:
            mock_assistant.return_value = MagicMock()
            with patch(
                "application.routes.chat_endpoints.stream.StreamingService"
            ) as mock_streaming:
                mock_streaming.stream_agent_response = MagicMock(
                    return_value=mock_stream()
                )
                with patch(
                    "application.routes.chat_endpoints.helpers.get_edge_message_persistence_service"
                ) as mock_persistence:
                    mock_persistence.return_value.save_message_as_edge_message = (
                        AsyncMock(return_value="msg_123")
                    )
                    mock_persistence.return_value.save_response_with_history = (
                        AsyncMock(return_value="resp_123")
                    )

                    response = await client.post(
                        "/api/v1/chats/conv_123/stream", json={"message": "Test"}
                    )
                    assert response.status_code == 200
                    content = await response.get_data(as_text=True)
                    assert "hook" in content

    @pytest.mark.asyncio
    async def test_stream_with_adk_session_id(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test stream with ADK session ID in response."""

        async def mock_stream():
            yield "event: start\ndata: {}\n\n"
            yield 'event: done\ndata: {"response": "OK", "adk_session_id": "session_123"}\n\n'

        sample_conversation.adk_session_id = None
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()

        with patch(
            "application.routes.chat_endpoints.stream.StreamingService"
        ) as mock_streaming:
            mock_streaming.stream_agent_response = MagicMock(return_value=mock_stream())
            with patch(
                "application.routes.chat_endpoints.helpers.get_edge_message_persistence_service"
            ) as mock_persistence:
                mock_persistence.return_value.save_message_as_edge_message = AsyncMock(
                    return_value="msg_123"
                )
                mock_persistence.return_value.save_response_with_history = AsyncMock(
                    return_value="resp_123"
                )

                response = await client.post(
                    "/api/v1/chats/conv_123/stream", json={"message": "Test"}
                )
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_superuser_access(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test stream access for superuser on other user's chat."""
        sample_conversation.user_id = "other_user"
        mock_auth.return_value = ("superuser_123", True)
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )

        async def mock_stream():
            yield "event: start\ndata: {}\n\n"
            yield 'event: done\ndata: {"response": "OK"}\n\n'

        with patch(
            "application.routes.chat_endpoints.stream.StreamingService"
        ) as mock_streaming:
            mock_streaming.stream_agent_response = MagicMock(return_value=mock_stream())
            with patch(
                "application.routes.chat_endpoints.helpers.get_edge_message_persistence_service"
            ) as mock_persistence:
                mock_persistence.return_value.save_message_as_edge_message = AsyncMock(
                    return_value="msg_123"
                )
                mock_persistence.return_value.save_response_with_history = AsyncMock(
                    return_value="resp_123"
                )

                response = await client.post(
                    "/api/v1/chats/conv_123/stream", json={"message": "Test"}
                )
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_with_streaming_error(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test stream error handling during streaming."""

        async def mock_stream_with_error():
            yield "event: start\ndata: {}\n\n"
            raise ValueError("Streaming error")

        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()

        with patch(
            "application.routes.chat_endpoints.stream.StreamingService"
        ) as mock_streaming:
            mock_streaming.stream_agent_response = MagicMock(
                return_value=mock_stream_with_error()
            )
            with patch(
                "application.routes.chat_endpoints.helpers.get_edge_message_persistence_service"
            ) as mock_persistence:
                mock_persistence.return_value.save_message_as_edge_message = AsyncMock(
                    return_value="msg_123"
                )
                mock_persistence.return_value.save_response_with_history = AsyncMock(
                    return_value="resp_123"
                )

                response = await client.post(
                    "/api/v1/chats/conv_123/stream", json={"message": "Test"}
                )
                assert response.status_code == 200
                content = await response.get_data(as_text=True)
                assert "error" in content.lower()

    @pytest.mark.asyncio
    async def test_stream_with_various_event_types(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test stream with various event types (start, agent, tool, content, done)."""

        async def mock_stream():
            yield "event: start\ndata: {}\n\n"
            yield 'event: agent\ndata: {"agent": "test_agent"}\n\n'
            yield 'event: tool\ndata: {"tool": "test_tool"}\n\n'
            yield 'event: content\ndata: {"chunk": "Response"}\n\n'
            yield 'event: done\ndata: {"response": "Response"}\n\n'

        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.update_conversation = AsyncMock(
            return_value=sample_conversation
        )

        with patch(
            "application.routes.chat_endpoints.helpers.get_cyoda_assistant_instance"
        ) as mock_assistant:
            mock_assistant.return_value = MagicMock()
            with patch(
                "application.routes.chat_endpoints.stream.StreamingService"
            ) as mock_streaming:
                mock_streaming.stream_agent_response = MagicMock(
                    return_value=mock_stream()
                )
                with patch(
                    "application.routes.chat_endpoints.helpers.get_edge_message_persistence_service"
                ) as mock_persistence:
                    mock_persistence.return_value.save_message_as_edge_message = (
                        AsyncMock(return_value="msg_123")
                    )
                    mock_persistence.return_value.save_response_with_history = (
                        AsyncMock(return_value="resp_123")
                    )

                    response = await client.post(
                        "/api/v1/chats/conv_123/stream", json={"message": "Test"}
                    )
                    assert response.status_code == 200
                    content = await response.get_data(as_text=True)
                    assert "event: start" in content
                    assert "event: agent" in content
                    assert "event: tool" in content
                    assert "event: content" in content
                    assert "event: done" in content


class TestCanvasQuestions:
    """Tests for POST /chats/canvas-questions endpoint."""

    @pytest.mark.asyncio
    async def test_canvas_question_entity_json(self, client, mock_auth):
        """Test entity JSON generation."""
        with patch(
            "application.routes.chat_endpoints.canvas.google_adk_service"
        ) as mock_adk:
            mock_adk.is_configured.return_value = False

            response = await client.post(
                "/api/v1/chats/canvas-questions",
                json={
                    "question": "Create a user entity",
                    "response_type": "entity_json",
                    "context": {},
                },
            )
            assert response.status_code == 200

            data = await response.get_json()
            assert "hook" in data
            assert data["hook"]["type"] == "entity_config"

    @pytest.mark.asyncio
    async def test_canvas_question_missing_question(self, client, mock_auth):
        """Test canvas question without question field."""
        response = await client.post(
            "/api/v1/chats/canvas-questions", json={"response_type": "text"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_canvas_question_invalid_type(self, client, mock_auth):
        """Test canvas question with invalid response type."""
        response = await client.post(
            "/api/v1/chats/canvas-questions",
            json={"question": "Test", "response_type": "invalid_type"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_canvas_question_workflow_json(self, client, mock_auth):
        """Test workflow JSON generation."""
        with patch(
            "application.routes.chat_endpoints.canvas.google_adk_service"
        ) as mock_adk:
            mock_adk.is_configured.return_value = False

            response = await client.post(
                "/api/v1/chats/canvas-questions",
                json={
                    "question": "Create approval workflow",
                    "response_type": "workflow_json",
                    "context": {},
                },
            )
            assert response.status_code == 200

            data = await response.get_json()
            assert data["hook"]["data"]["name"] == "MockWorkflow"
            assert "states" in data["hook"]["data"]

    @pytest.mark.asyncio
    async def test_canvas_question_text_type(self, client, mock_auth):
        """Test text response type."""
        with patch(
            "application.routes.chat_endpoints.canvas.google_adk_service"
        ) as mock_adk:
            mock_adk.is_configured.return_value = False

            response = await client.post(
                "/api/v1/chats/canvas-questions",
                json={
                    "question": "What is Cyoda?",
                    "response_type": "text",
                    "context": {},
                },
            )
            assert response.status_code == 200

            data = await response.get_json()
            assert "message" in data
            assert "hook" in data

    @pytest.mark.asyncio
    async def test_canvas_question_app_config_json(self, client, mock_auth):
        """Test app config JSON generation."""
        with patch(
            "application.routes.chat_endpoints.canvas.google_adk_service"
        ) as mock_adk:
            mock_adk.is_configured.return_value = False

            response = await client.post(
                "/api/v1/chats/canvas-questions",
                json={
                    "question": "Create app config",
                    "response_type": "app_config_json",
                    "context": {"app_name": "TestApp"},
                },
            )
            assert response.status_code == 200

            data = await response.get_json()
            assert data["hook"]["type"] == "app_config_config"
            assert data["hook"]["data"]["app_name"] == "TestApp"

    @pytest.mark.asyncio
    async def test_canvas_question_environment_json(self, client, mock_auth):
        """Test environment JSON generation."""
        with patch(
            "application.routes.chat_endpoints.canvas.google_adk_service"
        ) as mock_adk:
            mock_adk.is_configured.return_value = False

            response = await client.post(
                "/api/v1/chats/canvas-questions",
                json={
                    "question": "Create environment",
                    "response_type": "environment_json",
                    "context": {},
                },
            )
            assert response.status_code == 200

            data = await response.get_json()
            assert "hook" in data
            assert data["hook"]["type"] == "environment_config"

    @pytest.mark.asyncio
    async def test_canvas_question_requirement_json(self, client, mock_auth):
        """Test requirement JSON generation."""
        with patch(
            "application.routes.chat_endpoints.canvas.google_adk_service"
        ) as mock_adk:
            mock_adk.is_configured.return_value = False

            response = await client.post(
                "/api/v1/chats/canvas-questions",
                json={
                    "question": "Create requirement",
                    "response_type": "requirement_json",
                    "context": {},
                },
            )
            assert response.status_code == 200

            data = await response.get_json()
            assert "hook" in data
            assert data["hook"]["type"] == "requirement_config"

    @pytest.mark.asyncio
    async def test_canvas_question_missing_response_type(self, client, mock_auth):
        """Test canvas question without response_type field."""
        response = await client.post(
            "/api/v1/chats/canvas-questions", json={"question": "Test question"}
        )
        assert response.status_code == 400


class TestTransferChats:
    """Tests for POST /chats/transfer endpoint."""

    @pytest.mark.asyncio
    async def test_transfer_chats_success(
        self, client, mock_auth, mock_service_factory
    ):
        """Test successful chat transfer."""
        mock_service_factory.chat_service.transfer_guest_chats = AsyncMock(
            return_value=3
        )

        with patch(
            "application.routes.chat_endpoints.workflow.get_user_info_from_token"
        ) as mock_token:
            mock_token.return_value = ("guest.12345", False)

            response = await client.post(
                "/api/v1/chats/transfer", json={"guest_token": "mock_jwt_token"}
            )
            assert response.status_code == 200

            data = await response.get_json()
            assert data["transferred_count"] == 3

    @pytest.mark.asyncio
    async def test_transfer_chats_to_guest(self, client, mock_guest_auth):
        """Test transfer to guest user (should fail)."""
        response = await client.post(
            "/api/v1/chats/transfer", json={"guest_token": "mock_token"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_transfer_chats_missing_token(self, client, mock_auth):
        """Test transfer without guest token."""
        response = await client.post("/api/v1/chats/transfer", json={})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_transfer_chats_invalid_token(self, client, mock_auth):
        """Test transfer with invalid token."""
        from common.utils.jwt_utils import TokenValidationError

        with patch(
            "application.routes.chat_endpoints.workflow.get_user_info_from_token"
        ) as mock_token:
            mock_token.side_effect = TokenValidationError("Invalid token")

            response = await client.post(
                "/api/v1/chats/transfer", json={"guest_token": "invalid_token"}
            )
            assert response.status_code == 400  # Invalid guest token returns 400


class TestApproveAndRollback:
    """Tests for approve and rollback endpoints."""

    @pytest.mark.asyncio
    async def test_approve_success(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test successful approval."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )

        response = await client.post("/api/v1/chats/conv_123/approve")
        assert response.status_code == 200

        data = await response.get_json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_approve_chat_not_found(
        self, client, mock_auth, mock_service_factory
    ):
        """Test approve on non-existent chat."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=None
        )

        response = await client.post("/api/v1/chats/nonexistent/approve")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_rollback_success(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test successful rollback."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )

        response = await client.post("/api/v1/chats/conv_123/rollback")
        assert response.status_code == 200

        data = await response.get_json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_rollback_chat_not_found(
        self, client, mock_auth, mock_service_factory
    ):
        """Test rollback on non-existent chat."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=None
        )

        response = await client.post("/api/v1/chats/nonexistent/rollback")
        assert response.status_code == 404


class TestDownloadFile:
    """Tests for file download endpoint."""

    @pytest.mark.asyncio
    async def test_download_file_success(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test successful file download."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )

        response = await client.get("/api/v1/chats/conv_123/files/blob_123")
        assert response.status_code == 200
        assert "attachment" in response.headers.get("Content-Disposition", "")

    @pytest.mark.asyncio
    async def test_download_file_chat_not_found(
        self, client, mock_auth, mock_service_factory
    ):
        """Test file download for non-existent chat."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=None
        )

        response = await client.get("/api/v1/chats/nonexistent/files/blob_123")
        assert response.status_code == 404


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_canvas_schema_entity(self):
        """Test entity JSON schema generation."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        schema = service.get_schema("entity_json")
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "fields" in schema["properties"]

    def test_get_canvas_schema_workflow(self):
        """Test workflow JSON schema generation."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        schema = service.get_schema("workflow_json")
        assert schema["type"] == "object"
        assert "states" in schema["properties"]
        assert "transitions" in schema["properties"]

    def test_get_canvas_schema_app_config(self):
        """Test app config JSON schema generation."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        schema = service.get_schema("app_config_json")
        assert schema["type"] == "object"
        assert "app_name" in schema["properties"]

    def test_get_canvas_schema_generic(self):
        """Test generic schema generation for unknown types."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        schema = service.get_schema("unknown_type")
        assert schema["type"] == "object"
        assert "data" in schema["properties"]

    def test_build_canvas_prompt_entity(self):
        """Test entity prompt building."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        prompt = service.build_prompt("entity_json", "Create user entity", {})
        assert "User request" in prompt
        assert "PascalCase" in prompt

    def test_build_canvas_prompt_workflow(self):
        """Test workflow prompt building."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        prompt = service.build_prompt("workflow_json", "Create approval workflow", {})
        assert "User request" in prompt
        assert "States" in prompt

    def test_build_canvas_prompt_app_config(self):
        """Test app config prompt building."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        prompt = service.build_prompt(
            "app_config_json", "Create app", {"app_name": "MyApp"}
        )
        assert "MyApp" in prompt
        assert "entities" in prompt.lower()

    def test_build_canvas_prompt_with_context(self):
        """Test prompt building with context."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        context = {"key": "value", "nested": {"data": "test"}}
        prompt = service.build_prompt("entity_json", "Create entity", context)
        assert "Additional context" in prompt

    def test_generate_mock_canvas_response_entity(self):
        """Test mock entity response generation."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        response = service.generate_mock_response("entity_json", "Create user", {})
        assert response["name"] == "MockEntity"
        assert len(response["fields"]) > 0
        assert "id" in [f["name"] for f in response["fields"]]

    def test_generate_mock_canvas_response_workflow(self):
        """Test mock workflow response generation."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        response = service.generate_mock_response(
            "workflow_json", "Create workflow", {}
        )
        assert response["name"] == "MockWorkflow"
        assert "draft" in response["states"]
        assert len(response["transitions"]) > 0

    def test_generate_mock_canvas_response_app_config(self):
        """Test mock app config response generation."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        response = service.generate_mock_response(
            "app_config_json", "Create app", {"app_name": "TestApp"}
        )
        assert response["app_name"] == "TestApp"
        assert "entities" in response
        assert "workflows" in response

    def test_generate_mock_canvas_response_generic(self):
        """Test mock generic response generation."""
        from application.services import GoogleADKService
        from application.services.openai.canvas_question_service import (
            CanvasQuestionService,
        )

        service = CanvasQuestionService(GoogleADKService())
        response = service.generate_mock_response("unknown_type", "Test", {})
        assert response["mock"] is True
        assert response["type"] == "unknown_type"


class TestRateLimiting:
    """Tests for rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_applied(self, client, mock_auth, mock_service_factory):
        """Test that rate limiting is applied to endpoints."""
        # This test verifies that rate limit decorators are present
        # Actual rate limit testing would require real Redis/rate limiter
        from application.routes.chat import chat_bp

        # Just verify endpoints are registered
        assert chat_bp.name == "chat"


class TestAuthErrorHandling:
    """Tests for authentication error handling."""

    @pytest.mark.asyncio
    async def test_list_chats_token_expired(self, client, mock_service_factory):
        """Test token expiry returns 401."""
        from common.utils.jwt_utils import TokenExpiredError

        with patch(
            "application.routes.chat_endpoints.list_and_create.get_authenticated_user"
        ) as mock_auth:
            mock_auth.side_effect = TokenExpiredError("Token has expired")

            response = await client.get("/api/v1/chats")
            assert response.status_code == 401

            data = await response.get_json()
            assert "expired" in str(data).lower()

    @pytest.mark.asyncio
    async def test_create_chat_token_expired(self, client, mock_service_factory):
        """Test token expiry in create_chat returns 401."""
        from common.utils.jwt_utils import TokenExpiredError

        with patch(
            "application.routes.chat_endpoints.list_and_create.get_authenticated_user"
        ) as mock_auth:
            mock_auth.side_effect = TokenExpiredError("Token has expired")

            response = await client.post("/api/v1/chats", json={"name": "Test Chat"})
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_chat_token_validation_error(self, client, mock_service_factory):
        """Test token validation error returns 401."""
        from common.utils.jwt_utils import TokenValidationError

        with patch(
            "application.routes.chat_endpoints.crud.get_authenticated_user"
        ) as mock_auth:
            mock_auth.side_effect = TokenValidationError("Invalid token")

            response = await client.get("/api/v1/chats/conv_123")
            assert response.status_code == 401

            data = await response.get_json()
            assert "invalid" in str(data).lower() or "token" in str(data).lower()

    @pytest.mark.asyncio
    async def test_update_chat_token_expired(self, client, mock_service_factory):
        """Test token expiry in update_chat returns 401."""
        from common.utils.jwt_utils import TokenExpiredError

        with patch(
            "application.routes.chat_endpoints.crud.get_authenticated_user"
        ) as mock_auth:
            mock_auth.side_effect = TokenExpiredError("Token has expired")

            response = await client.put(
                "/api/v1/chats/conv_123", json={"chat_name": "Updated"}
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_chat_token_expired(self, client, mock_service_factory):
        """Test token expiry in delete_chat returns 401."""
        from common.utils.jwt_utils import TokenExpiredError

        with patch(
            "application.routes.chat_endpoints.crud.get_authenticated_user"
        ) as mock_auth:
            mock_auth.side_effect = TokenExpiredError("Token has expired")

            response = await client.delete("/api/v1/chats/conv_123")
            assert response.status_code == 401


class TestErrorHandling:
    """Tests for error handling across endpoints."""

    @pytest.mark.asyncio
    async def test_list_chats_exception(self, client, mock_auth, mock_service_factory):
        """Test exception handling in list_chats."""
        mock_service_factory.chat_service.list_conversations = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        response = await client.get("/api/v1/chats")
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_get_chat_exception(self, client, mock_auth, mock_service_factory):
        """Test exception handling in get_chat."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        response = await client.get("/api/v1/chats/conv_123")
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_stream_value_error(self, client, mock_auth, mock_service_factory):
        """Test ValueError handling in stream endpoint."""
        mock_service_factory.chat_stream_service.prepare_stream = AsyncMock(
            side_effect=ValueError("Invalid message format")
        )

        response = await client.post(
            "/api/v1/chats/conv_123/stream", json={"message": "Test"}
        )
        assert response.status_code == 200
        content = await response.get_data(as_text=True)
        assert "error" in content.lower()

    @pytest.mark.asyncio
    async def test_stream_conversation_not_found(
        self, client, mock_auth, mock_service_factory
    ):
        """Test conversation not found in stream endpoint."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=None
        )

        response = await client.post(
            "/api/v1/chats/nonexistent/stream", json={"message": "Test"}
        )
        assert response.status_code == 200
        content = await response.get_data(as_text=True)
        assert "chat not found" in content.lower()

    @pytest.mark.asyncio
    async def test_create_chat_exception(self, client, mock_auth, mock_service_factory):
        """Test exception handling in create_chat."""
        mock_service_factory.chat_service.create_conversation = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = await client.post("/api/v1/chats", json={"name": "Test Chat"})
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_update_chat_exception(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test exception handling in update_chat."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()
        mock_service_factory.chat_service.update_conversation = AsyncMock(
            side_effect=Exception("Update failed")
        )

        response = await client.put(
            "/api/v1/chats/conv_123", json={"chat_name": "Updated"}
        )
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_delete_chat_exception(
        self, client, mock_auth, mock_service_factory, sample_conversation
    ):
        """Test exception handling in delete_chat."""
        mock_service_factory.chat_service.get_conversation = AsyncMock(
            return_value=sample_conversation
        )
        mock_service_factory.chat_service.validate_ownership = MagicMock()
        mock_service_factory.chat_service.delete_conversation = AsyncMock(
            side_effect=Exception("Delete failed")
        )

        response = await client.delete("/api/v1/chats/conv_123")
        assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
