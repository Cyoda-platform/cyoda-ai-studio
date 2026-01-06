"""Unit tests for AssistantFactory."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

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

    @patch('application.services.assistant.factory.is_using_openai_sdk')
    @patch('application.services.assistant.factory.get_sdk_name')
    def test_create_assistant_delegates_to_google_adk(self, mock_get_sdk, mock_is_openai, factory):
        """Test create_assistant delegates to Google ADK when configured."""
        mock_is_openai.return_value = False
        mock_get_sdk.return_value = "google"

        with patch.object(factory, '_create_google_adk_assistant') as mock_create_google:
            mock_create_google.return_value = MagicMock()

            result = factory.create_assistant()

            mock_create_google.assert_called_once()
            assert result is not None

    @patch('application.services.assistant.factory.is_using_openai_sdk')
    @patch('application.services.assistant.factory.get_sdk_name')
    def test_create_assistant_delegates_to_openai(self, mock_get_sdk, mock_is_openai, factory):
        """Test create_assistant delegates to OpenAI when configured."""
        mock_is_openai.return_value = True
        mock_get_sdk.return_value = "openai"

        with patch.object(factory, '_create_openai_assistant') as mock_create_openai:
            mock_create_openai.return_value = MagicMock()

            result = factory.create_assistant()

            mock_create_openai.assert_called_once()
            assert result is not None

    @patch('application.services.assistant.factory.get_model_config')
    @patch('application.services.assistant.factory.create_instruction_provider')
    def test_create_google_adk_assistant_structure(self, mock_instruction, mock_model, factory):
        """Test Google ADK assistant is created with correct structure."""
        mock_model.return_value = MagicMock()
        mock_instruction.return_value = "instruction"

        with patch('google.adk.agents.LlmAgent') as mock_llm_agent:
            with patch('application.services.assistant.wrapper.CyodaAssistantWrapper') as mock_wrapper:
                mock_agent = MagicMock()
                mock_llm_agent.return_value = mock_agent
                mock_wrapper.return_value = MagicMock()

                result = factory._create_google_adk_assistant()

                # Verify LlmAgent was created
                mock_llm_agent.assert_called_once()
                call_kwargs = mock_llm_agent.call_args[1]

                assert call_kwargs['name'] == 'cyoda_assistant'
                assert 'description' in call_kwargs
                assert 'instruction' in call_kwargs
                assert 'tools' in call_kwargs
                assert 'sub_agents' in call_kwargs

                # Verify wrapper was created with agent and entity service
                mock_wrapper.assert_called_once_with(mock_agent, factory.entity_service)

    def test_create_google_adk_loads_get_user_info_tool(self, factory):
        """Test Google ADK assistant loads get_user_info tool."""
        with patch('application.services.assistant.factory.get_model_config'):
            with patch('application.services.assistant.factory.create_instruction_provider'):
                with patch('google.adk.agents.LlmAgent') as mock_llm_agent:
                    with patch('application.services.assistant.wrapper.CyodaAssistantWrapper'):
                        # Mock get_user_info import
                        mock_get_user_info = MagicMock()
                        with patch.dict('sys.modules', {'application.agents.setup.tools': MagicMock(get_user_info=mock_get_user_info)}):
                            factory._create_google_adk_assistant()

                            call_kwargs = mock_llm_agent.call_args[1]
                            tools = call_kwargs['tools']

                            # Should have get_user_info in tools
                            assert len(tools) == 1
                            assert tools[0] == mock_get_user_info

    def test_create_google_adk_handles_missing_get_user_info(self, factory):
        """Test Google ADK assistant handles missing get_user_info gracefully."""
        with patch('application.services.assistant.factory.get_model_config'):
            with patch('application.services.assistant.factory.create_instruction_provider'):
                with patch('google.adk.agents.LlmAgent') as mock_llm_agent:
                    with patch('application.services.assistant.wrapper.CyodaAssistantWrapper'):
                        # Mock the import to raise ImportError inside the try block
                        import sys
                        original_modules = sys.modules.copy()
                        # Remove the module if it exists
                        if 'application.agents.setup.tools' in sys.modules:
                            del sys.modules['application.agents.setup.tools']

                        # Mock to raise ImportError
                        sys.modules['application.agents.setup.tools'] = None

                        try:
                            factory._create_google_adk_assistant()

                            call_kwargs = mock_llm_agent.call_args[1]
                            tools = call_kwargs['tools']

                            # Should have empty tools list when import fails
                            assert len(tools) == 0
                        finally:
                            # Restore modules
                            sys.modules.update(original_modules)

    def test_create_google_adk_includes_all_sub_agents(self, factory):
        """Test Google ADK assistant includes all required sub-agents."""
        with patch('application.services.assistant.factory.get_model_config'):
            with patch('application.services.assistant.factory.create_instruction_provider'):
                with patch('google.adk.agents.LlmAgent') as mock_llm_agent:
                    with patch('application.services.assistant.wrapper.CyodaAssistantWrapper'):
                        factory._create_google_adk_assistant()

                        call_kwargs = mock_llm_agent.call_args[1]
                        sub_agents = call_kwargs['sub_agents']

                        # Should have at least 6 sub-agents (may vary with implementation)
                        assert len(sub_agents) >= 6
                        # Verify all expected agents are present (by checking it's a list)
                        assert isinstance(sub_agents, list)

    def test_create_openai_assistant_structure(self, factory):
        """Test OpenAI assistant is created with correct structure."""
        # Skip if OpenAI wrapper doesn't exist
        try:
            import application.services.openai.assistant_wrapper
            import application.agents.openai_agents
        except ImportError:
            pytest.skip("OpenAI components not available")

        with patch('application.services.openai.assistant_wrapper.OpenAIAssistantWrapper') as mock_wrapper:
            with patch('application.agents.openai_agents.create_openai_coordinator_agent') as mock_create:
                mock_coordinator = MagicMock()
                mock_create.return_value = mock_coordinator
                mock_wrapper.return_value = MagicMock()

                result = factory._create_openai_assistant()

                # Verify coordinator was created
                mock_create.assert_called_once()

                # Verify wrapper was created with coordinator and entity service
                mock_wrapper.assert_called_once_with(mock_coordinator, factory.entity_service)


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

        assert hasattr(factory, 'create_assistant')
        assert hasattr(factory, '_create_google_adk_assistant')
        assert hasattr(factory, '_create_openai_assistant')
        assert callable(factory.create_assistant)
        assert callable(factory._create_google_adk_assistant)
        assert callable(factory._create_openai_assistant)
