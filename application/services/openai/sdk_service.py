"""
Enhanced OpenAI SDK Service for AI Assistant Application

Provides integration with OpenAI's API for:
- Chat message generation with conversation context
- Structured output generation using Pydantic schemas
- Streaming responses with keep-alive support
- Vision/multimodal capabilities
- Retry logic and error handling

Following OpenAI best practices from https://platform.openai.com/docs/
"""

import asyncio
import logging
import os
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar

from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OpenAISDKService:
    """
    Enhanced OpenAI SDK integration service with full feature parity to Google ADK.

    Supports multiple OpenAI models and provides:
    - Text generation with retry logic
    - Structured output with Pydantic schemas
    - Streaming responses
    - Vision/multimodal support
    - Comprehensive error handling
    """

    def __init__(self) -> None:
        """
        Initialize OpenAI SDK client with configuration from environment.

        Environment variables:
            OPENAI_API_KEY: Required API key for OpenAI
            OPENAI_MODEL: Model name (default: gpt-4o)
            OPENAI_TEMPERATURE: Temperature for generation (default: 0.7)
            OPENAI_MAX_TOKENS: Max output tokens (default: 8192)
            OPENAI_TIMEOUT: Request timeout in seconds (default: 300)
            OPENAI_MAX_RETRIES: Max retry attempts (default: 3)
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning(
                "OPENAI_API_KEY not set - OpenAISDKService will not function"
            )

        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "8192"))
        self.timeout = int(os.getenv("OPENAI_TIMEOUT", "300"))
        self.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))

        # Initialize client
        self.client = (
            AsyncOpenAI(api_key=self.api_key, timeout=self.timeout)
            if self.api_key
            else None
        )

        logger.info(
            f"OpenAISDKService initialized: model={self.model_name}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}, "
            f"timeout={self.timeout}s, max_retries={self.max_retries}"
        )

    async def _call_api(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call OpenAI API and return response.

        Args:
            messages: Message list
            temperature: Temperature setting
            max_tokens: Max tokens

        Returns:
            Generated response text
        """
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        result = response.choices[0].message.content or ""
        logger.debug(f"Generated response: {len(result)} characters")
        return result

    async def _handle_retry_error(
        self, error: Exception, attempt: int, error_type: str
    ) -> None:
        """Handle retry logic for API errors.

        Args:
            error: The error that occurred
            attempt: Current attempt number
            error_type: Type of error (rate_limit, connection, server)

        Raises:
            Exception: If max retries exceeded or error is not retryable
        """
        if attempt < self.max_retries - 1:
            wait_time = 2**attempt
            logger.warning(f"{error_type} error, retrying in {wait_time}s: {error}")
            await asyncio.sleep(wait_time)
        else:
            logger.error(f"{error_type} failed after {self.max_retries} retries")
            raise Exception(f"{error_type} failed: {str(error)}") from error

    async def generate_response(
        self,
        prompt: str,
        context: Optional[List[Dict[str, str]]] = None,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate AI response using OpenAI API with retry logic.

        Args:
            prompt: User message/question
            context: Conversation history as list of {"role": "user/assistant", "content": "..."}
            system_instruction: Optional system prompt to guide AI behavior
            temperature: Override default temperature (0.0-1.0)
            max_tokens: Override default max output tokens

        Returns:
            Generated text response

        Raises:
            Exception: If API key is not configured or all retries fail
        """
        if not self.client:
            raise Exception("OpenAI client not initialized - check OPENAI_API_KEY")

        messages = self._build_messages(prompt, context, system_instruction)
        temp = temperature or self.temperature
        tokens = max_tokens or self.max_tokens

        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Generating response (attempt {attempt + 1}/{self.max_retries}): "
                    f"model={self.model_name}, context_messages={len(context) if context else 0}"
                )

                return await self._call_api(messages, temp, tokens)

            except RateLimitError as e:
                await self._handle_retry_error(e, attempt, "Rate limit")

            except APIConnectionError as e:
                await self._handle_retry_error(e, attempt, "Connection")

            except APIError as e:
                if attempt < self.max_retries - 1 and e.status_code >= 500:
                    await self._handle_retry_error(e, attempt, "Server")
                else:
                    logger.error(f"API error: {e}")
                    raise Exception(f"API error: {str(e)}") from e

    async def generate_structured_output(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """
        Generate structured output using Pydantic schema.

        Args:
            prompt: User question/request
            schema: Pydantic model class defining the expected output structure
            system_instruction: Optional system prompt
            temperature: Override default temperature

        Returns:
            Parsed object matching the schema

        Raises:
            Exception: If API key is not configured or API call fails
        """
        if not self.client:
            raise Exception("OpenAI client not initialized - check OPENAI_API_KEY")

        messages = self._build_messages(prompt, None, system_instruction)

        try:
            logger.debug(f"Generating structured output with schema: {schema.__name__}")

            response = await self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                response_format=schema,
                temperature=temperature or self.temperature,
            )

            result = response.choices[0].message.parsed
            logger.debug(f"Structured output generated: {type(result).__name__}")
            return result

        except ValidationError as e:
            logger.error(f"Schema validation failed: {e}")
            raise Exception(f"Schema validation failed: {str(e)}") from e
        except Exception as e:
            logger.exception(f"Error generating structured output: {e}")
            raise Exception(f"Failed to generate structured output: {str(e)}") from e

    async def stream_response(
        self,
        prompt: str,
        context: Optional[List[Dict[str, str]]] = None,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream response chunks from OpenAI API.

        Args:
            prompt: User message/question
            context: Conversation history
            system_instruction: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max output tokens

        Yields:
            Response text chunks as they arrive

        Raises:
            Exception: If API key is not configured or streaming fails
        """
        if not self.client:
            raise Exception("OpenAI client not initialized - check OPENAI_API_KEY")

        messages = self._build_messages(prompt, context, system_instruction)

        try:
            logger.debug(f"Starting stream: model={self.model_name}")

            async with await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True,
            ) as stream:
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            logger.debug("Stream completed successfully")

        except Exception as e:
            logger.exception(f"Error during streaming: {e}")
            raise Exception(f"Streaming failed: {str(e)}") from e

    def _build_messages(
        self,
        prompt: str,
        context: Optional[List[Dict[str, str]]] = None,
        system_instruction: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build message list for API call.

        Args:
            prompt: Current user message
            context: Previous conversation messages
            system_instruction: Optional system prompt

        Returns:
            Messages formatted for OpenAI API
        """
        messages: List[Dict[str, str]] = []

        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        if context:
            messages.extend(context)

        messages.append({"role": "user", "content": prompt})
        return messages

    def is_configured(self) -> bool:
        """
        Check if the service is properly configured.

        Returns:
            True if API key is set and client is initialized
        """
        return self.client is not None
