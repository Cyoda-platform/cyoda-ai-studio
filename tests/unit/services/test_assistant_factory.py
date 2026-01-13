"""Unit tests for AssistantFactory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.assistant.factory import AssistantFactory


class TestAssistantFactory:
    """Test AssistantFactory class."""

    @pytest.fixture
    def mock_entity_service(self):
        """Create mock entity service."""
        return MagicMock()

    @pytest.fixture
    def factory(self, mock_entity_service):
        """Create factory instance."""
        return AssistantFactory(mock_entity_service)

    def test_factory_initialization(self, mock_entity_service):
        """Test factory can be initialized."""
        factory = AssistantFactory(mock_entity_service)
        assert factory.entity_service == mock_entity_service

    @patch("application.services.assistant.factory.is_using_openai_sdk")
    @patch("application.services.assistant.factory.get_sdk_name")
    def test_create_assistant_delegates_to_google_adk(
        self, mock_get_sdk, mock_is_openai, factory
    ):
        """Test create_assistant delegates to Google ADK when configured."""
        mock_is_openai.return_value = False
        mock_get_sdk.return_value = "google"

        with patch.object(
            factory, "_create_google_adk_assistant"
        ) as mock_create_google:
            mock_create_google.return_value = MagicMock()

            result = factory.create_assistant()

            mock_create_google.assert_called_once()
            assert result is not None

    @patch("application.services.assistant.factory.is_using_openai_sdk")
    @patch("application.services.assistant.factory.get_sdk_name")
    def test_create_assistant_delegates_to_openai(
        self, mock_get_sdk, mock_is_openai, factory
    ):
        """Test create_assistant delegates to OpenAI when configured."""
        mock_is_openai.return_value = True
        mock_get_sdk.return_value = "openai"

        with patch.object(factory, "_create_openai_assistant") as mock_create_openai:
            mock_create_openai.return_value = MagicMock()

            result = factory.create_assistant()

            mock_create_openai.assert_called_once()
            assert result is not None

    def test_create_google_adk_assistant_structure(self, factory):
        """Test Google ADK assistant is created with correct structure."""
        with patch(
            "application.agents.coordinator.agent.root_agent"
        ) as mock_coordinator:
            with patch(
                "application.services.assistant.wrapper.CyodaAssistantWrapper"
            ) as mock_wrapper:
                mock_coordinator_instance = MagicMock()
                mock_coordinator.return_value = mock_coordinator_instance
                mock_wrapper.return_value = MagicMock()

                result = factory._create_google_adk_assistant()

                # Verify wrapper was created with coordinator and entity service
                mock_wrapper.assert_called_once()
                assert result is not None

    def test_create_google_adk_loads_coordinator_agent(self, factory):
        """Test Google ADK assistant loads coordinator agent."""
        with patch(
            "application.agents.coordinator.agent.root_agent"
        ) as mock_coordinator:
            with patch(
                "application.services.assistant.wrapper.CyodaAssistantWrapper"
            ) as mock_wrapper:
                mock_wrapper_instance = MagicMock()
                mock_wrapper.return_value = mock_wrapper_instance

                result = factory._create_google_adk_assistant()

                # Should wrap coordinator agent with entity service
                mock_wrapper.assert_called_once_with(
                    mock_coordinator, factory.entity_service
                )
                assert result == mock_wrapper_instance

    def test_create_google_adk_uses_coordinator(self, factory):
        """Test Google ADK assistant uses coordinator agent."""
        with patch("application.agents.coordinator.agent.root_agent"):
            with patch(
                "application.services.assistant.wrapper.CyodaAssistantWrapper"
            ) as mock_wrapper:
                mock_wrapper_instance = MagicMock()
                mock_wrapper.return_value = mock_wrapper_instance

                result = factory._create_google_adk_assistant()

                # Verify coordinator agent is used and wrapped
                assert result == mock_wrapper_instance
                mock_wrapper.assert_called_once()

    def test_create_openai_assistant_structure(self, factory):
        """Test OpenAI assistant is created with correct structure."""
        # Skip if OpenAI wrapper doesn't exist
        try:
            import application.agents.openai_agents
            import application.services.openai.assistant_wrapper
        except ImportError:
            pytest.skip("OpenAI components not available")

        with patch(
            "application.services.openai.assistant_wrapper.OpenAIAssistantWrapper"
        ) as mock_wrapper:
            with patch(
                "application.agents.openai_agents.create_openai_coordinator_agent"
            ) as mock_create:
                mock_coordinator = MagicMock()
                mock_create.return_value = mock_coordinator
                mock_wrapper.return_value = MagicMock()

                result = factory._create_openai_assistant()

                # Verify coordinator was created
                mock_create.assert_called_once()

                # Verify wrapper was created with coordinator and entity service
                mock_wrapper.assert_called_once_with(
                    mock_coordinator, factory.entity_service
                )


class TestAssistantFactoryIntegration:
    """Integration tests for AssistantFactory with real imports."""

    @pytest.fixture
    def mock_entity_service(self):
        """Create mock entity service."""
        return MagicMock()

    def test_factory_can_import_all_dependencies(self, mock_entity_service):
        """Test factory can import all its dependencies without errors."""
        # This test verifies no circular imports
        try:
            factory = AssistantFactory(mock_entity_service)
            assert factory is not None
        except ImportError as e:
            pytest.fail(f"Failed to create factory due to import error: {e}")

    def test_factory_has_required_methods(self, mock_entity_service):
        """Test factory has all required methods."""
        factory = AssistantFactory(mock_entity_service)

        assert hasattr(factory, "create_assistant")
        assert hasattr(factory, "_create_google_adk_assistant")
        assert hasattr(factory, "_create_openai_assistant")
        assert callable(factory.create_assistant)
        assert callable(factory._create_google_adk_assistant)
        assert callable(factory._create_openai_assistant)
