"""
Google ADK Service for AI Assistant Application

Provides integration with Google's Generative AI API (ADK) for:
- Chat message generation with conversation context
- Structured output generation for canvas questions
- Multi-model support via environment configuration

Following Google ADK best practices from https://google.github.io/adk-docs/
"""

import logging
import os
from typing import Any, Dict, List, Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GoogleADKService:
    """
    Google ADK integration service.

    Supports multiple Gemini models and provides both text generation
    and structured output capabilities for the AI Assistant.
    """

    def __init__(self) -> None:
        """
        Initialize Google ADK client with configuration from environment.

        Environment variables:
            GOOGLE_API_KEY: Required API key for Google AI
            GOOGLE_MODEL: Model name (default: gemini-2.0-flash-exp)
            GOOGLE_TEMPERATURE: Temperature for generation (default: 0.7)
            GOOGLE_MAX_TOKENS: Max output tokens (default: 8192)
        """
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning(
                "GOOGLE_API_KEY not set - GoogleADKService will not function"
            )

        self.model_name = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash-exp")
        self.temperature = float(os.getenv("GOOGLE_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("GOOGLE_MAX_TOKENS", "8192"))

        # Initialize client
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

        logger.info(
            f"GoogleADKService initialized with model={self.model_name}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}"
        )

    async def generate_response(
        self,
        prompt: str,
        context: Optional[List[Dict[str, str]]] = None,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate AI response using Google ADK.

        Args:
            prompt: User message/question
            context: Conversation history as list of {"role": "user/assistant", "content": "..."}
            system_instruction: Optional system prompt to guide AI behavior
            temperature: Override default temperature (0.0-1.0)
            max_tokens: Override default max output tokens

        Returns:
            Generated text response

        Raises:
            Exception: If API key is not configured or API call fails
        """
        if not self.client:
            raise Exception("Google ADK client not initialized - check GOOGLE_API_KEY")

        try:
            # Build content from context + current prompt
            contents = self._build_contents(prompt, context)

            # Configure generation
            config = types.GenerateContentConfig(
                temperature=temperature or self.temperature,
                top_p=0.95,
                max_output_tokens=max_tokens or self.max_tokens,
                system_instruction=system_instruction,
            )

            logger.debug(
                f"Generating response with model={self.model_name}, "
                f"context_messages={len(context) if context else 0}"
            )

            # Generate response
            response = await self.client.aio.models.generate_content(
                model=self.model_name, contents=contents, config=config
            )

            # Extract text from response
            result = response.text or ""
            logger.debug(f"Generated response length: {len(result)} characters")

            return result

        except Exception as e:
            logger.exception(f"Error generating response: {e}")
            raise Exception(f"Failed to generate AI response: {str(e)}") from e

    async def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output using response schema.

        Used for canvas questions to generate entity configs, workflow configs, etc.

        Args:
            prompt: User question/request
            schema: JSON schema defining the expected output structure
            system_instruction: Optional system prompt
            temperature: Override default temperature

        Returns:
            Parsed JSON object matching the schema

        Raises:
            Exception: If API key is not configured or API call fails
        """
        if not self.client:
            raise Exception("Google ADK client not initialized - check GOOGLE_API_KEY")

        try:
            # Configure for structured output
            config = types.GenerateContentConfig(
                temperature=temperature or self.temperature,
                response_mime_type="application/json",
                response_schema=schema,
                system_instruction=system_instruction,
            )

            logger.debug(
                f"Generating structured output with model={self.model_name}, "
                f"schema_keys={list(schema.keys())}"
            )

            # Generate response
            response = await self.client.aio.models.generate_content(
                model=self.model_name, contents=prompt, config=config
            )

            # Parse JSON response
            result_data = response.json()
            # Ensure we return a dict
            if isinstance(result_data, dict):
                logger.debug(f"Generated structured output: {list(result_data.keys())}")
                return result_data
            else:
                # If not a dict, wrap it
                logger.warning(f"Unexpected response type: {type(result_data)}")
                return {"data": result_data}

        except Exception as e:
            logger.exception(f"Error generating structured output: {e}")
            raise Exception(f"Failed to generate structured output: {str(e)}") from e

    def _build_contents(
        self, current_prompt: str, context: Optional[List[Dict[str, str]]] = None
    ) -> Any:
        """
        Build contents for API call from context and current prompt.

        Args:
            current_prompt: Current user message
            context: Previous conversation messages

        Returns:
            Contents formatted for Google ADK API (str or list)
        """
        if not context:
            # No context - just return the prompt
            return current_prompt

        # Build conversation history
        # Google ADK expects alternating user/model messages
        contents: List[Dict[str, Any]] = []
        for msg in context:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map role names
            if role == "assistant":
                role = "model"

            contents.append({"role": role, "parts": [{"text": content}]})

        # Add current prompt
        contents.append({"role": "user", "parts": [{"text": current_prompt}]})

        return contents

    async def generate_with_pydantic(
        self,
        prompt: str,
        response_model: Type[T],
        context: Optional[List[Dict[str, str]]] = None,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """
        Generate structured output using a Pydantic model.

        This is a convenience method that converts a Pydantic model to a JSON schema,
        generates the structured output, and parses it back into the Pydantic model.

        Args:
            prompt: User message/question
            response_model: Pydantic model class defining the expected output structure
            context: Conversation history as list of {"role": "user/assistant", "content": "..."}
            system_instruction: Optional system prompt to guide AI behavior
            temperature: Override default temperature (0.0-1.0)

        Returns:
            Instance of the Pydantic model with the generated data

        Raises:
            Exception: If API key is not configured or API call fails
        """
        if not self.client:
            raise Exception("Google ADK client not initialized - check GOOGLE_API_KEY")

        try:
            # Build content from context + current prompt
            contents = self._build_contents(prompt, context)

            # Get JSON schema from Pydantic model
            schema = response_model.model_json_schema()

            # Remove additionalProperties from schema (not supported by Gemini)
            def remove_additional_properties(obj):
                if isinstance(obj, dict):
                    obj.pop("additionalProperties", None)
                    for value in obj.values():
                        remove_additional_properties(value)
                elif isinstance(obj, list):
                    for item in obj:
                        remove_additional_properties(item)

            remove_additional_properties(schema)

            # Configure for structured output
            config = types.GenerateContentConfig(
                temperature=temperature or self.temperature,
                response_mime_type="application/json",
                response_schema=schema,
                system_instruction=system_instruction,
            )

            logger.debug(
                f"Generating Pydantic output with model={self.model_name}, "
                f"response_model={response_model.__name__}"
            )

            # Generate response
            response = await self.client.aio.models.generate_content(
                model=self.model_name, contents=contents, config=config
            )

            # Parse JSON response into Pydantic model
            result_data = response.json()
            result = response_model.model_validate(result_data)

            logger.debug(f"Successfully parsed response into {response_model.__name__}")

            return result

        except Exception as e:
            logger.exception(f"Error generating Pydantic output: {e}")
            raise Exception(f"Failed to generate Pydantic output: {str(e)}") from e

    def is_configured(self) -> bool:
        """
        Check if the service is properly configured.

        Returns:
            True if API key is set and client is initialized
        """
        return self.client is not None
