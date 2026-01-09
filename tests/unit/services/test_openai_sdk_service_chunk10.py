"""Tests for generate_response method in OpenAISDKService."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIConnectionError, APIError, RateLimitError

from application.services.openai.sdk_service import OpenAISDKService


class TestGenerateResponse:
    """Tests for generate_response method."""

    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """Test successful response generation."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service._build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        result = await service.generate_response("test prompt")

        assert result == "Generated response"
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_no_client(self):
        """Test error when client not initialized."""
        service = OpenAISDKService()
        service.client = None

        with pytest.raises(Exception, match="OpenAI client not initialized"):
            await service.generate_response("test prompt")

    @pytest.mark.asyncio
    async def test_generate_response_with_context(self):
        """Test response generation with conversation context."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        service._build_messages = MagicMock(
            return_value=context + [{"role": "user", "content": "test"}]
        )

        result = await service.generate_response("test prompt", context=context)

        assert result == "Response"

    @pytest.mark.asyncio
    async def test_generate_response_with_system_instruction(self):
        """Test response generation with system instruction."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service._build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        result = await service.generate_response(
            "test prompt", system_instruction="You are helpful"
        )

        assert result == "Response"
        service._build_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_with_custom_temperature(self):
        """Test response generation with custom temperature."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service._build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        result = await service.generate_response("test prompt", temperature=0.5)

        assert result == "Response"
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_generate_response_with_custom_max_tokens(self):
        """Test response generation with custom max_tokens."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service._build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        result = await service.generate_response("test prompt", max_tokens=500)

        assert result == "Response"
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["max_tokens"] == 500

    @pytest.mark.asyncio
    async def test_generate_response_uses_build_messages(self):
        """Test that _build_messages is called with correct parameters."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service._build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        context = [{"role": "user", "content": "Hello"}]
        system_instruction = "You are helpful"

        result = await service.generate_response(
            "test prompt", context=context, system_instruction=system_instruction
        )

        assert result == "Response"
        service._build_messages.assert_called_once_with(
            "test prompt", context, system_instruction
        )

    @pytest.mark.asyncio
    async def test_generate_response_calls_api_with_correct_model(self):
        """Test that API is called with correct model name."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service._build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        result = await service.generate_response("test prompt")

        assert result == "Response"
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_generate_response_uses_default_temperature(self):
        """Test that default temperature is used when not overridden."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service._build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        result = await service.generate_response("test prompt")

        assert result == "Response"
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_generate_response_uses_default_max_tokens(self):
        """Test that default max_tokens is used when not overridden."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service._build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        result = await service.generate_response("test prompt")

        assert result == "Response"
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["max_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_generate_response_returns_content_from_first_choice(self):
        """Test that response content is extracted from first choice."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(), MagicMock()]
        mock_response.choices[0].message.content = "First choice"
        mock_response.choices[1].message.content = "Second choice"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service._build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        result = await service.generate_response("test prompt")

        assert result == "First choice"

    @pytest.mark.asyncio
    async def test_generate_response_empty_content(self):
        """Test handling of empty response content."""
        mock_client = AsyncMock()
        service = OpenAISDKService()
        service.client = mock_client
        service.model_name = "gpt-4"
        service.temperature = 0.7
        service.max_tokens = 1000

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        service._build_messages = MagicMock(
            return_value=[{"role": "user", "content": "test"}]
        )

        result = await service.generate_response("test prompt")

        assert result == ""
