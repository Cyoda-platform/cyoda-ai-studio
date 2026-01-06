"""
Unit tests for OpenAI SDK Service
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

from application.services.openai.sdk_service import OpenAISDKService


class TestPerson(BaseModel):
    """Test schema for structured output."""
    name: str
    age: int
    email: str


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("OPENAI_TEMPERATURE", "0.7")
    monkeypatch.setenv("OPENAI_MAX_TOKENS", "8192")
    monkeypatch.setenv("OPENAI_TIMEOUT", "300")
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "3")


@pytest.fixture
def service(mock_env):
    """Create service instance with mocked client."""
    with patch('application.services.openai.sdk_service.AsyncOpenAI'):
        service = OpenAISDKService()
        service.client = AsyncMock()
        return service


class TestOpenAISDKServiceInit:
    """Test service initialization."""

    def test_init_with_api_key(self, mock_env):
        """Test initialization with API key."""
        with patch('application.services.openai.sdk_service.AsyncOpenAI'):
            service = OpenAISDKService()
            assert service.api_key == "sk-test-key"
            assert service.model_name == "gpt-4o"
            assert service.temperature == 0.7
            assert service.max_tokens == 8192
            assert service.timeout == 300
            assert service.max_retries == 3

    def test_init_without_api_key(self, monkeypatch):
        """Test initialization without API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch('application.services.openai.sdk_service.AsyncOpenAI'):
            service = OpenAISDKService()
            assert service.api_key is None
            assert service.client is None

    def test_is_configured_true(self, service):
        """Test is_configured returns True when client exists."""
        assert service.is_configured() is True

    def test_is_configured_false(self, mock_env):
        """Test is_configured returns False when client is None."""
        with patch('application.services.openai.sdk_service.AsyncOpenAI'):
            service = OpenAISDKService()
            service.client = None
            assert service.is_configured() is False


class TestGenerateResponse:
    """Test response generation."""

    @pytest.mark.asyncio
    async def test_generate_response_success(self, service):
        """Test successful response generation."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        response = await service.generate_response("Hello")
        assert response == "Test response"

    @pytest.mark.asyncio
    async def test_generate_response_with_context(self, service):
        """Test response generation with context."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        context = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"}
        ]
        response = await service.generate_response("How are you?", context=context)
        assert response == "Response"

    @pytest.mark.asyncio
    async def test_generate_response_with_system_instruction(self, service):
        """Test response generation with system instruction."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        response = await service.generate_response(
            "Hello",
            system_instruction="You are helpful"
        )
        assert response == "Response"

    @pytest.mark.asyncio
    async def test_generate_response_not_configured(self, mock_env):
        """Test response generation when not configured."""
        with patch('application.services.openai.sdk_service.AsyncOpenAI'):
            service = OpenAISDKService()
            service.client = None

            with pytest.raises(Exception, match="not initialized"):
                await service.generate_response("Hello")

    @pytest.mark.asyncio
    async def test_generate_response_empty_content(self, service):
        """Test response generation with empty content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        response = await service.generate_response("Hello")
        assert response == ""

    @pytest.mark.asyncio
    async def test_generate_response_api_call_parameters(self, service):
        """Test that API is called with correct parameters."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_response("Test prompt")

        # Verify API was called
        service.client.chat.completions.create.assert_called_once()
        call_kwargs = service.client.chat.completions.create.call_args[1]
        assert "messages" in call_kwargs
        assert "model" in call_kwargs

    @pytest.mark.asyncio
    async def test_generate_response_uses_model_from_config(self, service):
        """Test that model from service configuration is used."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_response("Test")

        call_kwargs = service.client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == service.model_name

    @pytest.mark.asyncio
    async def test_generate_response_uses_temperature(self, service):
        """Test that temperature from service configuration is used."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_response("Test")

        call_kwargs = service.client.chat.completions.create.call_args[1]
        assert call_kwargs.get("temperature") == service.temperature

    @pytest.mark.asyncio
    async def test_generate_response_uses_max_tokens(self, service):
        """Test that max_tokens from service configuration is used."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_response("Test")

        call_kwargs = service.client.chat.completions.create.call_args[1]
        assert call_kwargs.get("max_tokens") == service.max_tokens

    @pytest.mark.asyncio
    async def test_generate_response_message_structure(self, service):
        """Test that messages are structured correctly."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate_response("Test prompt")

        call_kwargs = service.client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert isinstance(messages, list)
        assert len(messages) > 0
        assert "role" in messages[-1]
        assert "content" in messages[-1]

    @pytest.mark.asyncio
    async def test_generate_response_with_context_message_order(self, service):
        """Test that context messages are in correct order."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        context = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"}
        ]

        await service.generate_response("Third", context=context)

        call_kwargs = service.client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        # Context should be first, prompt last
        assert messages[0]["content"] == "First"
        assert messages[1]["content"] == "Second"
        assert messages[2]["content"] == "Third"

    @pytest.mark.asyncio
    async def test_generate_response_long_content(self, service):
        """Test response with long content."""
        long_response = "A" * 5000
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=long_response))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        response = await service.generate_response("Hello")

        assert response == long_response
        assert len(response) == 5000

    @pytest.mark.asyncio
    async def test_generate_response_special_characters(self, service):
        """Test response with special characters."""
        special_response = "Test\\nwith\\ttabs and \"quotes\" and 'apostrophes'"
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=special_response))]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        response = await service.generate_response("Test")

        assert response == special_response


class TestGenerateStructuredOutput:
    """Test structured output generation."""

    @pytest.mark.asyncio
    async def test_generate_structured_output_success(self, service):
        """Test successful structured output generation."""
        mock_person = TestPerson(name="John", age=30, email="john@example.com")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(parsed=mock_person))]
        service.client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)

        result = await service.generate_structured_output(
            "Extract person info",
            TestPerson
        )
        assert result.name == "John"
        assert result.age == 30
        assert result.email == "john@example.com"

    @pytest.mark.asyncio
    async def test_generate_structured_output_not_configured(self, mock_env):
        """Test structured output when not configured."""
        with patch('application.services.openai.sdk_service.AsyncOpenAI'):
            service = OpenAISDKService()
            service.client = None

            with pytest.raises(Exception, match="not initialized"):
                await service.generate_structured_output("Test", TestPerson)


class TestStreamResponse:
    """Test response streaming."""

    @pytest.mark.asyncio
    async def test_stream_response_success(self, service):
        """Test successful response streaming."""
        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=" "))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="world"))]),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_stream())
        mock_context.__aexit__ = AsyncMock(return_value=None)

        service.client.chat.completions.create = AsyncMock(return_value=mock_context)

        chunks = []
        async for chunk in service.stream_response("Hello"):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert "".join(chunks) == "Hello world"

    @pytest.mark.asyncio
    async def test_stream_response_not_configured(self, mock_env):
        """Test streaming when not configured."""
        with patch('application.services.openai.sdk_service.AsyncOpenAI'):
            service = OpenAISDKService()
            service.client = None

            with pytest.raises(Exception, match="not initialized"):
                async for _ in service.stream_response("Hello"):
                    pass


class TestBuildMessages:
    """Test message building."""

    def test_build_messages_simple(self, service):
        """Test building simple message."""
        messages = service._build_messages("Hello")
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_build_messages_with_system(self, service):
        """Test building message with system instruction."""
        messages = service._build_messages(
            "Hello",
            system_instruction="You are helpful"
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_build_messages_with_context(self, service):
        """Test building message with context."""
        context = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"}
        ]
        messages = service._build_messages("How are you?", context=context)
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_build_messages_with_all(self, service):
        """Test building message with all parameters."""
        context = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"}
        ]
        messages = service._build_messages(
            "How are you?",
            context=context,
            system_instruction="You are helpful"
        )
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
        assert messages[3]["role"] == "user"

