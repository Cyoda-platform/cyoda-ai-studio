"""Unit tests for cyoda_assistant module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from google.genai import types

from application.agents.cyoda_assistant import CyodaAssistantWrapper


# Module-level fixtures for TestSaveSessionState
@pytest.fixture
def mock_agent():
    """Create a mock ADK agent."""
    agent = MagicMock()
    agent.name = "test_agent"
    return agent


@pytest.fixture
def mock_entity_service():
    """Create a mock entity service."""
    return AsyncMock()


class TestCyodaAssistant:
    """Test cyoda_assistant entry point."""

    def test_create_cyoda_assistant_imports(self):
        """Test create_cyoda_assistant can be imported."""
        try:
            from application.agents.cyoda_assistant import create_cyoda_assistant

            assert callable(create_cyoda_assistant)
        except ImportError as e:
            pytest.fail(f"Failed to import create_cyoda_assistant: {e}")

    def test_cyoda_assistant_wrapper_imports(self):
        """Test CyodaAssistantWrapper can be imported."""
        try:
            from application.agents.cyoda_assistant import CyodaAssistantWrapper

            assert CyodaAssistantWrapper is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CyodaAssistantWrapper: {e}")


class TestCyodaAssistantWrapper:
    """Test CyodaAssistantWrapper class."""

    def test_wrapper_can_be_imported(self):
        """Test that CyodaAssistantWrapper can be imported."""
        try:
            from application.agents.cyoda_assistant import CyodaAssistantWrapper

            assert CyodaAssistantWrapper is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CyodaAssistantWrapper: {e}")


class TestCyodaAssistantLazyImports:
    """Test lazy imports in agents module."""

    def test_agents_module_lazy_import_create_cyoda_assistant(self):
        """Test lazy import of create_cyoda_assistant from agents module."""
        from application.agents import create_cyoda_assistant

        assert callable(create_cyoda_assistant)

    def test_agents_module_lazy_import_wrapper(self):
        """Test lazy import of CyodaAssistantWrapper from agents module."""
        from application.agents import CyodaAssistantWrapper

        assert CyodaAssistantWrapper is not None

    def test_agents_module_exports(self):
        """Test agents module __all__ exports."""
        import application.agents as agents

        assert hasattr(agents, "__all__")
        assert "create_cyoda_assistant" in agents.__all__
        assert "CyodaAssistantWrapper" in agents.__all__
        assert "OpenAIAssistantWrapper" in agents.__all__


class TestProcessMessage:
    """Test CyodaAssistantWrapper.process_message method."""

    @pytest.fixture
    def mock_entity_service(self):
        """Create a mock entity service."""
        return AsyncMock()

    @pytest.fixture
    def mock_adk_agent(self):
        """Create a mock ADK agent."""
        agent = MagicMock()
        agent.name = "test_coordinator"
        return agent

    @pytest.fixture
    def mock_runner(self):
        """Create a mock Runner."""
        runner = AsyncMock()
        runner.session_service = AsyncMock()
        return runner

    @pytest.fixture
    def wrapper(self, mock_adk_agent, mock_entity_service):
        """Create a CyodaAssistantWrapper instance with mocked dependencies."""
        from application.agents.cyoda_assistant import CyodaAssistantWrapper

        with patch("google.adk.runners.Runner") as mock_runner_class:
            mock_runner_instance = AsyncMock()
            mock_runner_instance.session_service = AsyncMock()
            mock_runner_class.return_value = mock_runner_instance

            wrapper = CyodaAssistantWrapper(
                adk_agent=mock_adk_agent, entity_service=mock_entity_service
            )
            wrapper.runner = mock_runner_instance
            return wrapper

    @pytest.mark.asyncio
    async def test_process_message_with_new_session(self, wrapper):
        """Test processing a message with a new session creation."""
        user_message = "Hello, help me build an app"
        conversation_history = []
        user_id = "user123"

        # Mock session creation
        mock_session = AsyncMock()
        mock_session.state = {
            "__cyoda_technical_id__": "session_tech_id_123",
            "conversation_history": [],
            "user_id": user_id,
        }

        # Setup mocks before calling process_message
        final_session = AsyncMock()
        final_session.state = {"conversation_history": []}
        get_session_mock = AsyncMock(side_effect=[None, final_session])
        create_session_mock = AsyncMock(return_value=mock_session)
        wrapper.runner.session_service.get_session = get_session_mock
        wrapper.runner.session_service.create_session = create_session_mock

        # Mock runner.run_async to return events
        mock_event = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Here's how to build your app..."
        mock_event.content = MagicMock()
        mock_event.content.parts = [mock_part]

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        wrapper.runner.run_async = mock_run_async

        result = await wrapper.process_message(
            user_message=user_message,
            conversation_history=conversation_history,
            user_id=user_id,
        )

        assert result["response"] == "Here's how to build your app..."
        # Verify session was created
        assert create_session_mock.called

    @pytest.mark.asyncio
    async def test_process_message_with_existing_session(self, wrapper):
        """Test processing a message with an existing session."""
        user_message = "Continue building"
        conversation_history = [{"role": "user", "content": "Hello"}]
        conversation_id = "conv_123"
        user_id = "user123"

        # Mock existing session
        mock_session = AsyncMock()
        mock_session.state = {
            "__cyoda_technical_id__": "session_tech_id_456",
            "conversation_history": conversation_history,
            "user_id": user_id,
        }

        wrapper.runner.session_service.get_session = AsyncMock(
            return_value=mock_session
        )

        # Mock runner.run_async
        mock_event = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Continuing from where we left off..."
        mock_event.content = MagicMock()
        mock_event.content.parts = [mock_part]

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        wrapper.runner.run_async = mock_run_async

        # Mock session state loading
        wrapper._load_session_state = AsyncMock(
            return_value={"previous_state": "value"}
        )
        wrapper._save_session_state = AsyncMock()

        result = await wrapper.process_message(
            user_message=user_message,
            conversation_history=conversation_history,
            conversation_id=conversation_id,
            user_id=user_id,
        )

        assert result["response"] == "Continuing from where we left off..."
        # Session state saving is handled internally
        wrapper._save_session_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_with_ui_functions(self, wrapper):
        """Test that UI functions are extracted from session state."""
        user_message = "Build my app"
        conversation_history = []
        user_id = "user123"

        # Create initial session state that will be modified
        session_state_ref = {
            "__cyoda_technical_id__": "session_tech_id_789",
            "ui_functions": [],
        }

        mock_session = AsyncMock()
        mock_session.id = "session_id_789"
        mock_session.state = session_state_ref

        wrapper.runner.session_service.get_session = AsyncMock(return_value=None)
        wrapper.runner.session_service.create_session = AsyncMock(
            return_value=mock_session
        )

        mock_event = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "App created"
        mock_event.content = MagicMock()
        mock_event.content.parts = [mock_part]

        async def mock_run_async(*args, **kwargs):
            # Simulate agent execution adding ui_functions to session state
            session_state_ref["ui_functions"] = [
                {"type": "hook", "action": "open_canvas"}
            ]
            yield mock_event

        wrapper.runner.run_async = mock_run_async

        # Mock _build_initial_session_state to return our session_state_ref
        wrapper._build_initial_session_state = AsyncMock(return_value=session_state_ref)

        result = await wrapper.process_message(
            user_message=user_message,
            conversation_history=conversation_history,
            user_id=user_id,
        )

        assert len(result["metadata"]["ui_functions"]) == 1
        assert result["metadata"]["ui_functions"][0]["action"] == "open_canvas"

    @pytest.mark.asyncio
    async def test_process_message_with_repository_info(self, wrapper):
        """Test that repository info is extracted from session state."""
        user_message = "Build my app"
        conversation_history = []
        user_id = "user123"

        session_state_ref = {
            "__cyoda_technical_id__": "session_tech_id_999",
        }

        mock_session = AsyncMock()
        mock_session.id = "session_id_999"
        mock_session.state = session_state_ref

        wrapper.runner.session_service.get_session = AsyncMock(return_value=None)
        wrapper.runner.session_service.create_session = AsyncMock(
            return_value=mock_session
        )

        mock_event = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Repository created"
        mock_event.content = MagicMock()
        mock_event.content.parts = [mock_part]

        async def mock_run_async(*args, **kwargs):
            # Simulate agent execution adding repository info to session state
            session_state_ref["repository_name"] = "my-app"
            session_state_ref["repository_owner"] = "user123"
            session_state_ref["branch_name"] = "main"
            yield mock_event

        wrapper.runner.run_async = mock_run_async

        # Mock _build_initial_session_state to return our session_state_ref
        wrapper._build_initial_session_state = AsyncMock(return_value=session_state_ref)

        result = await wrapper.process_message(
            user_message=user_message,
            conversation_history=conversation_history,
            user_id=user_id,
        )

        assert result["metadata"]["repository_info"] is not None
        assert result["metadata"]["repository_info"]["repository_name"] == "my-app"
        assert result["metadata"]["repository_info"]["repository_owner"] == "user123"
        assert result["metadata"]["repository_info"]["repository_branch"] == "main"

    @pytest.mark.asyncio
    async def test_process_message_with_build_task_id(self, wrapper):
        """Test that build task ID is extracted from session state."""
        user_message = "Build my app"
        conversation_history = []
        user_id = "user123"

        session_state_ref = {
            "__cyoda_technical_id__": "session_tech_id_111",
        }

        mock_session = AsyncMock()
        mock_session.id = "session_id_111"
        mock_session.state = session_state_ref

        wrapper.runner.session_service.get_session = AsyncMock(return_value=None)
        wrapper.runner.session_service.create_session = AsyncMock(
            return_value=mock_session
        )

        mock_event = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Build started"
        mock_event.content = MagicMock()
        mock_event.content.parts = [mock_part]

        async def mock_run_async(*args, **kwargs):
            # Simulate agent execution adding build_task_id to session state
            session_state_ref["build_task_id"] = "build_task_123"
            yield mock_event

        wrapper.runner.run_async = mock_run_async

        # Mock _build_initial_session_state to return our session_state_ref
        wrapper._build_initial_session_state = AsyncMock(return_value=session_state_ref)

        result = await wrapper.process_message(
            user_message=user_message,
            conversation_history=conversation_history,
            user_id=user_id,
        )

        assert result["metadata"]["build_task_id"] == "build_task_123"

    @pytest.mark.asyncio
    async def test_process_message_runner_error(self, wrapper):
        """Test that runner errors are properly raised."""
        user_message = "Build my app"
        conversation_history = []
        user_id = "user123"

        mock_session = AsyncMock()
        mock_session.state = {
            "__cyoda_technical_id__": "session_tech_id_222",
        }

        wrapper.runner.session_service.get_session = AsyncMock(return_value=None)
        wrapper.runner.session_service.create_session = AsyncMock(
            return_value=mock_session
        )

        # Make runner.run_async raise an exception
        async def mock_run_async_error(*args, **kwargs):
            raise RuntimeError("Agent execution failed")
            yield  # Never reached

        wrapper.runner.run_async = mock_run_async_error

        with pytest.raises(RuntimeError, match="Agent execution failed"):
            await wrapper.process_message(
                user_message=user_message,
                conversation_history=conversation_history,
                user_id=user_id,
            )

    @pytest.mark.asyncio
    async def test_process_message_with_conversation_id(self, wrapper):
        """Test processing a message with conversation_id to save session state."""
        user_message = "Build an app"
        conversation_history = [{"role": "user", "content": "Hello"}]
        conversation_id = "conv_123"
        user_id = "user123"

        # Mock conversation entity for _load_session_state
        mock_conversation_response = MagicMock()
        mock_conversation_response.data = {
            "id": conversation_id,
            "user_id": user_id,
            "workflow_cache": {"adk_session_state": {"previous_state": "value"}},
        }
        wrapper.entity_service.get_by_id = AsyncMock(
            return_value=mock_conversation_response
        )
        wrapper.entity_service.update = AsyncMock()

        # Mock session
        session_state_ref = {
            "conversation_history": conversation_history,
            "user_id": user_id,
            "previous_state": "value",
        }
        mock_session = AsyncMock()
        mock_session.id = "session_id_123"
        mock_session.state = session_state_ref

        wrapper.runner.session_service.get_session = AsyncMock(return_value=None)
        wrapper.runner.session_service.create_session = AsyncMock(
            return_value=mock_session
        )

        mock_event = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "App created"
        mock_event.content = MagicMock()
        mock_event.content.parts = [mock_part]

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        wrapper.runner.run_async = mock_run_async

        result = await wrapper.process_message(
            user_message=user_message,
            conversation_history=conversation_history,
            conversation_id=conversation_id,
            user_id=user_id,
        )

        assert result["response"] == "App created"
        # Verify session state was saved (update was called for conversation)
        wrapper.entity_service.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_with_session_technical_id(self, wrapper):
        """Test that session_technical_id is used when provided."""
        user_message = "Continue"
        conversation_history = []
        conversation_id = "conv_123"
        session_technical_id = "session_tech_456"
        user_id = "user123"

        # Mock conversation entity for _load_session_state
        mock_conversation_response = MagicMock()
        mock_conversation_response.data = {
            "id": conversation_id,
            "user_id": user_id,
            "workflow_cache": {},
        }
        wrapper.entity_service.get_by_id = AsyncMock(
            return_value=mock_conversation_response
        )
        wrapper.entity_service.update = AsyncMock()

        # Mock session retrieval by technical_id
        mock_session = AsyncMock()
        mock_session.id = "some_session_id"
        mock_session.state = {
            "__cyoda_technical_id__": session_technical_id,
            "conversation_history": [],
        }

        # Mock get_session_by_technical_id to return the session
        wrapper._get_session_by_technical_id = AsyncMock(return_value=mock_session)

        mock_event = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Continuing..."
        mock_event.content = MagicMock()
        mock_event.content.parts = [mock_part]

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        wrapper.runner.run_async = mock_run_async

        result = await wrapper.process_message(
            user_message=user_message,
            conversation_history=conversation_history,
            conversation_id=conversation_id,
            session_technical_id=session_technical_id,
            user_id=user_id,
        )

        # Verify the response
        assert result["response"] == "Continuing..."
        # Verify session state was saved (update was called for conversation)
        wrapper.entity_service.update.assert_called_once()


class TestSaveSessionState:
    """Comprehensive tests for _save_session_state function."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_agent, mock_entity_service):
        """Setup fixtures for each test."""
        self.mock_agent = mock_agent
        self.mock_entity_service = mock_entity_service

    @pytest.mark.asyncio
    async def test_save_session_state_success(self):
        """Test successful session state save."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        # Mock conversation entity with required user_id field
        mock_conversation = {
            "id": "conv123",
            "user_id": "user123",
            "workflow_cache": {},
        }
        mock_response = MagicMock()
        mock_response.data = mock_conversation

        self.mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)
        self.mock_entity_service.update = AsyncMock()

        session_state = {"key": "value", "user_id": "user123"}

        await wrapper._save_session_state("conv123", session_state)

        # Verify get_by_id was called
        self.mock_entity_service.get_by_id.assert_called_once()
        # Verify update was called with correct data
        self.mock_entity_service.update.assert_called_once()

        # Verify session state was saved in workflow_cache
        update_call = self.mock_entity_service.update.call_args
        assert update_call[1]["entity_id"] == "conv123"
        assert "adk_session_state" in update_call[1]["entity"]["workflow_cache"]

    @pytest.mark.asyncio
    async def test_save_session_state_conversation_not_found(self):
        """Test handling when conversation is not found."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        self.mock_entity_service.get_by_id = AsyncMock(return_value=None)
        self.mock_entity_service.update = AsyncMock()

        session_state = {"key": "value"}

        # Should not raise exception
        await wrapper._save_session_state("nonexistent", session_state)

        # Verify get_by_id was called but update was not
        self.mock_entity_service.get_by_id.assert_called_once()
        self.mock_entity_service.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_session_state_version_conflict_retry(self):
        """Test retry logic on version conflict error."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        # Mock conversation entity with required user_id field
        mock_conversation = {
            "id": "conv123",
            "user_id": "user123",
            "workflow_cache": {},
        }
        mock_response = MagicMock()
        mock_response.data = mock_conversation

        self.mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)

        # First call fails with version conflict, second succeeds
        from common.service.service import EntityServiceError

        self.mock_entity_service.update = AsyncMock(
            side_effect=[
                EntityServiceError("Error 422: version mismatch"),
                None,  # Success on retry
            ]
        )

        session_state = {"key": "value"}

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await wrapper._save_session_state("conv123", session_state)

            # Verify retry happened
            assert self.mock_entity_service.update.call_count == 2
            # Verify sleep was called for backoff
            mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_save_session_state_max_retries_exceeded(self):
        """Test handling when max retries are exceeded."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        # Mock conversation entity with required user_id field
        mock_conversation = {
            "id": "conv123",
            "user_id": "user123",
            "workflow_cache": {},
        }
        mock_response = MagicMock()
        mock_response.data = mock_conversation

        self.mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)

        # All attempts fail with version conflict
        from common.service.service import EntityServiceError

        self.mock_entity_service.update = AsyncMock(
            side_effect=EntityServiceError("Error 422: version mismatch")
        )

        session_state = {"key": "value"}

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Should not raise exception, just log error
            await wrapper._save_session_state("conv123", session_state)

            # Verify all retries were attempted
            assert self.mock_entity_service.update.call_count == 5

    @pytest.mark.asyncio
    async def test_save_session_state_non_retryable_error(self):
        """Test handling non-retryable errors."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        # Mock conversation entity with required user_id field
        mock_conversation = {
            "id": "conv123",
            "user_id": "user123",
            "workflow_cache": {},
        }
        mock_response = MagicMock()
        mock_response.data = mock_conversation

        self.mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)

        # Non-retryable error (not a version conflict)
        from common.service.service import EntityServiceError

        self.mock_entity_service.update = AsyncMock(
            side_effect=EntityServiceError("Authorization error")
        )

        session_state = {"key": "value"}

        # Should not raise exception
        await wrapper._save_session_state("conv123", session_state)

        # Verify update was called only once (no retry)
        self.mock_entity_service.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_session_state_unexpected_error(self):
        """Test handling unexpected errors."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        # Mock conversation entity with required user_id field
        mock_conversation = {
            "id": "conv123",
            "user_id": "user123",
            "workflow_cache": {},
        }
        mock_response = MagicMock()
        mock_response.data = mock_conversation

        self.mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)
        self.mock_entity_service.update = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        session_state = {"key": "value"}

        # Should not raise exception
        await wrapper._save_session_state("conv123", session_state)

        # Verify update was called
        self.mock_entity_service.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_session_state_preserves_existing_workflow_cache(self):
        """Test that existing workflow_cache data is preserved."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        # Mock conversation with existing workflow_cache and required user_id field
        mock_conversation = {
            "id": "conv123",
            "user_id": "user123",
            "workflow_cache": {
                "existing_key": "existing_value",
                "adk_session_state": {"old": "state"},
            },
        }
        mock_response = MagicMock()
        mock_response.data = mock_conversation

        self.mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)
        self.mock_entity_service.update = AsyncMock()

        new_session_state = {"new": "state"}

        await wrapper._save_session_state("conv123", new_session_state)

        # Verify update was called
        update_call = self.mock_entity_service.update.call_args
        updated_entity = update_call[1]["entity"]

        # Verify new session state is saved
        assert (
            updated_entity["workflow_cache"]["adk_session_state"] == new_session_state
        )
        # Verify other keys are preserved
        assert updated_entity["workflow_cache"]["existing_key"] == "existing_value"

    @pytest.mark.asyncio
    async def test_save_session_state_with_complex_state(self):
        """Test saving complex session state with nested structures."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        # Mock conversation entity with required user_id field
        mock_conversation = {
            "id": "conv123",
            "user_id": "user123",
            "workflow_cache": {},
        }
        mock_response = MagicMock()
        mock_response.data = mock_conversation

        self.mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)
        self.mock_entity_service.update = AsyncMock()

        # Complex session state
        complex_state = {
            "user_id": "user123",
            "conversation_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
            "nested_data": {"level1": {"level2": ["item1", "item2"]}},
            "metadata": {"timestamp": 1234567890},
        }

        await wrapper._save_session_state("conv123", complex_state)

        # Verify complex state was saved correctly
        update_call = self.mock_entity_service.update.call_args
        saved_state = update_call[1]["entity"]["workflow_cache"]["adk_session_state"]

        assert saved_state == complex_state
        assert saved_state["conversation_history"][0]["content"] == "Hello"
        assert saved_state["nested_data"]["level1"]["level2"] == ["item1", "item2"]

    @pytest.mark.asyncio
    async def test_save_session_state_version_conflict_errors(self):
        """Test various version conflict error messages are recognized."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        # Mock conversation entity with required user_id field
        mock_conversation = {
            "id": "conv123",
            "user_id": "user123",
            "workflow_cache": {},
        }
        mock_response = MagicMock()
        mock_response.data = mock_conversation

        self.mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)

        from common.service.service import EntityServiceError

        # Test different version conflict error messages
        error_messages = [
            "422 Unprocessable Entity",
            "500 Internal Server Error",
            "version mismatch detected",
            "earliestUpdateAccept constraint violated",
            "was changed by another transaction",
            "update operation returned no entity id",
        ]

        for error_msg in error_messages:
            self.mock_entity_service.update = AsyncMock(
                side_effect=[EntityServiceError(error_msg), None]  # Success on retry
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await wrapper._save_session_state("conv123", {"key": "value"})

                # Should have retried (2 calls)
                assert self.mock_entity_service.update.call_count == 2

    @pytest.mark.asyncio
    async def test_save_session_state_with_response_data_attribute(self):
        """Test handling when response has data attribute."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        # Mock response with .data attribute and required user_id field
        mock_conversation = {
            "id": "conv123",
            "user_id": "user123",
            "workflow_cache": {},
        }
        mock_response = MagicMock()
        mock_response.data = mock_conversation

        self.mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)
        self.mock_entity_service.update = AsyncMock()

        session_state = {"key": "value"}

        await wrapper._save_session_state("conv123", session_state)

        # Should succeed without errors
        self.mock_entity_service.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_session_state_with_direct_conversation_data(self):
        """Test handling when response is the conversation directly."""
        wrapper = CyodaAssistantWrapper(self.mock_agent, self.mock_entity_service)

        # Mock response without .data attribute (direct response) with required user_id field
        mock_conversation = {
            "id": "conv123",
            "user_id": "user123",
            "workflow_cache": {},
        }
        mock_response = mock_conversation

        self.mock_entity_service.get_by_id = AsyncMock(return_value=mock_response)
        self.mock_entity_service.update = AsyncMock()

        session_state = {"key": "value"}

        await wrapper._save_session_state("conv123", session_state)

        # Should succeed without errors
        self.mock_entity_service.update.assert_called_once()
